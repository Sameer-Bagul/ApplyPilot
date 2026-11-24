import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'node:child_process';
import path from 'node:path';
import { getPythonBin, getProjectRoot, getLeadDetail, updateLead } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json().catch(() => ({}));
    const leadIds: string[] = Array.isArray(body.lead_ids)
      ? body.lead_ids
      : body.lead_id || body.leadId
      ? [body.lead_id || body.leadId]
      : [];

    if (leadIds.length === 0) {
      return NextResponse.json({ success: false, error: 'lead_id or lead_ids is required' }, { status: 400 });
    }

    // If single lead and custom subject/body edits were sent, persist them first
    if (leadIds.length === 1 && (body.subject || body.body_text || body.contact_email || body.preferred_channel)) {
      updateLead(leadIds[0], {
        contact_name: body.contact_name,
        contact_email: body.contact_email,
        personal_email: body.personal_email,
        preferred_channel: body.preferred_channel,
        role_title: body.role_title,
        persona: body.persona,
        email_subject: body.subject,
        email_body_text: body.body_text,
        email_draft_subject: body.subject,
        email_draft_body: body.body_text,
      });
    }

    const projectRoot = getProjectRoot();
    const pythonBin = getPythonBin();

    const script = `
import json, sys
from applypilot.outreach.mailer import send_single_lead_email

ids = ${JSON.stringify(leadIds)}
results = []
for lid in ids:
    res = send_single_lead_email(lid)
    results.append(res)

print("---AP_RESULT_START---")
print(json.dumps(results if len(ids) > 1 else results[0]))
print("---AP_RESULT_END---")
`;

    return new Promise<NextResponse>((resolve) => {
      const proc = spawn(pythonBin, ['-c', script], {
        cwd: projectRoot,
        env: { ...process.env, PYTHONPATH: path.join(projectRoot, 'src') },
      });

      let stdout = '';
      let stderr = '';

      proc.stdout.on('data', (d) => { stdout += d.toString(); });
      proc.stderr.on('data', (d) => { stderr += d.toString(); });

      const timeoutMs = Math.max(20000, leadIds.length * 5000);
      const timer = setTimeout(() => {
        try { proc.kill(); } catch {}
        resolve(NextResponse.json({ success: false, error: 'Timed out dispatching email' }, { status: 504 }));
      }, timeoutMs);

      proc.on('close', (code) => {
        clearTimeout(timer);
        if (stdout.includes('---AP_RESULT_START---')) {
          try {
            const raw = stdout.split('---AP_RESULT_START---')[1].split('---AP_RESULT_END---')[0].trim();
            const result = JSON.parse(raw);

            if (Array.isArray(result)) {
              const successCount = result.filter((r) => r.success).length;
              resolve(NextResponse.json({
                success: successCount > 0,
                dispatchedCount: successCount,
                results: result,
                message: `Dispatched ${successCount} of ${result.length} outreach emails.`,
              }));
              return;
            }

            const updated = getLeadDetail(leadIds[0]);
            resolve(NextResponse.json({
              success: result.success,
              result,
              lead: updated,
              message: result.success ? `Email sent to ${result.to_email}` : result.error,
            }, { status: result.success ? 200 : 400 }));
            return;
          } catch (e: any) {}
        }

        if (code !== 0) {
          resolve(NextResponse.json({
            success: false,
            error: stderr || stdout || `Process exited with code ${code}`,
          }, { status: 500 }));
        } else {
          resolve(NextResponse.json({
            success: true,
            message: 'Email dispatched successfully',
            output: stdout,
          }));
        }
      });
    });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to dispatch email' },
      { status: 500 }
    );
  }
}
