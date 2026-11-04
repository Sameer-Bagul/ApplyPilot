import { NextResponse } from 'next/server';
import { getCandidateProfile, saveCandidateProfile } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const data = getCandidateProfile();
    return NextResponse.json({ success: true, ...data });
  } catch (err: any) {
    return NextResponse.json({ success: false, error: err.message }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    if (!body || typeof body !== 'object') {
      return NextResponse.json({ success: false, error: 'Invalid profile payload' }, { status: 400 });
    }

    const result = saveCandidateProfile(body);
    if (!result.success) {
      return NextResponse.json({ success: false, error: result.error }, { status: 500 });
    }

    return NextResponse.json({ success: true, message: 'Profile saved successfully' });
  } catch (err: any) {
    return NextResponse.json({ success: false, error: err.message }, { status: 500 });
  }
}
