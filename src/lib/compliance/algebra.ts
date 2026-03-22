/**
 * Compliance Algebra — TypeScript port of Subjective Logic operators.
 *
 * Grounded in Jøsang's Subjective Logic and FINRA/SEC regulatory requirements.
 * ComplianceOpinion ω = (b, d, u, a) where b + d + u = 1.
 *   b = belief    — evidence of lawfulness
 *   d = disbelief — evidence of violation
 *   u = uncertainty
 *   a = base rate (prior probability of compliance)
 *
 * Projected probability: P(ω) = b + a·u
 */

import { ComplianceOpinion } from '@/types';

// ─── Validation ────────────────────────────────────────────────────────────

export function validateOpinion(op: ComplianceOpinion): void {
  const sum = op.b + op.d + op.u;
  if (Math.abs(sum - 1.0) > 1e-6) {
    throw new Error(`Opinion components must sum to 1, got ${sum.toFixed(6)}`);
  }
  if ([op.b, op.d, op.u, op.a].some((v) => v < 0 || v > 1)) {
    throw new Error('All opinion components must be in [0, 1]');
  }
}

// ─── Projected Probability ─────────────────────────────────────────────────

/** E(X) = b + a·u — the scalar expectation of lawfulness. */
export function projectedProbability(op: ComplianceOpinion): number {
  return op.b + op.a * op.u;
}

// ─── §5 Jurisdictional Meet ────────────────────────────────────────────────

/**
 * Binary jurisdictional meet (AND / conjunction).
 * Models compliance across two independent jurisdictions:
 *   lawfulness requires BOTH to be satisfied.
 *
 * Based on Jøsang SL conjunction (Definition 9):
 *   u_AND = (u_A * u_B) / (1 - a_A * a_B)
 *   b_AND = b_A*b_B + ((1-a_B)*b_A*u_B + (1-a_A)*u_A*b_B) / denom
 *   d_AND = 1 - b_AND - u_AND
 *   a_AND = a_A * a_B
 */
function jurisdictionalMeetPair(
  opA: ComplianceOpinion,
  opB: ComplianceOpinion,
): ComplianceOpinion {
  const denom = 1 - opA.a * opB.a;

  if (Math.abs(denom) < 1e-10) {
    // Both base rates ≈ 1: degenerate case
    return clamp({
      b: opA.b * opB.b,
      d: Math.max(opA.d, opB.d),
      u: 0,
      a: 1,
    });
  }

  const u = (opA.u * opB.u) / denom;
  const b =
    opA.b * opB.b +
    ((1 - opB.a) * opA.b * opB.u + (1 - opA.a) * opA.u * opB.b) / denom;
  const d = Math.max(0, 1 - b - u);
  const a = opA.a * opB.a;

  return clamp({ b, d, u, a });
}

/** N-ary jurisdictional meet via left-fold. */
export function jurisdictionalMeet(...opinions: ComplianceOpinion[]): ComplianceOpinion {
  if (opinions.length === 0) throw new Error('jurisdictionalMeet requires ≥1 opinion');
  if (opinions.length === 1) return opinions[0];
  return opinions.reduce((acc, op) => jurisdictionalMeetPair(acc, op));
}

// ─── §7 Consent Validity ───────────────────────────────────────────────────

export interface ConsentParams {
  hasExplicitConsent: boolean;
  consentAgeInDays?: number;
  consentMaxAgeDays?: number;
  isOptOut: boolean;
}

/**
 * Consent validity opinion.
 * Hard block on opt-out; high uncertainty without explicit consent;
 * near-certain lawfulness with fresh explicit consent.
 */
