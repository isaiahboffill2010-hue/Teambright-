import { createClient } from '@supabase/supabase-js';
import { NextRequest, NextResponse } from 'next/server';
import { scoreContent } from '@/lib/compliance/scorer';
import type { ConsentParams } from '@/lib/compliance/algebra';

const supabase = createClient(process.env.SUPABASE_URL!, process.env.SUPABASE_ANON_KEY!);

interface ScoreRequest {
  bucket?: string;
  path?: string;
  content?: string;
  subject?: string;
  hasUnsubscribeLink?: boolean;
  consent?: ConsentParams;
}

export async function POST(request: NextRequest) {
  let body: ScoreRequest;

  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Request body must be valid JSON' }, { status: 400 });
  }

  if (!body.bucket && !body.content && !body.subject) {
    return NextResponse.json(
      { error: 'Provide bucket, content, or subject' },
      { status: 400 },
    );
  }

  let content = body.content;
  if (body.bucket && body.path) {
    const { data, error } = await supabase.storage.from(body.bucket).download(body.path);
    if (error) {
      return NextResponse.json({ error: `Failed to fetch content: ${error.message}` }, { status: 500 });
    }
    content = await data.text();
  }

  const score = scoreContent({
    content: content ?? '',
    subject: body.subject ?? '',
    hasUnsubscribeLink: body.hasUnsubscribeLink ?? false,
    consent: body.consent ?? { hasExplicitConsent: false, isOptOut: false },
  });
  return NextResponse.json({ score });
}
