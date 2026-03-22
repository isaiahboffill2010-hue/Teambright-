/**
 * FINRA / SEC rule predicates.
 * Each rule function evaluates email content and returns an opinion
 * + metadata, ready for fusion via cumulativeFusion.
 */

import { ComplianceOpinion } from '@/types';

export interface RuleEvaluation {
  ruleId: string;
  ruleName: string;
  regulation: string;
  severity: 'info' | 'warning' | 'critical';
  opinion: ComplianceOpinion;
  triggered: boolean;
  detail?: string;
}

// ─── Pattern banks ─────────────────────────────────────────────────────────

const PROHIBITED_CLAIMS = [
  /guaranteed\s+return/i,
  /risk[\s-]free\s+(investment|return|profit)/i,
  /no\s+risk/i,
  /beat\s+the\s+market/i,
  /100%\s+(safe|secure|guaranteed)/i,
  /promise\s+(of\s+)?(profit|return)/i,
  /can't\s+lose/i,
  /sure[\s-]thing/i,
];

const PERFORMANCE_PUFFERY = [
  /consistently\s+outperform/i,
  /always\s+(profit|gain|returns)/i,
  /never\s+(lost|lose)/i,
];

const REQUIRED_DISCLOSURES = [
  /past\s+performance/i,
  /not\s+(a\s+)?guarantee/i,
  /may\s+lose\s+(value|principal)/i,
];

const SPECIFIC_SECURITY_RECOMMEND = [
  /\b(buy|invest\s+in|purchase)\s+[A-Z]{2,5}\b/,
  /\bstock\s+tip\b/i,
];

const TAX_ADVICE_SIGNALS = [
  /you\s+will\s+(save|owe)\s+\$[\d,]+\s+in\s+tax/i,
  /guaranteed\s+tax\s+savings/i,
];

// ─── FINRA Rule 2210 — Fair and Balanced Communication ────────────────────

export function rule2210_fairBalance(content: string): RuleEvaluation {
  const hasProhibited = PROHIBITED_CLAIMS.some((re) => re.test(content));
  const hasPuffery = PERFORMANCE_PUFFERY.some((re) => re.test(content));
  const hasDisclosure = REQUIRED_DISCLOSURES.some((re) => re.test(content));
  const wordCount = content.trim().split(/\s+/).length;

  let opinion: ComplianceOpinion;
  let severity: RuleEvaluation['severity'] = 'info';
  let detail: string | undefined;

  if (hasProhibited) {
    opinion = { b: 0.05, d: 0.90, u: 0.05, a: 0.5 };
    severity = 'critical';
    detail = 'Contains prohibited performance guarantees or misleading claims.';
  } else if (hasPuffery) {
    opinion = { b: 0.35, d: 0.40, u: 0.25, a: 0.55 };
    severity = 'warning';
    detail = 'Contains performance puffery that may mislead recipients.';
  } else if (wordCount > 400 && !hasDisclosure) {
    opinion = { b: 0.55, d: 0.15, u: 0.30, a: 0.65 };
    severity = 'warning';
    detail = 'Longer content without required risk disclosures.';
  } else {
    opinion = { b: 0.82, d: 0.04, u: 0.14, a: 0.80 };
  }

  return {
    ruleId: 'FINRA-2210',
    ruleName: 'Fair and Balanced Communication',
    regulation: 'FINRA Rule 2210',
    severity,
    opinion,
    triggered: hasProhibited || hasPuffery || (wordCount > 400 && !hasDisclosure),
    detail,
  };
}

// ─── FINRA Rule 2241 / SEC Reg BI — Best Interest / Suitability ───────────

export function rule2241_suitability(content: string): RuleEvaluation {
  const hasSpecificRec = SPECIFIC_SECURITY_RECOMMEND.some((re) => re.test(content));

  const opinion: ComplianceOpinion = hasSpecificRec
    ? { b: 0.28, d: 0.42, u: 0.30, a: 0.50 }
    : { b: 0.88, d: 0.04, u: 0.08, a: 0.85 };

  return {
    ruleId: 'FINRA-2241',
    ruleName: 'Best Interest / Suitability',
    regulation: 'FINRA Rule 2241 / SEC Reg BI',
    severity: hasSpecificRec ? 'warning' : 'info',
    opinion,
    triggered: hasSpecificRec,
    detail: hasSpecificRec
      ? 'Specific security recommendations require suitability documentation.'
      : undefined,
  };
}

// ─── CAN-SPAM Act — Required Email Elements ───────────────────────────────

export function ruleCANSPAM(
  content: string,
  hasUnsubscribeLink: boolean,
): RuleEvaluation {
  const hasPhysicalAddress = /\d+\s+\w[\w\s]+,\s*\w+,?\s*[A-Z]{2}/i.test(content);
  const compliant = hasUnsubscribeLink && hasPhysicalAddress;

  const opinion: ComplianceOpinion = compliant
    ? { b: 0.95, d: 0.02, u: 0.03, a: 0.90 }
    : !hasUnsubscribeLink
    ? { b: 0.10, d: 0.80, u: 0.10, a: 0.45 }
    : { b: 0.55, d: 0.25, u: 0.20, a: 0.65 };

  return {
    ruleId: 'CAN-SPAM',
    ruleName: 'CAN-SPAM Compliance',
    regulation: 'CAN-SPAM Act 2003',
    severity: !compliant ? 'critical' : 'info',
    opinion,
    triggered: !compliant,
    detail: !hasUnsubscribeLink
      ? 'Missing unsubscribe link (required by CAN-SPAM).'
      : !hasPhysicalAddress
      ? 'Missing physical mailing address (required by CAN-SPAM).'
      : undefined,
  };
}

// ─── Tax Advice Rule — Explicit Tax Guarantee ─────────────────────────────

export function ruleTaxAdvice(content: string): RuleEvaluation {
  const hasGuaranteedTax = TAX_ADVICE_SIGNALS.some((re) => re.test(content));

  const opinion: ComplianceOpinion = hasGuaranteedTax
    ? { b: 0.15, d: 0.65, u: 0.20, a: 0.45 }
    : { b: 0.88, d: 0.04, u: 0.08, a: 0.85 };

  return {
    ruleId: 'TAX-ADVICE',
    ruleName: 'Tax Advice Guardrails',
    regulation: 'SEC / IRS Marketing Guidelines',
    severity: hasGuaranteedTax ? 'critical' : 'info',
    opinion,
    triggered: hasGuaranteedTax,
    detail: hasGuaranteedTax
      ? 'Guaranteed tax savings claims are prohibited without qualified advice disclaimer.'
      : undefined,
  };
}
