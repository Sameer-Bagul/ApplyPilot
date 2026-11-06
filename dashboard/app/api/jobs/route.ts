import { NextRequest, NextResponse } from 'next/server';
import { getJobs, createJob } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const search = searchParams.get('search') || undefined;
    const route = searchParams.get('route') || undefined;
    const state = searchParams.get('state') || undefined;
    const minScore = searchParams.get('minScore') ? parseInt(searchParams.get('minScore')!, 10) : undefined;
    const location = searchParams.get('location') || undefined;
    const ats = searchParams.get('ats') || searchParams.get('source') || undefined;
    const page = parseInt(searchParams.get('page') || '1', 10);
    const limit = parseInt(searchParams.get('limit') || '25', 10);

    const result = getJobs({ search, route, state, minScore, location, ats, page, limit });
    return NextResponse.json({ success: true, ...result });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to fetch jobs' },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    if (!body.url || !body.title || !body.company) {
      return NextResponse.json(
        { success: false, error: 'url, title, and company are required' },
        { status: 400 }
      );
    }

    const created = createJob(body);
    return NextResponse.json({ success: true, job: created }, { status: 201 });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to create job' },
      { status: 500 }
    );
  }
}
