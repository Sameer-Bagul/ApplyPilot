import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';

export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json().catch(() => ({}));
    const query = body.query as string | undefined;
    const includeYc = body.includeYc !== false;
    const limit = typeof body.limit === 'number' ? body.limit : 20;

    const projectRoot = path.resolve(process.cwd(), '..');
    const pythonBin = path.join(projectRoot, '.venv', 'bin', 'python');

    const script = `
import json, sys
from applypilot.discovery.tech_company_search_engine import run_tech_company_search_engine

queries = [${JSON.stringify(query)}] if ${JSON.stringify(Boolean(query))} else None
res = run_tech_company_search_engine(
    queries=queries,
    include_yc=${includeYc ? 'True' : 'False'},
    yc_limit=${limit},
    dork_results_limit=10,
    auto_handoff_workers=True,
    max_workers_handoff=5,
)
print(json.dumps(res))
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
            status: 'running_in_background',
            message: 'Search engine running asynchronously in background',
          })
        );
      }, 15000);

      proc.on('close', (code) => {
        clearTimeout(timer);
        try {
          const lines = stdout.trim().split('\n');
          const lastLine = lines[lines.length - 1];
          const parsed = JSON.parse(lastLine);
          resolve(NextResponse.json({ success: true, ...parsed }));
        } catch {
          resolve(
            NextResponse.json({
              success: code === 0,
              stdout: stdout.trim(),
              stderr: stderr.trim(),
            })
          );
        }
      });
    });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to run company search engine' },
      { status: 500 }
    );
  }
}
