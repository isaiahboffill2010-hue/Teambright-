import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const { subject, body, recipients, channel } = await request.json();

    if (!subject || !body || !recipients?.length) {
      return NextResponse.json({ error: 'subject, body, and recipients are required' }, { status: 400 });
    }

    // In production, integrate with Resend SDK:
    // const resend = new Resend(process.env.RESEND_API_KEY);
    // await resend.emails.send({ from: '...', to: recipients, subject, html: body });

    // Simulate send
    await new Promise((r) => setTimeout(r, 300));

    return NextResponse.json({
      success: true,
      sentCount: recipients.length,
      channel: channel ?? 'resend',
      sentAt: new Date().toISOString(),
    });
  } catch {
    return NextResponse.json({ error: 'Send failed' }, { status: 500 });
  }
}
