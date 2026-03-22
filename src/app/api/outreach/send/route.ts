import { NextRequest, NextResponse } from 'next/server';
import { Resend } from 'resend';

const resend = new Resend(process.env.RESEND_API_KEY);

export async function POST(request: NextRequest) {
  try {
    const { subject, body, recipients } = await request.json() as {
      subject: string;
      body: string;
      recipients: { email: string; firstName: string; lastName: string }[];
    };

    if (!subject || !body || !recipients?.length) {
      return NextResponse.json({ error: 'subject, body, and recipients are required' }, { status: 400 });
    }

    if (!process.env.RESEND_API_KEY || process.env.RESEND_API_KEY === 're_your_resend_api_key_here') {
      return NextResponse.json({ error: 'RESEND_API_KEY is not configured' }, { status: 500 });
    }

    const results = await Promise.allSettled(
      recipients.map((r) => {
        const personalizedBody = body
          .replace(/\{\{first_name\}\}/g, r.firstName)
          .replace(/\{\{last_name\}\}/g, r.lastName);

        return resend.emails.send({
          from: 'AdvisorFlow <onboarding@resend.dev>',
          to: r.email,
          subject,
          text: personalizedBody,
        });
      })
    );

    const sentCount = results.filter((r) => r.status === 'fulfilled').length;
    const failedCount = results.length - sentCount;

    return NextResponse.json({
      success: true,
      sentCount,
      failedCount,
      sentAt: new Date().toISOString(),
    });
  } catch {
    return NextResponse.json({ error: 'Send failed' }, { status: 500 });
  }
}
