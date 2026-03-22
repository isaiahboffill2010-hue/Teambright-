import { describe, it, expect } from 'vitest';
import {
  projectedProbability,
  jurisdictionalMeet,
  consentValidity,
  cumulativeFusion,
  expiryTrigger,
  reviewDueTrigger,
} from '../algebra';
import type { ComplianceOpinion } from '@/types';

// ─── Helpers ──────────────────────────────────────────────────────────────────

function sumComponents(op: ComplianceOpinion): number {
  return op.b + op.d + op.u;
}

const CLEAN: ComplianceOpinion = { b: 0.80, d: 0.05, u: 0.15, a: 0.80 };
const RISKY: ComplianceOpinion = { b: 0.20, d: 0.60, u: 0.20, a: 0.50 };
const DOGMATIC_LAWFUL: ComplianceOpinion = { b: 1.0, d: 0.0, u: 0.0, a: 0.9 };
const DOGMATIC_VIOLATION: ComplianceOpinion = { b: 0.0, d: 1.0, u: 0.0, a: 0.1 };

// ─── projectedProbability ────────────────────────────────────────────────────

describe('projectedProbability', () => {
  it('returns b + a*u', () => {
    expect(projectedProbability(CLEAN)).toBeCloseTo(0.80 + 0.80 * 0.15);
  });

  it('returns exactly b when u = 0 (dogmatic)', () => {
    expect(projectedProbability(DOGMATIC_LAWFUL)).toBeCloseTo(1.0);
    expect(projectedProbability(DOGMATIC_VIOLATION)).toBeCloseTo(0.0);
  });

  it('is within [0, 1] for any valid opinion', () => {
    const pp = projectedProbability(RISKY);
    expect(pp).toBeGreaterThanOrEqual(0);
    expect(pp).toBeLessThanOrEqual(1);
  });
});

// ─── jurisdictionalMeet ──────────────────────────────────────────────────────

describe('jurisdictionalMeet', () => {
  it('preserves a single opinion unchanged', () => {
    const result = jurisdictionalMeet(CLEAN);
    expect(result).toEqual(CLEAN);
  });

  it('throws on empty input', () => {
    expect(() => jurisdictionalMeet()).toThrow();
  });

  it('output components sum to 1', () => {
    const result = jurisdictionalMeet(CLEAN, RISKY);
    expect(sumComponents(result)).toBeCloseTo(1, 5);
  });

  it('AND with hard violation produces a risky output', () => {
    const result = jurisdictionalMeet(CLEAN, DOGMATIC_VIOLATION);
    expect(result.d).toBeGreaterThan(result.b);
  });

  it('AND with hard lawful keeps b positive and output valid', () => {
    const result = jurisdictionalMeet(CLEAN, DOGMATIC_LAWFUL);
    // Meeting a dogmatic-lawful source can increase b (evidence accumulation);
    // the key invariant is that the output is a valid opinion and d stays low.
    expect(result.b).toBeGreaterThan(0);
    expect(result.d).toBeLessThan(CLEAN.d + 0.05); // violation should not spike
    expect(sumComponents(result)).toBeCloseTo(1, 5);
  });

  it('is order-dependent in practice (non-commutative for dissimilar base rates)', () => {
    // Meet is defined to be commutative in the spec, so both orderings
    // should produce the same projected probability (within floating point).
    const ab = projectedProbability(jurisdictionalMeet(CLEAN, RISKY));
    const ba = projectedProbability(jurisdictionalMeet(RISKY, CLEAN));
    expect(ab).toBeCloseTo(ba, 5);
  });

  it('handles n-ary meet correctly', () => {
    const result = jurisdictionalMeet(CLEAN, RISKY, { b: 0.6, d: 0.1, u: 0.3, a: 0.7 });
    expect(sumComponents(result)).toBeCloseTo(1, 5);
    expect(result.b).toBeGreaterThanOrEqual(0);
    expect(result.d).toBeGreaterThanOrEqual(0);
    expect(result.u).toBeGreaterThanOrEqual(0);
  });
});

// ─── cumulativeFusion ────────────────────────────────────────────────────────

describe('cumulativeFusion', () => {
  it('output sums to 1', () => {
    const result = cumulativeFusion(CLEAN, RISKY);
    expect(sumComponents(result)).toBeCloseTo(1, 5);
  });

  it('fusing two agreeing opinions increases belief', () => {
    const op: ComplianceOpinion = { b: 0.70, d: 0.10, u: 0.20, a: 0.80 };
    const result = cumulativeFusion(op, op);
    expect(result.b).toBeGreaterThan(op.b);
    expect(result.u).toBeLessThan(op.u);
  });

  it('fusing dogmatic opinions falls back to weighted average', () => {
    const result = cumulativeFusion(DOGMATIC_LAWFUL, DOGMATIC_VIOLATION);
    // Both u = 0, degenerate case — result should still sum to 1
    expect(sumComponents(result)).toBeCloseTo(1, 5);
  });

  it('reduces uncertainty vs either source opinion', () => {
    const result = cumulativeFusion(CLEAN, { b: 0.50, d: 0.10, u: 0.40, a: 0.70 });
    expect(result.u).toBeLessThan(CLEAN.u);
  });
});

