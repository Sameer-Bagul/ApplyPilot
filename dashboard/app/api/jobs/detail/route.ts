import { NextRequest, NextResponse } from 'next/server';
import { getJobDetail, updateJob, deleteJob } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const url = searchParams.get('url');

    if (!url) {
      return NextResponse.json({ success: false, error: 'url parameter is required' }, { status: 400 });
    }

    const detail = getJobDetail(url);
    if (!detail) {
      return NextResponse.json({ success: false, error: 'Job not found' }, { status: 404 });
    }

    return NextResponse.json({ success: true, ...detail });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to fetch job detail' },
      { status: 500 }
    );
  }
}

export async function PATCH(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const url = searchParams.get('url');
    const body = await request.json();

    const targetUrl = url || body.url;
    if (!targetUrl) {
      return NextResponse.json({ success: false, error: 'Job url is required' }, { status: 400 });
    }

    const updated = updateJob(targetUrl, body);
    return NextResponse.json({ success: true, job: updated });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to update job' },
      { status: 500 }
    );
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const url = searchParams.get('url');

    if (!url) {
      return NextResponse.json({ success: false, error: 'Job url is required' }, { status: 400 });
    }

    deleteJob(url);
    return NextResponse.json({ success: true, message: 'Job deleted successfully' });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to delete job' },
      { status: 500 }
    );
  }
}

