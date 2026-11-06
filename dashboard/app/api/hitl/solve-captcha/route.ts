import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'node:child_process';
import { getDb, getApplypilotBin } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const ticketId = body.ticket_id || body.ticketId;

    if (!ticketId) {
      return NextResponse.json({ success: false, error: 'ticket_id is required' }, { status: 400 });
    }

    const db = getDb();
    const ticket: any = db.prepare('SELECT * FROM hitl_tickets WHERE ticket_id = ?').get(ticketId);

    if (!ticket) {
      return NextResponse.json({ success: false, error: 'Ticket not found' }, { status: 404 });
    }

    const targetUrl = ticket.job_url;
    if (!targetUrl) {
      return NextResponse.json({ success: false, error: 'Ticket does not contain a job_url' }, { status: 400 });
    }

    // Launch apply in headed mode with auto-submit enabled by default
    const args = ['apply', '--url', targetUrl];
    if (body.auto_submit !== false && body.autoSubmit !== false) {
      args.push('--auto-submit');
    }

    return new Promise<Response>((resolve) => {
      let stdout = '';
      let stderr = '';

      const proc = spawn(getApplypilotBin(), args, {
        env: {
          ...process.env,
          PYTHONUNBUFFERED: '1',
          DISPLAY: process.env.DISPLAY || ':1',
          WAYLAND_DISPLAY: process.env.WAYLAND_DISPLAY || 'wayland-1',
          APPLYPILOT_HEADLESS: 'false',
        },
      });

      // 5-minute window for candidate to solve CAPTCHA and review
      const timer = setTimeout(() => {
        try {
          proc.kill();
        } catch {}

        resolve(
          NextResponse.json({
            success: true,
            status: 'running',
            message: 'Headed browser window active on screen. Please complete CAPTCHA in the window.',
            output: stdout.slice(-1000),
          })
        );
      }, 300000);

      proc.stdout.on('data', (d) => {
        stdout += d.toString();
      });

      proc.stderr.on('data', (d) => {
        stderr += d.toString();
      });

      proc.on('close', (code) => {
        clearTimeout(timer);

        const updatedJob: any = db.prepare('SELECT state FROM jobs WHERE url = ?').get(targetUrl);
        const isApplied = code === 0 || updatedJob?.state === 'applied';

        if (isApplied) {
          const now = new Date().toISOString();
          db.prepare("UPDATE hitl_tickets SET status = 'resolved', resolved_at = ? WHERE ticket_id = ?").run(now, ticketId);
          db.prepare("UPDATE jobs SET state = 'applied', applied_at = ?, needs_human_reason = NULL WHERE url = ?").run(now, targetUrl);

          resolve(
            NextResponse.json({
              success: true,
              status: 'resolved',
              message: 'CAPTCHA solved and application submitted successfully!',
              output: stdout.slice(-2000),
            })
          );
        } else {
          resolve(
            NextResponse.json({
              success: false,
              status: updatedJob?.state || 'pending',
              error: `Process finished with code ${code}. If CAPTCHA was solved, review window status.`,
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
