import { NextRequest, NextResponse } from 'next/server';
import { scoreContent, ScorerInput } from '@/lib/compliance/scorer';

export async function POST(request: NextRequest) {
  try {
    const body: ScorerInput = await request.json();

    if (!body.content && !body.subject) {
      return NextResponse.json({ error: 'content or subject required' }, { status: 400 });
    }

    const score = scoreContent({
      subject: body.subject ?? '',
      content: body.content ?? '',
      hasUnsubscribeLink: body.hasUnsubscribeLink ?? false,
      consent: body.consent ?? { hasExplicitConsent: false, isOptOut: false },
    });

    return NextResponse.json(score);
  } catch (err) {
    return NextResponse.json({ error: 'Invalid request' }, { status: 400 });
  }
}
