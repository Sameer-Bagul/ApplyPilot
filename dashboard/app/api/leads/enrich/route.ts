import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs';
import { getLeadDetail, getDb } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json().catch(() => ({}));
    const leadId = body.leadId || body.lead_id;
    const contactName = body.contactName || body.contact_name;
    const companyName = body.companyName || body.company_name;
    const domain = body.domain || body.company_domain;
    const githubHandle = body.githubHandle || body.github_handle;

    if (!leadId || !contactName) {
      return NextResponse.json(
        { success: false, error: 'leadId and contactName are required' },
        { status: 400 }
      );
    }

    const projectRoot = path.resolve(process.cwd(), '..');
    const venvPython = path.join(projectRoot, '.venv', 'bin', 'python');
    const pythonBin = fs.existsSync(venvPython) ? venvPython : 'python3';

    const script = `
import json, sys
from applypilot.discovery.company_osint import hunt_candidate_and_exec_emails

res = hunt_candidate_and_exec_emails(
    person_name=${JSON.stringify(contactName)},
    company_name=${JSON.stringify(companyName || "")},
    domain=${JSON.stringify(domain || "")},
    github_handle=${JSON.stringify(githubHandle || "")}
)
print("__RESULT__" + json.dumps(res))
`;

    return new Promise<NextResponse>((resolve) => {
      const proc = spawn(pythonBin, ['-c', script], {
        cwd: projectRoot,
        env: { ...process.env, PYTHONPATH: path.join(projectRoot, 'src') },
      });

      let stdout = '';
      let stderr = '';

      proc.stdout.on('data', (d) => {
        stdout += d.toString();
      });

      proc.stderr.on('data', (d) => {
        stderr += d.toString();
      });

      const timer = setTimeout(() => {
        try {
          proc.kill();
        } catch {}
        resolve(
          NextResponse.json({
            success: true,
            status: 'timeout',
            leadData: getLeadDetail(leadId),
          })
        );
      }, 10000);

      proc.on('close', (code) => {
        clearTimeout(timer);
        try {
          const match = stdout.match(/__RESULT__(.*)$/m);
          let huntResult: any = null;
          if (match && match[1]) {
            huntResult = JSON.parse(match[1]);
          }

          if (huntResult) {
            const db = getDb();
            const personalEmail = huntResult.personal_emails?.[0] || null;
            const personalSource = huntResult.sources_used?.join(', ') || null;
            const corporateEmail = huntResult.corporate_emails?.[0] || null;

            db.prepare(`
              UPDATE recruiter_leads
              SET personal_email = COALESCE(?, personal_email),
                  personal_email_source = COALESCE(?, personal_email_source),
                  contact_email = COALESCE(contact_email, ?)
              WHERE lead_id = ?
            `).run(personalEmail, personalSource, corporateEmail, leadId);
          }

          const updatedLead = getLeadDetail(leadId);
          resolve(NextResponse.json({ success: true, huntResult, leadData: updatedLead }));
        } catch (e: any) {
          resolve(
            NextResponse.json({
              success: code === 0,
              stdout: stdout.trim(),
              stderr: stderr.trim(),
              leadData: getLeadDetail(leadId),
            })
          );
        }
      });
    });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to enrich lead emails' },
      { status: 500 }
    );
  }
}
