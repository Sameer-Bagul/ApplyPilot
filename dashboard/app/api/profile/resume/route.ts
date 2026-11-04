import { NextResponse } from 'next/server';
import path from 'node:path';
import fs from 'node:fs';
import os from 'node:os';

export const dynamic = 'force-dynamic';

export async function POST(request: Request) {
  try {
    const formData = await request.formData();
    const file = formData.get('resume') as File | null;

    if (!file) {
      return NextResponse.json({ success: false, error: 'No resume file provided' }, { status: 400 });
    }

    const customDir = process.env.APPLYPILOT_DIR;
    const baseDir = customDir || path.join(os.homedir(), '.applypilot');

    if (!fs.existsSync(baseDir)) {
      fs.mkdirSync(baseDir, { recursive: true });
    }

    const originalName = file.name || 'resume.pdf';
    const ext = path.extname(originalName).toLowerCase() || '.pdf';
    const bytes = await file.arrayBuffer();
    const buffer = Buffer.from(bytes);

    let targetFilename = 'resume.pdf';
    if (ext === '.docx') targetFilename = 'resume.docx';
    else if (ext === '.txt') targetFilename = 'resume.txt';

    const targetPath = path.join(baseDir, targetFilename);
    fs.writeFileSync(targetPath, buffer);

    // If it's a text file or we can extract text, also write resume.txt
    if (ext === '.txt') {
      const textContent = buffer.toString('utf-8');
      fs.writeFileSync(path.join(baseDir, 'resume.txt'), textContent);
    }

    return NextResponse.json({
      success: true,
      message: `Resume saved successfully as ${targetFilename}`,
      path: targetPath,
      filename: targetFilename,
      size: buffer.length,
    });
  } catch (err: any) {
    return NextResponse.json({ success: false, error: err.message }, { status: 500 });
  }
}

