import { NextRequest, NextResponse } from 'next/server';
import { getCompanyDetail, updateCompany, deleteCompany } from '@/lib/db';

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

export async function PATCH(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const id = searchParams.get('id');
    const body = await request.json();
    const targetId = id || body.company_id;

    if (!targetId) {
      return NextResponse.json({ success: false, error: 'company_id is required' }, { status: 400 });
    }

    const updated = updateCompany(targetId, body);
    return NextResponse.json({ success: true, company: updated });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to update company' },
      { status: 500 }
    );
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const id = searchParams.get('id');

    if (!id) {
      return NextResponse.json({ success: false, error: 'id parameter is required' }, { status: 400 });
    }

    deleteCompany(id);
    return NextResponse.json({ success: true, message: 'Company deleted successfully' });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to delete company' },
      { status: 500 }
    );
  }
}