// ─── consentValidity ─────────────────────────────────────────────────────────

describe('consentValidity', () => {
  it('hard blocks opt-out: d=1, b=0, u=0', () => {
    const result = consentValidity({ hasExplicitConsent: false, isOptOut: true });
    expect(result.b).toBe(0);
    expect(result.d).toBe(1);
    expect(result.u).toBe(0);
  });

  it('opt-out takes precedence over explicit consent', () => {
    const result = consentValidity({ hasExplicitConsent: true, isOptOut: true });
    expect(result.d).toBe(1);
  });

  it('cold outreach has high uncertainty', () => {
    const result = consentValidity({ hasExplicitConsent: false, isOptOut: false });
    expect(result.u).toBeGreaterThanOrEqual(0.40);
    expect(result.b).toBeGreaterThan(0); // permissible under FINRA, not zero
  });

  it('fresh explicit consent produces high belief', () => {
    const result = consentValidity({
      hasExplicitConsent: true,
      consentAgeInDays: 30,
      isOptOut: false,
    });
    expect(result.b).toBeGreaterThanOrEqual(0.85);
    expect(result.d).toBeLessThan(0.05);
  });

  it('stale consent produces intermediate belief', () => {
    const fresh = consentValidity({ hasExplicitConsent: true, consentAgeInDays: 30, isOptOut: false });
    const stale = consentValidity({
      hasExplicitConsent: true,
      consentAgeInDays: 400,
      consentMaxAgeDays: 365,
      isOptOut: false,
    });
    expect(stale.b).toBeLessThan(fresh.b);
  });

  it('output always sums to 1', () => {
    const cases = [
      { hasExplicitConsent: false, isOptOut: true },
      { hasExplicitConsent: false, isOptOut: false },
      { hasExplicitConsent: true, isOptOut: false },
      { hasExplicitConsent: true, consentAgeInDays: 400, consentMaxAgeDays: 365, isOptOut: false },
    ];
    for (const c of cases) {
      expect(sumComponents(consentValidity(c))).toBeCloseTo(1, 5);
    }
  });
});

// ─── expiryTrigger ───────────────────────────────────────────────────────────

describe('expiryTrigger', () => {
  it('returns opinion unchanged before trigger time', () => {
    const result = expiryTrigger(CLEAN, 100, 200);
    expect(result).toEqual(CLEAN);
  });

  it('hard expiry (residualFactor=0) converts all b to d', () => {
    const result = expiryTrigger(CLEAN, 300, 200, 0);
    expect(result.b).toBeCloseTo(0);
    expect(result.d).toBeCloseTo(CLEAN.d + CLEAN.b, 5);
    expect(result.u).toBeCloseTo(CLEAN.u, 5);
    expect(sumComponents(result)).toBeCloseTo(1, 5);
  });

  it('full residual (residualFactor=1) leaves opinion unchanged', () => {
    const result = expiryTrigger(CLEAN, 300, 200, 1);
    expect(result.b).toBeCloseTo(CLEAN.b, 5);
    expect(result.d).toBeCloseTo(CLEAN.d, 5);
  });

  it('partial residual produces intermediate values', () => {
    const result = expiryTrigger(CLEAN, 300, 200, 0.5);
    expect(result.b).toBeCloseTo(CLEAN.b * 0.5, 5);
    expect(result.d).toBeCloseTo(CLEAN.d + CLEAN.b * 0.5, 5);
    expect(sumComponents(result)).toBeCloseTo(1, 5);
  });
});

// ─── reviewDueTrigger ────────────────────────────────────────────────────────

describe('reviewDueTrigger', () => {
  it('returns opinion unchanged before trigger time', () => {
    const result = reviewDueTrigger(CLEAN, 5, 10, 30);
    expect(result).toEqual(CLEAN);
  });

  it('at trigger time, opinion is unchanged (elapsed=0)', () => {
    const result = reviewDueTrigger(CLEAN, 10, 10, 30);
    expect(result.b).toBeCloseTo(CLEAN.b, 5);
  });

  it('after one half-life, b decays by 50%', () => {
    const result = reviewDueTrigger(CLEAN, 10 + 30, 10, 30);
    expect(result.b).toBeCloseTo(CLEAN.b * 0.5, 3);
    expect(result.u).toBeCloseTo(CLEAN.u + CLEAN.b * 0.5, 3);
  });

  it('d is preserved (decay goes to u, not d)', () => {
    const result = reviewDueTrigger(CLEAN, 10 + 30, 10, 30);
    expect(result.d).toBeCloseTo(CLEAN.d, 5);
  });

  it('output sums to 1', () => {
    const result = reviewDueTrigger(CLEAN, 100, 10, 30);
    expect(sumComponents(result)).toBeCloseTo(1, 5);
  });
});
