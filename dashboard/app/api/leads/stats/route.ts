import { NextResponse } from 'next/server';
import { getTopPickStats } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const stats = getTopPickStats();
    return NextResponse.json({ success: true, stats });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to fetch outreach stats' },
      { status: 500 }
    );
  }
}
