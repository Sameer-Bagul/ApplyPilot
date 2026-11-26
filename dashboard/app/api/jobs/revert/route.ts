import { NextRequest, NextResponse } from 'next/server';
import { getDb } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const targetUrl = body.url || body.jobUrl || body.job_url;
    const targetId = body.job_id || body.jobId || body.id;

    if (!targetUrl && !targetId) {
      return NextResponse.json(
        { success: false, error: 'url, jobUrl, or job_id is required' },
        { status: 400 }
      );
    }

    const db = getDb();
    let updated = false;

    if (targetUrl) {
      db.prepare(`
        UPDATE jobs
        SET state = 'ready_to_apply',
            apply_status = 'ready',
            applied_at = NULL,
            needs_human_reason = 'reverted_by_user_proof_inspected'
        WHERE url = ?
      `).run(targetUrl);
      updated = true;
    } else if (targetId) {
      db.prepare(`
        UPDATE jobs
        SET state = 'ready_to_apply',
            apply_status = 'ready',
            applied_at = NULL,
            needs_human_reason = 'reverted_by_user_proof_inspected'
        WHERE rowid = ? OR url = ?
      `).run(targetId, String(targetId));
      updated = true;
    }

    return NextResponse.json({
      success: true,
      message: 'Job status successfully reverted to ready_to_apply',
      target: targetUrl || targetId,
    });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to revert job status' },
      { status: 500 }
    );
  }
}
