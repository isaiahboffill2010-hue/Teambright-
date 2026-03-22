/**
 * Compliance scorer — orchestrates rule evaluations and algebra operators
 * into a single ComplianceScore for a given email message.
 */

import { ComplianceScore } from '@/types';
import {
  cumulativeFusion,
  jurisdictionalMeet,
  consentValidity,
  projectedProbability,
  ConsentParams,
} from './algebra';
import {
  rule2210_fairBalance,
  rule2241_suitability,
  ruleCANSPAM,
  ruleTaxAdvice,
} from './rules';

export interface ScorerInput {
  content: string;
  subject: string;
  hasUnsubscribeLink: boolean;
  consent: ConsentParams;
}

function toRiskLevel(pp: number, d: number): ComplianceScore['riskLevel'] {
  if (d > 0.65) return 'blocked';
  if (pp < 0.40) return 'high';
  if (pp < 0.65) return 'medium';
  return 'low';
}

export function scoreContent(input: ScorerInput): ComplianceScore {
  const combined = input.subject + ' ' + input.content;

  // 1. Evaluate rules
  const evals = [
    rule2210_fairBalance(combined),
    rule2241_suitability(combined),
    ruleCANSPAM(combined, input.hasUnsubscribeLink),
    ruleTaxAdvice(combined),
  ];

  // 2. Fuse content opinions via CBF
  const contentOpinion = evals
    .map((e) => e.opinion)
    .reduce((acc, op) => cumulativeFusion(acc, op));

  // 3. Consent opinion
  const consentOp = consentValidity(input.consent);

  // 4. Meet content × consent across jurisdictions
  const finalOpinion = jurisdictionalMeet(contentOpinion, consentOp);

  const pp = projectedProbability(finalOpinion);
  const riskLevel = toRiskLevel(pp, finalOpinion.d);

  const triggeredRules = evals
    .filter((e) => e.triggered)
    .map((e) => ({
      ruleId: e.ruleId,
      ruleName: e.ruleName,
      description: e.detail ?? e.ruleName,
      severity: e.severity,
      regulation: e.regulation,
    }));

  return {
    opinion: finalOpinion,
    riskLevel,
    projectedProbability: Math.round(pp * 1000) / 1000,
    triggeredRules,
    requiresReview: riskLevel === 'medium' || riskLevel === 'high',
    autoBlocked: riskLevel === 'blocked',
    scoredAt: new Date().toISOString(),
  };
}
