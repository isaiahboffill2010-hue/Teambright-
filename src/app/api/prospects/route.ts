import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

export async function POST(request: NextRequest) {
  try {
    const supabase = await createClient();

    const { data: { user }, error: authError } = await supabase.auth.getUser();
    if (authError || !user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await request.json();
    const { firstName, lastName, email, phone, notes, source = 'manual' } = body;

    if (!firstName || !lastName || !email) {
      return NextResponse.json({ error: 'firstName, lastName, and email are required' }, { status: 400 });
    }

    const { data, error } = await supabase
      .from('prospects')
      .insert({
        advisor_id: user.id,
        first_name: firstName,
        last_name: lastName,
        email,
        phone: phone || null,
        notes: notes || '',
        source,
        status: 'new',
        tags: [],
      })
      .select()
      .single();

    if (error) {
      if (error.code === '23505') {
        return NextResponse.json({ error: 'A prospect with this email already exists.' }, { status: 409 });
      }
      return NextResponse.json({ error: error.message }, { status: 500 });
    }

    // Map snake_case DB row back to camelCase Prospect shape
    const prospect = {
      id: data.id,
      advisorId: data.advisor_id,
      firstName: data.first_name,
      lastName: data.last_name,
      email: data.email,
      phone: data.phone ?? undefined,
      status: data.status,
      source: data.source,
      tags: data.tags ?? [],
      notes: data.notes ?? '',
      hasOptedOut: data.has_opted_out,
      hasExplicitConsent: data.has_explicit_consent,
      enrichment: data.enrichment ?? undefined,
      taxProfile: data.tax_profile ?? undefined,
      scoring: data.scoring ?? undefined,
      createdAt: data.created_at,
      updatedAt: data.updated_at,
    };

    return NextResponse.json({ prospect }, { status: 201 });
  } catch {
    return NextResponse.json({ error: 'Failed to create prospect' }, { status: 500 });
  }
}
