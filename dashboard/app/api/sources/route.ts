import { NextResponse } from 'next/server';
import { getSourcesStats } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const data = getSourcesStats();
    return NextResponse.json({ success: true, ...data });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to fetch sources stats' },
      { status: 500 }
    );
  }
}

