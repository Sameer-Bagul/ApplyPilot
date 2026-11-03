import { NextResponse } from 'next/server';
import { getPipelineTelemetry } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const telemetry = getPipelineTelemetry();
    return NextResponse.json({ success: true, ...telemetry });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to fetch pipeline telemetry' },
      { status: 500 }
    );
  }
}
