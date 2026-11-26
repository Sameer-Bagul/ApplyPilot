import { NextResponse } from 'next/server';
import { getDb } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function GET() {
  const startTime = Date.now();
  let dbStatus = 'ok';
  let dbLatencyMs = 0;
  let totalJobs = 0;

  try {
    const db = getDb();
    const queryStart = Date.now();
    const result = db.prepare('SELECT COUNT(*) as c FROM jobs').get() as any;
    dbLatencyMs = Date.now() - queryStart;
    totalJobs = result?.c || 0;
  } catch (err: any) {
    dbStatus = 'degraded';
    console.error('[Health Check DB Error]', err.message);
  }

  const isHealthy = dbStatus === 'ok';

  return NextResponse.json(
    {
      status: isHealthy ? 'healthy' : 'degraded',
      service: 'applypilot-dashboard',
      timestamp: new Date().toISOString(),
      uptimeSeconds: Math.floor(process.uptime()),
      database: {
        status: dbStatus,
        latencyMs: dbLatencyMs,
        totalJobs,
      },
      durationMs: Date.now() - startTime,
    },
    { status: isHealthy ? 200 : 503 }
  );
}
