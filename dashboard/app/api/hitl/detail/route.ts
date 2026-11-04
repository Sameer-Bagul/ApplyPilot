import { NextRequest, NextResponse } from 'next/server';
import { getHitlTicketDetail, resolveHitlTicket, deleteHitlTicket } from '@/lib/db';

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
  try {
    const { searchParams } = new URL(request.url);
    const id = searchParams.get('id');
    const body = await request.json();
    const targetId = parseInt(id || body.ticket_id, 10);

    if (!targetId) {
      return NextResponse.json({ success: false, error: 'ticket_id is required' }, { status: 400 });
    }

    const updated = resolveHitlTicket(targetId, body.answers);
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