export function consentValidity(params: ConsentParams): ComplianceOpinion {
  const { hasExplicitConsent, consentAgeInDays, consentMaxAgeDays = 365, isOptOut } = params;

  if (isOptOut) return { b: 0, d: 1, u: 0, a: 0 };

  if (!hasExplicitConsent) {
    // Cold outreach: permissible under FINRA with disclosures, but uncertain
    return { b: 0.40, d: 0.10, u: 0.50, a: 0.60 };
  }

  if (consentAgeInDays !== undefined && consentAgeInDays > consentMaxAgeDays) {
    // Stale consent
    return { b: 0.50, d: 0.20, u: 0.30, a: 0.65 };
  }

  // Fresh explicit consent
  return { b: 0.90, d: 0.02, u: 0.08, a: 0.95 };
}

// ─── §8 Expiry Trigger ─────────────────────────────────────────────────────

/**
 * At expiry, lawfulness mass transfers to violation (not uncertainty).
 * An expired deadline is a known fact, not epistemic uncertainty.
 *
 * γ = residual_factor ∈ [0, 1]
 *   γ = 0: hard expiry — all b converts to d
 *   γ = 1: no effect
 */
export function expiryTrigger(
  opinion: ComplianceOpinion,
  assessmentTime: number,
  triggerTime: number,
  residualFactor = 0.0,
): ComplianceOpinion {
  if (assessmentTime < triggerTime) return opinion;

  const gamma = residualFactor;
  const b = gamma * opinion.b;
  const d = opinion.d + (1 - gamma) * opinion.b;
  const u = opinion.u;

  return clamp({ b, d, u, a: opinion.a });
}

// ─── §8 Review Due Trigger ─────────────────────────────────────────────────

/**
 * A missed review shifts belief toward uncertainty (not violation).
 * Models the epistemics: we lack current evidence, not that we know it's bad.
 * Uses exponential decay: b decays to u.
 */
export function reviewDueTrigger(
  opinion: ComplianceOpinion,
  assessmentTime: number,
  triggerTime: number,
  acceleratedHalfLifeDays: number,
): ComplianceOpinion {
  if (assessmentTime < triggerTime) return opinion;

  const elapsed = assessmentTime - triggerTime;
  const lambda = Math.log(2) / acceleratedHalfLifeDays;
  const decayFactor = Math.exp(-lambda * elapsed);

  const b = opinion.b * decayFactor;
  const u = opinion.u + opinion.b * (1 - decayFactor);

  return clamp({ b, d: opinion.d, u, a: opinion.a });
}

// ─── Cumulative Belief Fusion ──────────────────────────────────────────────

/**
 * Fuse two independent source opinions (CBF operator).
 * Used when two rule engines both evaluate the same content independently.
 */
export function cumulativeFusion(
  opA: ComplianceOpinion,
  opB: ComplianceOpinion,
): ComplianceOpinion {
  const denom = opA.u + opB.u - opA.u * opB.u;

  if (denom < 1e-10) {
    // Both dogmatic — weighted average by base rate
    const w = opA.a + opB.a || 1;
    return clamp({
      b: (opA.a * opA.b + opB.a * opB.b) / w,
      d: (opA.a * opA.d + opB.a * opB.d) / w,
      u: 0,
      a: (opA.a + opB.a) / 2,
    });
  }

  const b = (opA.b * opB.u + opB.b * opA.u) / denom;
  const d = (opA.d * opB.u + opB.d * opA.u) / denom;
  const u = (opA.u * opB.u) / denom;

  return clamp({ b, d, u, a: (opA.a + opB.a) / 2 });
}

// ─── Internal ─────────────────────────────────────────────────────────────

function clamp(op: ComplianceOpinion): ComplianceOpinion {
  const b = Math.max(0, Math.min(1, op.b));
  const d = Math.max(0, Math.min(1, op.d));
  let u = Math.max(0, Math.min(1, op.u));
  const a = Math.max(0, Math.min(1, op.a));

  // Re-normalize if floating-point drift
  const sum = b + d + u;
  if (Math.abs(sum - 1) > 1e-8 && sum > 0) {
    return { b: b / sum, d: d / sum, u: u / sum, a };
  }

  return { b, d, u, a };
}
