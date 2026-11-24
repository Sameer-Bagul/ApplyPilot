import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'node:child_process';
import path from 'node:path';
import { getPythonBin, getProjectRoot, getLeadDetail, updateLead } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json().catch(() => ({}));
    const leadId = body.lead_id || body.leadId;
    const subject = body.subject || body.email_subject || body.email_draft_subject;
    const bodyText = body.body_text || body.email_body_text || body.email_draft_body;
    const bodyHtml = body.body_html || body.email_body_html;

    if (!leadId) {
      return NextResponse.json({ success: false, error: 'lead_id is required' }, { status: 400 });
    }

    // First update the database in Node.js, preserving all edited metadata
    updateLead(leadId, {
      contact_name: body.contact_name,
      contact_email: body.contact_email,
      personal_email: body.personal_email,
      personal_email_source: body.personal_email_source,
      preferred_channel: body.preferred_channel,
      role_title: body.role_title,
      persona: body.persona,
      email_subject: subject,
      email_body_text: bodyText,
      email_draft_subject: subject,
      email_draft_body: bodyText,
      followup_draft_subject: body.followup_draft_subject,
      followup_draft_body: body.followup_draft_body,
      outreach_status: 'drafted',
    });

    const projectRoot = getProjectRoot();
    const pythonBin = getPythonBin();

    const script = `
import json, sys
from applypilot.outreach.mailer import save_single_lead_draft

res = save_single_lead_draft(
    lead_id=${JSON.stringify(leadId)},
    subject=${JSON.stringify(subject || null)},
    body_text=${JSON.stringify(bodyText || null)},
    body_html=${JSON.stringify(bodyHtml || null)}
)
print("---AP_RESULT_START---")
print(json.dumps(res))
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

      const timer = setTimeout(() => {
        try { proc.kill(); } catch {}
        const updated = getLeadDetail(leadId);
        resolve(NextResponse.json({
          success: true,
          message: 'Draft saved in local database (background sync timed out)',
          lead: updated,
        }));
      }, 15000);

      proc.on('close', (code) => {
        clearTimeout(timer);
        const updated = getLeadDetail(leadId);
        if (stdout.includes('---AP_RESULT_START---')) {
          try {
            const raw = stdout.split('---AP_RESULT_START---')[1].split('---AP_RESULT_END---')[0].trim();
            const result = JSON.parse(raw);
            resolve(NextResponse.json({
              success: result.success,
              result,
              lead: updated,
              message: result.success ? `Draft saved (Draft ID: ${result.draft_id})` : result.error,
            }));
            return;
          } catch (e: any) {}
        }

        resolve(NextResponse.json({
          success: true,
          message: 'Draft saved successfully',
          lead: updated,
        }));
      });
    });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to save draft' },
      { status: 500 }
    );
  }
}
