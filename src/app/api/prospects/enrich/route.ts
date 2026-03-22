import { createClient } from '@supabase/supabase-js';
import { NextRequest, NextResponse } from 'next/server';

const supabase = createClient(process.env.SUPABASE_URL!, process.env.SUPABASE_ANON_KEY!);

export async function POST(request: NextRequest) {
  try {
    const { prospectId } = await request.json();

    if (!prospectId) {
      return NextResponse.json({ error: 'prospectId required' }, { status: 400 });
    }

    const { data, error } = await supabase
      .from('prospects')
      .select('*')
      .eq('id', prospectId)
      .single();

    if (error) {
      return NextResponse.json({ error: `Failed to fetch prospect: ${error.message}` }, { status: 500 });
    }

    return NextResponse.json({ prospect: data });
  } catch {
    return NextResponse.json({ error: 'Enrichment failed' }, { status: 500 });
  }
}
