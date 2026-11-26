import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';
import { getPythonBin, getProjectRoot } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json().catch(() => ({}));
    const mode = body.mode || 'single';
    const companyName = body.companyName as string | undefined;
    const domain = body.domain as string | undefined;
    const minEmails = typeof body.minEmails === 'number' ? body.minEmails : 5;
    const tier = typeof body.tier === 'number' ? body.tier : 1;
    const limit = typeof body.limit === 'number' ? body.limit : 50;
    const enrichEmails = body.enrich !== false;
    const pollJobs = body.pollJobs !== false;

    const projectRoot = getProjectRoot();
    const pythonBin = getPythonBin();

    let script = '';
    if (mode === 'batch') {
      script = `
import json, sys
from applypilot.discovery.company_deep_looper import loop_all_watchlist_companies

try:
    summary = loop_all_watchlist_companies(
        priority_tier=${tier},
        limit=${limit},
        target_emails=${minEmails},
        enrich_emails=${enrichEmails ? 'True' : 'False'},
        poll_jobs=${pollJobs ? 'True' : 'False'}
    )
    print(json.dumps({"success": True, "summary": summary}))
except Exception as e:
    print(json.dumps({"success": False, "error": str(e)}))
`;
    } else {
      if (!companyName || !companyName.trim()) {
        return NextResponse.json(
          { success: false, error: 'companyName is required for single company enrichment' },
          { status: 400 }
        );
      }

      script = `
import json, sys
from applypilot.discovery.web_and_social_recruiter_harvester import enrich_company_deep

try:
    res = enrich_company_deep(
        ${JSON.stringify(companyName.trim())},
        domain=${JSON.stringify(domain?.trim() || '')},
        target_count=${minEmails}
    )
    print(json.dumps({"success": True, "result": res}))
except Exception as e:
    print(json.dumps({"success": False, "error": str(e)}))
`;
    }

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

      // Allow 20s for single and initial response, or notify background execution
      const timer = setTimeout(() => {
        resolve(
          NextResponse.json({
            success: true,
            status: 'running_in_background',
            message: mode === 'batch'
              ? `Deep looping across Tier ${tier} (limit: ${limit}) is running in background.`
              : `Deep email discovery for ${companyName} is running in background.`,
          })
        );
      }, 15000);

      proc.on('close', (code) => {
        clearTimeout(timer);
        try {
          const lines = stdout.trim().split('\n');
          const lastLine = lines[lines.length - 1];
          const parsed = JSON.parse(lastLine);
          resolve(NextResponse.json(parsed));
        } catch {
          resolve(
            NextResponse.json({
              success: code === 0,
              stdout: stdout.trim(),
              stderr: stderr.trim(),
              status: code === 0 ? 'completed' : 'failed',
            })
          );
        }
      });
    });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to trigger enrichment' },
      { status: 500 }
    );
  }
}
