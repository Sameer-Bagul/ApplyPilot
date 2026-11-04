import { NextResponse } from 'next/server';
import { getQaKnowledgeList, saveQaKnowledgeItem, deleteQaKnowledgeItem } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const list = getQaKnowledgeList(200);
    return NextResponse.json({ success: true, list });
  } catch (err: any) {
    return NextResponse.json({ success: false, error: err.message }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { question_text, answer_text, field_type } = body;

    if (!question_text || !answer_text) {
      return NextResponse.json(
        { success: false, error: 'Both question_text and answer_text are required.' },
        { status: 400 }
      );
    }

    const res = saveQaKnowledgeItem({ question_text, answer_text, field_type });
    if (!res.success) {
      return NextResponse.json({ success: false, error: res.error }, { status: 500 });
    }

    return NextResponse.json({ success: true, id: res.id, message: 'Q&A pair saved to knowledge base' });
  } catch (err: any) {
    return NextResponse.json({ success: false, error: err.message }, { status: 500 });
  }
}

export async function DELETE(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const id = searchParams.get('id');

    if (!id) {
      return NextResponse.json({ success: false, error: 'Q&A ID is required.' }, { status: 400 });
    }

    const res = deleteQaKnowledgeItem(Number(id));
    if (!res.success) {
      return NextResponse.json({ success: false, error: res.error }, { status: 500 });
    }

    return NextResponse.json({ success: true, message: 'Q&A pair deleted' });
  } catch (err: any) {
    return NextResponse.json({ success: false, error: err.message }, { status: 500 });
  }
}
