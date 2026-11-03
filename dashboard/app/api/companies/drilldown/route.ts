import { NextRequest, NextResponse } from 'next/server';
import { getCompanyDetail } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const id = searchParams.get('id') || undefined;
    const name = searchParams.get('name') || undefined;

    if (!id && !name) {
      return NextResponse.json(
        { success: false, error: 'Either id or name query parameter is required' },
        { status: 400 }
      );
    }

    const data = getCompanyDetail({ id, name });
    if (!data) {
      return NextResponse.json(
        { success: false, error: 'Company not found' },
        { status: 404 }
      );
    }

    return NextResponse.json({ success: true, data });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to fetch company drilldown' },
      { status: 500 }
    );
  }
}

