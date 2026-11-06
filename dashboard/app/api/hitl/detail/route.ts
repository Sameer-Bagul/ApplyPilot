import { NextRequest, NextResponse } from 'next/server';
import { getHitlTicketDetail, resolveHitlTicket, deleteHitlTicket, getDb } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const id = searchParams.get('id');

    if (!id) {
      return NextResponse.json({ success: false, error: 'id is required' }, { status: 400 });
    }

    const ticket = getHitlTicketDetail(parseInt(id, 10));
    if (!ticket) {
      return NextResponse.json({ success: false, error: 'Ticket not found' }, { status: 404 });
    }

    return NextResponse.json({ success: true, ticket });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to fetch ticket detail' },
      { status: 500 }
    );
  }
}

export async function PATCH(request: NextRequest) {
  return handleResolution(request);
}

export async function POST(request: NextRequest) {
  return handleResolution(request);
}

async function handleResolution(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const id = searchParams.get('id');
    const body = await request.json();
    const targetId = parseInt(id || body.ticket_id, 10);
    const action = body.action || 'resolved';

    if (!targetId) {
      return NextResponse.json({ success: false, error: 'ticket_id is required' }, { status: 400 });
    }

    const db = getDb();
    const now = new Date().toISOString();

    if (action === 'dismissed') {
      db.prepare("UPDATE hitl_tickets SET status = 'dismissed', resolved_at = ? WHERE ticket_id = ?").run(now, targetId);
      return NextResponse.json({ success: true, message: 'Ticket dismissed' });
    }

    // Resolve ticket with provided answers
    const answers = body.answers || {};
    const ticket: any = db.prepare('SELECT * FROM hitl_tickets WHERE ticket_id = ?').get(targetId);

    if (ticket) {
      // 1. Auto-learn answers into qa_knowledge so future jobs automatically resolve these questions
      if (answers && Object.keys(answers).length > 0) {
        let questions: any[] = [];
        try {
          if (ticket.unanswered_questions_json) questions = JSON.parse(ticket.unanswered_questions_json);
        } catch {}

        for (const [key, answerVal] of Object.entries(answers)) {
          if (!answerVal) continue;
          const matchedQ = questions.find((q: any) => (q.field_id === key || q.label === key));
          const questionText = matchedQ?.label || key;
          const fieldType = matchedQ?.field_type || 'text';

          try {
            db.prepare(`
              INSERT INTO qa_knowledge (
                question_text, canonical_question, answer_text, answer_source, source, field_type, created_at, updated_at
              ) VALUES (?, ?, ?, 'hitl_resolution', 'human_intervention', ?, ?, ?)
            `).run(questionText, questionText, String(answerVal), fieldType, now, now);
          } catch {}
        }
      }

      // 2. Mark ticket resolved
      db.prepare("UPDATE hitl_tickets SET status = 'resolved', resolved_at = ? WHERE ticket_id = ?").run(now, targetId);

      // 3. Update job state to 'ready' or queue for apply replay
      if (ticket.job_url) {
        db.prepare("UPDATE jobs SET state = 'ready', needs_human_reason = NULL WHERE url = ?").run(ticket.job_url);
      }
    }

    const updated = getHitlTicketDetail(targetId);
    return NextResponse.json({ success: true, ticket: updated });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to update ticket' },
      { status: 500 }
    );
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const id = searchParams.get('id');

    if (!id) {
      return NextResponse.json({ success: false, error: 'id is required' }, { status: 400 });
    }

    deleteHitlTicket(parseInt(id, 10));
    return NextResponse.json({ success: true, message: 'Ticket deleted successfully' });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to delete ticket' },
      { status: 500 }
    );
  }
}

