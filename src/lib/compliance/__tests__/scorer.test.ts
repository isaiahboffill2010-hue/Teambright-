import { describe, it, expect } from 'vitest';
import { scoreContent } from '../scorer';

// ─── Integration: scoreContent ────────────────────────────────────────────────

const GOOD_EMAIL = `
Hi Sarah,

My name is Alex Johnson. I work with venture capital professionals to build tax-efficient
investment strategies. Given current market conditions, I'd love to share a few ideas in
a brief 20-minute call — no obligations.

Past performance does not indicate future results. Investment strategies involve risk,
including possible loss of principal. This message is for informational purposes only.

Best regards, Alex Johnson | Meridian Wealth | 123 Main St, Miami, FL 33101

To unsubscribe, click here: {{unsubscribe_link}}
`.trim();

const BLOCKED_EMAIL = `
I guarantee a 25% risk-free return. No risk involved. You will save $100,000 in taxes guaranteed.
Buy TSLA right now. This is a sure-thing investment.
`.trim();

describe('scoreContent', () => {
  it('clean compliant email with consent scores as low risk', () => {
    const score = scoreContent({
      subject: 'A brief note from Alex Johnson',
      content: GOOD_EMAIL,
      hasUnsubscribeLink: true,
      consent: { hasExplicitConsent: true, consentAgeInDays: 30, isOptOut: false },
    });

    expect(score.riskLevel).toBe('low');
    expect(score.autoBlocked).toBe(false);
    expect(score.requiresReview).toBe(false);
    expect(score.projectedProbability).toBeGreaterThan(0.65);
    expect(score.triggeredRules).toHaveLength(0);
    expect(score.scoredAt).toBeTruthy();
  });

  it('email with prohibited claims is blocked', () => {
    const score = scoreContent({
      subject: 'Guaranteed returns',
      content: BLOCKED_EMAIL,
      hasUnsubscribeLink: false,
      consent: { hasExplicitConsent: false, isOptOut: false },
    });

    expect(score.riskLevel).toBe('blocked');
    expect(score.autoBlocked).toBe(true);
    expect(score.projectedProbability).toBeLessThan(0.5);
    expect(score.triggeredRules.length).toBeGreaterThan(0);
  });

  it('opt-out recipient always blocks regardless of content', () => {
    const score = scoreContent({
      subject: 'Clean subject',
      content: GOOD_EMAIL,
      hasUnsubscribeLink: true,
      consent: { hasExplicitConsent: false, isOptOut: true },
    });

    // d=1 from consent meet drives d high → blocked
    expect(score.autoBlocked).toBe(true);
    expect(score.riskLevel).toBe('blocked');
  });

  it('medium risk email (no consent, no unsubscribe) requires review', () => {
    const score = scoreContent({
      subject: 'Investment ideas for your portfolio',
      content: 'Hi John, I wanted to share some investment ideas with you.',
      hasUnsubscribeLink: false,
      consent: { hasExplicitConsent: false, isOptOut: false },
    });

    // No unsubscribe → CAN-SPAM critical → should require review or block
    expect(score.requiresReview || score.autoBlocked).toBe(true);
    expect(score.triggeredRules.some((r) => r.ruleId === 'CAN-SPAM')).toBe(true);
  });

  it('opinion always sums to 1', () => {
    const score = scoreContent({
      subject: 'Test',
      content: GOOD_EMAIL,
      hasUnsubscribeLink: true,
      consent: { hasExplicitConsent: true, isOptOut: false },
    });
    const { b, d, u } = score.opinion;
    expect(b + d + u).toBeCloseTo(1, 5);
  });

  it('triggered rules contain required fields', () => {
    const score = scoreContent({
      subject: 'Guaranteed returns',
      content: BLOCKED_EMAIL,
      hasUnsubscribeLink: false,
      consent: { hasExplicitConsent: false, isOptOut: false },
    });

    for (const rule of score.triggeredRules) {
      expect(rule.ruleId).toBeTruthy();
      expect(rule.ruleName).toBeTruthy();
      expect(rule.severity).toMatch(/^(info|warning|critical)$/);
      expect(rule.regulation).toBeTruthy();
      expect(rule.description).toBeTruthy();
    }
  });

  it('projectedProbability is rounded to 3 decimal places', () => {
    const score = scoreContent({
      subject: 'Test',
      content: GOOD_EMAIL,
      hasUnsubscribeLink: true,
      consent: { hasExplicitConsent: true, isOptOut: false },
    });
    const str = score.projectedProbability.toString();
    const decimals = str.includes('.') ? str.split('.')[1].length : 0;
    expect(decimals).toBeLessThanOrEqual(3);
  });
});
