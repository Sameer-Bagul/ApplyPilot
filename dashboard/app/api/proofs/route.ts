import { NextRequest, NextResponse } from 'next/server';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { getDb } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const jobUrl = searchParams.get('job_url') || searchParams.get('url');
    const type = (searchParams.get('type') || 'video').toLowerCase();
    const explicitPath = searchParams.get('path');
    const isDownload = searchParams.get('download') === '1' || searchParams.get('download') === 'true';

    let filePath: string | null = null;

    if (explicitPath) {
      filePath = explicitPath;
    } else if (jobUrl) {
      const db = getDb();
      const job: any = db.prepare(
        'SELECT url, company, title, proof_video_path, proof_screenshot_path FROM jobs WHERE url = ?'
      ).get(jobUrl);

      if (job) {
        if (type === 'screenshot') {
          filePath = job.proof_screenshot_path;
        } else {
          filePath = job.proof_video_path;
        }

        // Fallback: search directory for matching filename if column empty
        if (!filePath) {
          const proofsDir = path.join(
            os.homedir(),
            '.applypilot',
            'proofs',
            type === 'screenshot' ? 'screenshots' : 'videos'
          );
          if (fs.existsSync(proofsDir)) {
            const ext = type === 'screenshot' ? '.png' : '.webm';
            const cleanCo = (job.company || '').replace(/[^a-zA-Z0-9_-]/g, '_').slice(0, 30);
            const files = fs.readdirSync(proofsDir).filter(f => f.endsWith(ext));
            if (cleanCo) {
              const matched = files.find(f => f.toLowerCase().includes(cleanCo.toLowerCase()));
              if (matched) {
                filePath = path.join(proofsDir, matched);
              }
            }
          }
        }
      }
    }

    if (!filePath) {
      return NextResponse.json(
        { success: false, error: 'No proof recording found for this job' },
        { status: 404 }
      );
    }

    const resolved = path.resolve(filePath);
    const allowedRoot = path.resolve(os.homedir(), '.applypilot');

    // Security check: prevent directory traversal
    if (!resolved.startsWith(allowedRoot)) {
      return NextResponse.json(
        { success: false, error: 'Access denied: path outside allowed proofs storage' },
        { status: 403 }
      );
    }

    if (!fs.existsSync(resolved)) {
      return NextResponse.json(
        { success: false, error: 'Proof file does not exist on disk', path: resolved },
        { status: 404 }
      );
    }

    const stat = fs.statSync(resolved);
    const fileSize = stat.size;
    const filename = path.basename(resolved);

    // 1. Image Screenshot serving
    if (type === 'screenshot' || resolved.endsWith('.png') || resolved.endsWith('.jpg')) {
      const contentType = resolved.endsWith('.jpg') || resolved.endsWith('.jpeg') ? 'image/jpeg' : 'image/png';
      const fileBuffer = fs.readFileSync(resolved);

      const headers: Record<string, string> = {
        'Content-Type': contentType,
        'Content-Length': String(fileBuffer.length),
        'Cache-Control': 'public, max-age=3600',
      };

      if (isDownload) {
        headers['Content-Disposition'] = `attachment; filename="${filename}"`;
      }

      return new Response(fileBuffer, { status: 200, headers });
    }

    // 2. 720p WebM Video streaming with HTTP 206 Partial Content support (crucial for scrubbing/seeking)
    const rangeHeader = request.headers.get('range');
    const contentType = resolved.endsWith('.mp4') ? 'video/mp4' : 'video/webm';

    if (rangeHeader) {
      const parts = rangeHeader.replace(/bytes=/, '').split('-');
      const start = parseInt(parts[0], 10);
      const end = parts[1] ? parseInt(parts[1], 10) : fileSize - 1;

      if (start >= fileSize || end >= fileSize) {
        return new Response(null, {
          status: 416,
          headers: {
            'Content-Range': `bytes */${fileSize}`,
          },
        });
      }

      const chunkSize = end - start + 1;
      const fileStream = fs.createReadStream(resolved, { start, end });

      const readableStream = new ReadableStream({
        start(controller) {
          fileStream.on('data', (chunk) => controller.enqueue(chunk));
          fileStream.on('end', () => controller.close());
          fileStream.on('error', (err) => controller.error(err));
        },
        cancel() {
          fileStream.destroy();
        },
      });

      const headers: Record<string, string> = {
        'Content-Range': `bytes ${start}-${end}/${fileSize}`,
        'Accept-Ranges': 'bytes',
        'Content-Length': String(chunkSize),
        'Content-Type': contentType,
        'Cache-Control': 'no-cache',
      };

      if (isDownload) {
        headers['Content-Disposition'] = `attachment; filename="${filename}"`;
      }

      return new Response(readableStream, {
        status: 206,
        headers,
      });
    } else {
      const fileStream = fs.createReadStream(resolved);
      const readableStream = new ReadableStream({
        start(controller) {
          fileStream.on('data', (chunk) => controller.enqueue(chunk));
          fileStream.on('end', () => controller.close());
          fileStream.on('error', (err) => controller.error(err));
        },
        cancel() {
          fileStream.destroy();
        },
      });

      const headers: Record<string, string> = {
        'Accept-Ranges': 'bytes',
        'Content-Length': String(fileSize),
        'Content-Type': contentType,
        'Cache-Control': 'no-cache',
      };

      if (isDownload) {
        headers['Content-Disposition'] = `attachment; filename="${filename}"`;
      }

      return new Response(readableStream, {
        status: 200,
        headers,
      });
    }
  } catch (err: any) {
    return NextResponse.json(
      { success: false, error: err.message || 'Failed to serve proof media' },
      { status: 500 }
    );
  }
}
