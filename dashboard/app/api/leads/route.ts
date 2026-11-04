import { NextRequest, NextResponse } from 'next/server';
import { getLeads, createLead } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const search = searchParams.get('search') || undefined;
    const type = searchParams.get('type') || undefined;
    const status = searchParams.get('status') || undefined;
    const page = parseInt(searchParams.get('page') || '1', 10);
    const limit = parseInt(searchParams.get('limit') || '25', 10);

    const result = getLeads({ search, type, status, page, limit });
    return NextResponse.json({ success: true, ...result });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to fetch leads' },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    if (!body.company_name || !body.contact_email) {
      return NextResponse.json(
        { success: false, error: 'company_name and contact_email are required' },
        { status: 400 }
      );
    }

    const created = createLead(body);
    return NextResponse.json({ success: true, lead: created }, { status: 201 });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to create recruiter lead' },
      { status: 500 }
    );
  }
}
