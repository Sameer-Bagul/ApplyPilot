import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs';
import { getCompanyDetail } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json().catch(() => ({}));
    const companyName = body.companyName || body.company_name;

    if (!companyName || typeof companyName !== 'string') {
      return NextResponse.json(
        { success: false, error: 'companyName is required' },
        { status: 400 }
      );
    }

    const projectRoot = path.resolve(process.cwd(), '..');
    const venvPython = path.join(projectRoot, '.venv', 'bin', 'python');
    const pythonBin = fs.existsSync(venvPython) ? venvPython : 'python3';

    const script = `
import json, sys
from applypilot.discovery.company_osint import investigate_and_store_company

res = investigate_and_store_company(${JSON.stringify(companyName.trim())})
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
            status: 'timeout_or_background',
            company: getCompanyDetail({ name: companyName.trim() }),
          })
        );
      }, 12000);

      proc.on('close', (code) => {
        clearTimeout(timer);
        try {
          const match = stdout.match(/__RESULT__(.*)$/m);
          let investigation = null;
          if (match && match[1]) {
            investigation = JSON.parse(match[1]);
          }
          const updated = getCompanyDetail({ name: companyName.trim() });
          resolve(NextResponse.json({ success: true, investigation, companyData: updated }));
        } catch (e: any) {
          resolve(
            NextResponse.json({
              success: code === 0,
              stdout: stdout.trim(),
              stderr: stderr.trim(),
              companyData: getCompanyDetail({ name: companyName.trim() }),
            })
          );
        }
      });
    });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to investigate company' },
      { status: 500 }
    );
  }
}

