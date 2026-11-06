import { NextRequest, NextResponse } from 'next/server';
import { getHitlTickets, getDb } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const status = searchParams.get('status') || undefined;
    const blocker_type = searchParams.get('blocker_type') || searchParams.get('blocker') || undefined;
    const page = parseInt(searchParams.get('page') || '1', 10);
    const limit = parseInt(searchParams.get('limit') || '25', 10);

    const result = getHitlTickets({ status, blocker_type, page, limit });
    return NextResponse.json({ success: true, ...result });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to fetch HITL tickets' },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const db = getDb();
    const now = new Date().toISOString();

    const info = db.prepare(`
      INSERT INTO hitl_tickets (
        job_url, company, role_title, blocker_type, unanswered_questions_json, status, created_at
      ) VALUES (?, ?, ?, ?, ?, 'sent', ?)
    `).run(
      body.job_url || 'https://applypilot.local',
      body.company || 'Unknown',
      body.role_title || 'Software Engineer',
      body.blocker_type || 'screening_question',
      JSON.stringify(body.questions || []),
      now
    );

    return NextResponse.json({ success: true, ticket_id: Number(info.lastInsertRowid) }, { status: 201 });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to create HITL ticket' },
      { status: 500 }
    );
  }
}

