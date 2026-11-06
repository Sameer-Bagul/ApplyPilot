import { NextResponse } from 'next/server';
import { spawn } from 'node:child_process';
import { getDb } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const targetUrl = body.job_url || body.jobUrl;
    const isHeadless = body.headless === true || (body.mode === 'headless' && body.headless !== false);
    const dryRun = Boolean(body.dry_run || body.dryRun);

    if (!targetUrl) {
      return NextResponse.json({ success: false, error: 'job_url or jobUrl is required' }, { status: 400 });
    }

    const db = getDb();
    const job = db.prepare('SELECT * FROM jobs WHERE url = ?').get(targetUrl) as any;

    if (!job) {
      return NextResponse.json({ success: false, error: 'Job not found in database' }, { status: 404 });
    }

    // Build CLI args for ApplyPilot apply command
    const args = ['apply', '--url', targetUrl];
    if (isHeadless) {
      args.push('--headless');
    }
    if (dryRun) {
      args.push('--dry-run');
    }
    if (body.autoSubmit === true || body.auto_submit === true) {
      args.push('--auto-submit');
    } else if (body.autoSubmit === false || body.auto_submit === false) {
      args.push('--review');
    }

    // Run in background or spawn process
    return new Promise<Response>((resolve) => {
      let stdout = '';
      let stderr = '';

      const proc = spawn('applypilot', args, {
        env: {
          ...process.env,
          PYTHONUNBUFFERED: '1',
          DISPLAY: process.env.DISPLAY || ':1',
          WAYLAND_DISPLAY: process.env.WAYLAND_DISPLAY || 'wayland-1',
          APPLYPILOT_HEADLESS: isHeadless ? 'true' : 'false',
        },
      });

      // 5-minute window for headed visual feedback & human CAPTCHA resolution; 45s for headless
      const timeoutMs = isHeadless ? 45000 : 300000;
      const timer = setTimeout(() => {
        try {
          proc.kill();
        } catch {}

        // Check if a HITL ticket was created
        const hitlTicket = db.prepare(
          'SELECT * FROM hitl_tickets WHERE job_url = ? ORDER BY ticket_id DESC LIMIT 1'
        ).get(targetUrl) as any;

        if (hitlTicket) {
          resolve(
            NextResponse.json({
              success: true,
              status: 'needs_human',
              message: 'Encountered application blocker or screening question. Intervention ticket created.',
              ticket_id: hitlTicket.ticket_id,
              output: stdout.slice(-1000),
            })
          );
        } else {
          resolve(
            NextResponse.json({
              success: true,
              status: 'running',
              message: isHeadless
                ? 'Application running in background.'
                : 'Headed browser active on your screen. Complete any CAPTCHA if prompted.',
              output: stdout.slice(-1000),
            })
          );
        }
      }, timeoutMs);

      proc.stdout.on('data', (d) => {
        stdout += d.toString();
      });

      proc.stderr.on('data', (d) => {
        stderr += d.toString();
      });

      proc.on('close', (code) => {
        clearTimeout(timer);

        // Check if HITL ticket was created
        const hitlTicket = db.prepare(
          'SELECT * FROM hitl_tickets WHERE job_url = ? ORDER BY ticket_id DESC LIMIT 1'
        ).get(targetUrl) as any;

        // Check latest job state
        const updatedJob = db.prepare('SELECT state FROM jobs WHERE url = ?').get(targetUrl) as any;

        if (hitlTicket && (hitlTicket.status === 'pending' || hitlTicket.status === 'sent')) {
          resolve(
            NextResponse.json({
              success: true,
              status: 'needs_human',
              ticket_id: hitlTicket.ticket_id,
              message: 'Screening question requires human input. Check HITL Tickets.',
              output: stdout.slice(-2000),
            })
          );
        } else if (code === 0 || updatedJob?.state === 'applied') {
          resolve(
            NextResponse.json({
              success: true,
              status: 'applied',
              message: 'Application submitted successfully!',
              output: stdout.slice(-2000),
            })
          );
        } else {
          resolve(
            NextResponse.json({
              success: false,
              status: updatedJob?.state || 'failed',
              error: `Apply process exited with code ${code}`,
              output: stdout.slice(-2000) || stderr.slice(-1000),
            })
          );
        }
      });

      proc.on('error', (err) => {
        clearTimeout(timer);
        resolve(
          NextResponse.json({
            success: false,
            error: `Failed to spawn applypilot process: ${err.message}`,
          }, { status: 500 })
        );
      });
    });
  } catch (err: any) {
    return NextResponse.json({ success: false, error: err.message }, { status: 500 });
  }
}

