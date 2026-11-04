import { NextRequest, NextResponse } from 'next/server';
import { rejectLead } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { lead_id, lead_ids } = body;

    if (lead_ids && Array.isArray(lead_ids)) {
      const results = lead_ids.map((id) => rejectLead(id));
      return NextResponse.json({ success: true, count: results.length, leads: results });
    }

    if (!lead_id) {
      return NextResponse.json({ success: false, error: 'lead_id or lead_ids is required' }, { status: 400 });
    }

    const updated = rejectLead(lead_id);
    return NextResponse.json({ success: true, lead: updated });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to reject lead' },
      { status: 500 }
    );
  }
}

