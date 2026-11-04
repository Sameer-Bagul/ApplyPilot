import { NextResponse } from 'next/server';
import { spawn } from 'node:child_process';
import { getDb } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { job_url, mode = 'headless', dry_run = false } = body;

    if (!job_url) {
      return NextResponse.json({ success: false, error: 'job_url is required' }, { status: 400 });
    }

    const db = getDb();
    const job = db.prepare('SELECT * FROM jobs WHERE url = ?').get(job_url) as any;

    if (!job) {
      return NextResponse.json({ success: false, error: 'Job not found in database' }, { status: 404 });
    }

    // Build CLI args for ApplyPilot apply command
    const args = ['apply', '--url', job_url];
    if (mode === 'headless') {
      args.push('--headless');
    }
    if (dry_run) {
      args.push('--dry-run');
    }

    // Run in background or spawn process
    return new Promise<Response>((resolve) => {
      let stdout = '';
      let stderr = '';

      const proc = spawn('applypilot', args, {
        env: {
          ...process.env,
          PYTHONUNBUFFERED: '1',
          APPLYPILOT_HEADLESS: mode === 'headless' ? 'true' : 'false',
        },
      });

      // Set timeout in case it's waiting on something
      const timer = setTimeout(() => {
        try {
          proc.kill();
        } catch {}

        // Check if a HITL ticket was created
        const hitlTicket = db.prepare(
          'SELECT * FROM hitl_tickets WHERE job_url = ? ORDER BY id DESC LIMIT 1'
        ).get(job_url) as any;

        if (hitlTicket) {
          resolve(
            NextResponse.json({
              success: true,
              status: 'needs_human',
              message: 'Encountered application blocker or screening question. Intervention ticket created.',
              ticket_id: hitlTicket.id,
              output: stdout.slice(-1000),
            })
          );
        } else {
          resolve(
            NextResponse.json({
              success: true,
              status: 'running',
              message: 'Application execution started in background.',
              output: stdout.slice(-1000),
            })
          );
        }
      }, 15000); // 15-second response window for immediate UI feedback

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
          'SELECT * FROM hitl_tickets WHERE job_url = ? ORDER BY id DESC LIMIT 1'
        ).get(job_url) as any;

        // Check latest job state
        const updatedJob = db.prepare('SELECT state FROM jobs WHERE url = ?').get(job_url) as any;

        if (hitlTicket && hitlTicket.status === 'pending') {
          resolve(
            NextResponse.json({
              success: true,
              status: 'needs_human',
              ticket_id: hitlTicket.id,
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
