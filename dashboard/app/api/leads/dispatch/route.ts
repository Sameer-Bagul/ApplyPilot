import { NextRequest, NextResponse } from 'next/server';
import { getDb } from '@/lib/db';
import { spawn } from 'node:child_process';
import path from 'node:path';

export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  try {
    const db = getDb();
    
    // Check how many approved leads are waiting
    const approvedLeads = db.prepare(`
      SELECT lead_id, company_name, contact_email, email_draft_subject
      FROM recruiter_leads
      WHERE outreach_status = 'approved'
    `).all() as any[];

    if (approvedLeads.length === 0) {
      return NextResponse.json({
        success: true,
        message: 'No approved leads waiting for dispatch.',
        dispatchedCount: 0,
      });
    }

    // Call python CLI in background to safely run dispatch_approved_leads
    const projectRoot = path.resolve(process.cwd(), '..');
    const venvPython = path.join(projectRoot, '.venv', 'bin', 'python');

    const py = spawn(venvPython, ['-m', 'applypilot.cli', 'outreach', 'send'], {
      cwd: projectRoot,
      env: { ...process.env, PYTHONPATH: path.join(projectRoot, 'src') },
    });

    let stdout = '';
    let stderr = '';

    py.stdout?.on('data', (d) => { stdout += d.toString(); });
    py.stderr?.on('data', (d) => { stderr += d.toString(); });

    await new Promise((resolve) => {
      py.on('close', resolve);
      // Timeout after 8 seconds
      setTimeout(resolve, 8000);
    });

    return NextResponse.json({
      success: true,
      message: `Dispatched ${approvedLeads.length} approved outreach emails.`,
      dispatchedCount: approvedLeads.length,
      logs: stdout || stderr,
    });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to dispatch approved leads' },
      { status: 500 }
    );
  }
}

