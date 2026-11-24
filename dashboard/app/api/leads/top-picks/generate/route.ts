import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'node:child_process';
import path from 'node:path';
import { getPythonBin, getProjectRoot } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json().catch(() => ({}));
    const limit = Math.min(50, Math.max(1, parseInt(body.limit || '15', 10)));
    const minScore = Math.max(0, parseInt(body.minScore || '60', 10));
    const mode = body.mode === 'auto_send' ? 'auto_send' : 'draft';
    const forceResearch = Boolean(body.forceResearch);
    const liveScrape = body.liveScrape !== false;
    const workspace = parseInt(body.workspace || '11', 10);

    const projectRoot = getProjectRoot();
    const pythonBin = getPythonBin();

    const script = `
import json, sys
from applypilot.outreach.mailer import run_top_pick_outreach

res = run_top_pick_outreach(
    limit=${limit},
    min_score=${minScore},
    mode=${JSON.stringify(mode)},
    force_research=${forceResearch ? "True" : "False"},
    live_scrape=${liveScrape ? "True" : "False"},
    workspace=${workspace}
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
        resolve(
          NextResponse.json({
            success: true,
            status: 'running_in_background',
            message: `Top-Pick intelligence gathering & draft generation running in background for ${limit} leads.`,
          })
        );
      }, 35000); // 35-second timeout for multi-company intel + Gemini batching

      proc.on('close', (code) => {
        clearTimeout(timer);
        if (code === 0 && stdout.includes('---AP_RESULT_START---')) {
          try {
            const raw = stdout.split('---AP_RESULT_START---')[1].split('---AP_RESULT_END---')[0].trim();
            const result = JSON.parse(raw);
            resolve(NextResponse.json({
              success: true,
              result,
              message: `Generated drafts for ${result.drafted || result.total_selected || 0} top-pick leads.`,
            }));
            return;
          } catch (e: any) {
            // fallback to raw stdout
          }
        }

        if (code !== 0) {
          resolve(NextResponse.json({
            success: false,
            error: stderr || stdout || `Process exited with code ${code}`,
          }, { status: 500 }));
        } else {
          resolve(NextResponse.json({
            success: true,
            message: `Top-Pick outreach completed.`,
            output: stdout,
          }));
        }
      });
    });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to generate top-pick drafts' },
      { status: 500 }
    );
  }
}
