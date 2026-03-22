import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const { prospectId, email } = await request.json();

    if (!prospectId) {
      return NextResponse.json({ error: 'prospectId required' }, { status: 400 });
    }

    // In production, integrate with Clay API:
    // const clay = new ClayClient(process.env.CLAY_API_KEY);
    // const data = await clay.enrich({ email });

    // Simulate enrichment response
    await new Promise((r) => setTimeout(r, 800));

    return NextResponse.json({
      prospectId,
      enrichment: {
        enrichedAt: new Date().toISOString(),
        confidenceScore: 0.78 + Math.random() * 0.15,
        source: 'clay',
      },
    });
  } catch {
    return NextResponse.json({ error: 'Enrichment failed' }, { status: 500 });
  }
}
