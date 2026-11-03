import { NextRequest, NextResponse } from 'next/server';
import { getCompanies } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const search = searchParams.get('search') || undefined;
    const sector = searchParams.get('sector') || undefined;
    const stage = searchParams.get('stage') || undefined;
    const vipOnly = searchParams.get('vip') === 'true';
    const page = parseInt(searchParams.get('page') || '1', 10);
    const limit = parseInt(searchParams.get('limit') || '25', 10);

    const result = getCompanies({ search, sector, stage, vipOnly, page, limit });
    return NextResponse.json({ success: true, ...result });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to fetch companies' },
      { status: 500 }
    );
  }
}

