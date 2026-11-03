import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';

export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json().catch(() => ({}));
    const companyName = body.companyName as string;

    if (!companyName || !companyName.trim()) {
      return NextResponse.json(
        { success: false, error: 'companyName is required' },
        { status: 400 }
      );
    }

    const projectRoot = path.resolve(process.cwd(), '..');
    const pythonBin = path.join(projectRoot, '.venv', 'bin', 'python');

    const script = `
import json, sys
from applypilot.discovery.tech_company_search_engine import deep_research_single_company

res = deep_research_single_company(${JSON.stringify(companyName.trim())})
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
            message: `Deep research for ${companyName} continues in background`,
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
      { success: false, error: error.message || 'Failed to research company' },
      { status: 500 }
    );
  }
}
