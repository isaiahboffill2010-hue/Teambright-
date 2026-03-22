import { describe, it, expect } from 'vitest';
import {
  rule2210_fairBalance,
  rule2241_suitability,
  ruleCANSPAM,
  ruleTaxAdvice,
} from '../rules';

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const CLEAN_INTRO = `
Hi Sarah, my name is Alex Johnson. I specialize in helping venture capital professionals
structure their wealth tax-efficiently. I'd love to share a few ideas in a brief call.
Past performance does not indicate future results. Investment strategies involve risk,
including possible loss of principal. To unsubscribe, click here: 123 Main St, Miami, FL.
`.trim();

// Exceeds 400 words, no disclosure (60 × 7 words = 420 words, strictly > 400)
const LONG_NO_DISCLOSURE = Array(60).fill('This is filler content about investment strategies.').join(' ');

// Contains prohibited guarantees
const GUARANTEED = 'I can guarantee a 20% risk-free return on your investment next quarter.';

// Contains puffery
const PUFFERY = 'Our fund consistently outperforms the market and has never lost money.';

// Contains specific security recommendation
const SPECIFIC_SECURITY = 'I recommend you buy AAPL and invest in TSLA right now.';

// Contains guaranteed tax savings
const GUARANTEED_TAX = 'You will save $50,000 in taxes guaranteed with this strategy.';

// ─── rule2210_fairBalance ─────────────────────────────────────────────────────

describe('rule2210_fairBalance', () => {
  it('clean message: low violation, not triggered', () => {
    const result = rule2210_fairBalance(CLEAN_INTRO);
    expect(result.triggered).toBe(false);
    expect(result.opinion.b).toBeGreaterThan(0.7);
    expect(result.severity).toBe('info');
  });

  it('prohibited guarantee: critical severity, triggered', () => {
    const result = rule2210_fairBalance(GUARANTEED);
    expect(result.triggered).toBe(true);
    expect(result.severity).toBe('critical');
    expect(result.opinion.d).toBeGreaterThan(0.5);
  });

  it('performance puffery: warning severity, triggered', () => {
    const result = rule2210_fairBalance(PUFFERY);
    expect(result.triggered).toBe(true);
    expect(result.severity).toBe('warning');
  });

  it('long content without disclosure: warning severity, triggered', () => {
    const result = rule2210_fairBalance(LONG_NO_DISCLOSURE);
    expect(result.triggered).toBe(true);   // bug-fix assertion — was previously false
    expect(result.severity).toBe('warning');
    expect(result.detail).toMatch(/disclosure/i);
  });

  it('always returns a valid ruleId and regulation', () => {
    const result = rule2210_fairBalance(CLEAN_INTRO);
    expect(result.ruleId).toBe('FINRA-2210');
    expect(result.regulation).toBeTruthy();
  });
});

// ─── rule2241_suitability ─────────────────────────────────────────────────────

describe('rule2241_suitability', () => {
  it('clean message: not triggered', () => {
    const result = rule2241_suitability(CLEAN_INTRO);
    expect(result.triggered).toBe(false);
    expect(result.severity).toBe('info');
    expect(result.opinion.b).toBeGreaterThan(0.7);
  });

  it('specific security recommendation: triggered with warning', () => {
    const result = rule2241_suitability(SPECIFIC_SECURITY);
    expect(result.triggered).toBe(true);
    expect(result.severity).toBe('warning');
    expect(result.opinion.d).toBeGreaterThan(result.opinion.b);
  });

  it('returns correct ruleId', () => {
    expect(rule2241_suitability(CLEAN_INTRO).ruleId).toBe('FINRA-2241');
  });
});

// ─── ruleCANSPAM ─────────────────────────────────────────────────────────────

describe('ruleCANSPAM', () => {
  const ADDR = '123 Main St, Miami, FL';

  it('compliant: unsubscribe link + physical address → not triggered', () => {
    const result = ruleCANSPAM(`Visit ${ADDR}. Click here to unsubscribe.`, true);
    expect(result.triggered).toBe(false);
    expect(result.opinion.b).toBeGreaterThan(0.8);
  });

  it('missing unsubscribe link → critical, triggered', () => {
    const result = ruleCANSPAM(`Visit ${ADDR}.`, false);
    expect(result.triggered).toBe(true);
    expect(result.severity).toBe('critical');
    expect(result.opinion.d).toBeGreaterThan(0.5);
    expect(result.detail).toMatch(/unsubscribe/i);
  });

  it('has unsubscribe but no physical address → triggered', () => {
    const result = ruleCANSPAM('No address here.', true);
    expect(result.triggered).toBe(true);
    expect(result.detail).toMatch(/address/i);
  });

  it('returns correct ruleId', () => {
    expect(ruleCANSPAM(CLEAN_INTRO, true).ruleId).toBe('CAN-SPAM');
  });
});

// ─── ruleTaxAdvice ────────────────────────────────────────────────────────────

describe('ruleTaxAdvice', () => {
  it('clean message: not triggered', () => {
    const result = ruleTaxAdvice(CLEAN_INTRO);
    expect(result.triggered).toBe(false);
    expect(result.severity).toBe('info');
  });

  it('guaranteed tax savings: triggered with critical severity', () => {
    const result = ruleTaxAdvice(GUARANTEED_TAX);
    expect(result.triggered).toBe(true);
    expect(result.severity).toBe('critical');
    expect(result.opinion.d).toBeGreaterThan(result.opinion.b);
  });

  it('returns correct ruleId', () => {
    expect(ruleTaxAdvice(CLEAN_INTRO).ruleId).toBe('TAX-ADVICE');
  });
});
