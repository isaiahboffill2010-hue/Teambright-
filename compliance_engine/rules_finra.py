"""
FINRA Rules — granular, context-aware compliance checking.

Scoring is now DYNAMIC based on actual message content:
    - Number and severity of pattern hits
    - Presence/absence of positive compliance signals
    - Message structure analysis (length, personalization depth, tone)
    - Interaction effects between rules

Each rule returns a ComplianceOpinion with VARYING scores, not flat defaults.
"""

from __future__ import annotations

import re
import math
from typing import List, Tuple

from .opinion import ComplianceOpinion
from .operators import RuleResult
from .registry import (
    Regulation, RuleDefinition, ProspectContext, default_registry,
)


# ═══════════════════════════════════════════════════════════════════
# PATTERN LIBRARIES (expanded with edge cases)
# ═══════════════════════════════════════════════════════════════════

PROMISSORY_PATTERNS = [
    # Hard violations — clearly promissory
    (r"\bguarantee[ds]?\b", "guarantee", 1.0),
    (r"\bpromise[ds]?\b", "promise", 1.0),
    (r"\brisk[- ]?free\b", "risk-free", 1.0),
    (r"\bno[- ]?risk\b", "no-risk", 1.0),
    (r"\bsafe investment\b", "safe investment", 1.0),
    (r"\bcertain return\b", "certain return", 1.0),
    (r"\bnever lose\b", "loss guarantee", 1.0),
    (r"\balways (profit|gain|win)\b", "absolute performance", 1.0),
    # Medium violations — context-dependent
    (r"\bensure[ds]?\b", "ensure (promissory)", 0.6),
    (r"\bassure[ds]?\b", "assure (promissory)", 0.6),
    (r"\bwill (increase|grow|double|triple|appreciate)\b", "future prediction", 0.8),
    (r"\byou will (make|earn|receive|get)\b", "earnings promise", 0.9),
    (r"\b100%\b", "absolute claim", 0.7),
    # Soft signals — potentially promissory
    (r"\bprotect(ed|s|ing)?\s+(your|the)\s+(wealth|assets|portfolio)\b", "protection language", 0.4),
    (r"\bsecure\s+(your|the)\s+(future|retirement)\b", "security language", 0.4),
    (r"\bworry[- ]?free\b", "worry-free", 0.5),
    (r"\bpeace of mind\b", "peace of mind", 0.3),
    (r"\bset for life\b", "set for life", 0.7),
]

EXAGGERATED_PATTERNS = [
    (r"\bbest (investment|strategy|approach|returns|advisor|firm)\b", "superlative claim", 1.0),
    (r"\b(top|#1|number one) (advisor|firm|strategy|rated)\b", "ranking claim", 1.0),
    (r"\bunbeatable\b", "superlative", 1.0),
    (r"\boutperform(s|ed|ing)? (every|all|the market)\b", "broad outperformance", 0.9),
    (r"\b(extraordinary|exceptional|incredible|amazing|unmatched) (returns|gains|performance|results)\b", "exaggerated returns", 0.8),
    (r"\bexclusive (access|opportunity|deal|offer)\b", "exclusivity pressure", 0.6),
    (r"\b(proven|guaranteed|certified) (strategy|method|system|approach)\b", "proven system", 0.7),
    (r"\bsecret(s)?\s+(strategy|method|technique|formula)\b", "secret formula", 0.8),
    (r"\b(no one else|only we|we alone)\b", "exclusivity claim", 0.6),
    (r"\brevolutionary\b", "revolutionary claim", 0.5),
]

PERFORMANCE_PREDICTION_PATTERNS = [
    (r"\bwill (return|yield|generate|produce)\s+\d", "specific return prediction", 1.0),
    (r"\bexpect(ed|ing)?\s+(\d+%|\$\d)", "specific expectation", 1.0),
    (r"\b\d+%\s+(return|gain|growth|yield|annually|per year)\b", "specific percentage", 1.0),
    (r"\b(double|triple|quadruple|10x)\s+(your|the)\s+(money|investment|portfolio)\b", "multiplier promise", 1.0),
    (r"\b(historically|typically|usually)\s+(returns?|yields?|generates?)\s+\d", "implied prediction", 0.6),
    (r"\b(average|median)\s+return\s+of\s+\d", "average return cite", 0.5),
    (r"\bprojected\s+(return|growth|income)\b", "projected returns", 0.8),
    (r"\bforecast(ed|ing)?\s+\d", "forecast with number", 0.9),
]

PRESSURE_PATTERNS = [
    (r"\b(act now|limited time|only \d+ spots?|expires? (soon|today|tomorrow))\b", "urgency pressure", 1.0),
    (r"\b(don't miss|last chance|once in a lifetime)\b", "scarcity pressure", 1.0),
    (r"\b(hurry|rush|immediately|right now)\b", "time pressure", 0.8),
    (r"\b(before it's too late|window closing|running out)\b", "deadline pressure", 0.8),
    (r"\b(limited (spots|availability|seats)|first come)\b", "artificial scarcity", 0.9),
    (r"\b(call me (today|now|asap|immediately))\b", "call urgency", 0.5),
]

COMPLEMENT_SIGNALS = [
    (r"\bcomplement\b", "complement language", 1.0),
    (r"\bancillary\b", "ancillary positioning", 1.0),
    (r"\bin addition to\b", "additive framing", 0.8),
    (r"\balongside\b", "alongside framing", 0.8),
    (r"\bnot (to )?(replace|replacing)\b", "explicit non-replacement", 1.0),
    (r"\bexisting (advisor|adviser|team|relationship)\b", "acknowledges existing", 0.9),
    (r"\bwithout disrupting\b", "non-disruptive", 0.7),
    (r"\bcollaborat(e|ing|ion)\b", "collaborative", 0.6),
]

# New: tone and professionalism signals
PROFESSIONAL_TONE_SIGNALS = [
    (r"\bwould you be (open|interested|willing)\b", "consultative ask", 0.8),
    (r"\bI'd (love|like|welcome) to\b", "polite framing", 0.6),
    (r"\bwhen (it|you|your) (makes?|works?|suits?)\b", "flexible scheduling", 0.5),
    (r"\bno obligation\b", "no-obligation", 0.7),
    (r"\bbrief (conversation|call|chat|meeting)\b", "low-commitment ask", 0.6),
]

UNPROFESSIONAL_SIGNALS = [
    (r"\b(bro|dude|buddy|pal|chief)\b", "overly casual", 0.6),
    (r"\!\!\!+", "excessive exclamation", 0.4),
    (r"\b[A-Z]{4,}\b", "shouting (all caps)", 0.5),
    (r"\$+\$+", "money symbols", 0.3),
]


# ═══════════════════════════════════════════════════════════════════
# HELPERS — weighted scanning
# ═══════════════════════════════════════════════════════════════════

def _scan_weighted(text: str, patterns: List[Tuple[str, str, float]]) -> Tuple[List[Tuple[str, str]], float]:
    """Scan for patterns; return hits and weighted severity sum."""
    text_lower = text.lower()
    hits = []
    severity_sum = 0.0
    for pattern, label, weight in patterns:
        for m in re.finditer(pattern, text_lower):
            hits.append((m.group(), label))
            severity_sum += weight
    return hits, severity_sum


def _scan_simple(text: str, patterns: List[Tuple[str, str, float]]) -> List[Tuple[str, str]]:
    """Scan returning just hits (no severity)."""
    hits, _ = _scan_weighted(text, patterns)
    return hits


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


# ═══════════════════════════════════════════════════════════════════
# RULE CHECKERS — granular, context-aware scoring
# ═══════════════════════════════════════════════════════════════════

def check_no_promissory(msg: str, ctx: ProspectContext) -> RuleResult:
    """FINRA 2210(d)(1)(A) — No promissory or misleading statements.

    Scoring is continuous: more hits and higher severity = lower lawfulness.
    Positive compliance signals boost lawfulness.
    """
    hits, severity = _scan_weighted(msg, PROMISSORY_PATTERNS)
    pos_hits = _scan_simple(msg, COMPLEMENT_SIGNALS)
    tone_hits = _scan_simple(msg, PROFESSIONAL_TONE_SIGNALS)

    # Base: start from clean slate
    if severity >= 2.5:
        l_base = 0.03
    elif severity >= 1.5:
        l_base = 0.10
    elif severity >= 0.8:
        l_base = 0.25
    elif severity >= 0.3:
        l_base = 0.45
    elif severity > 0:
        l_base = 0.55
    else:
        l_base = 0.70

    # Boost from positive signals
    pos_boost = min(len(pos_hits) * 0.04 + len(tone_hits) * 0.02, 0.15)
    l = _clamp(l_base + pos_boost)

    # Violation scales with severity
    v = _clamp(min(severity * 0.35, 0.90)) if severity > 0 else 0.02
    u = _clamp(1.0 - l - v)

    opinion = ComplianceOpinion.create(l, v, u, base_rate=0.3)

    if len(hits) == 0:
        if pos_hits:
            expl = f"No promissory language. {len(pos_hits)} positive compliance signal(s) detected."
        elif tone_hits:
            expl = f"No promissory language. Professional tone confirmed."
        else:
            expl = "No promissory language detected. Residual uncertainty from nuanced phrasing."
    elif len(hits) == 1:
        expl = f"Promissory phrase detected: '{hits[0][1]}' (severity {severity:.1f}). Needs review."
    else:
        expl = f"{len(hits)} promissory phrases (severity {severity:.1f}). High violation confidence."

    return RuleResult(
        rule_id="FINRA-2210-d1-A",
        rule_name="No promissory or misleading statements",
        regulation="FINRA",
        opinion=opinion, explanation=expl,
        flagged_phrases=[h[0] for h in hits],
        suggested_fixes=[f"Remove or rephrase '{h[0]}' — {h[1]}" for h in hits],
    )


def check_no_exaggerated(msg: str, ctx: ProspectContext) -> RuleResult:
    """FINRA 2210(d)(1)(B) — No exaggerated or unwarranted claims."""
    hits, severity = _scan_weighted(msg, EXAGGERATED_PATTERNS)
    unpro_hits = _scan_simple(msg, UNPROFESSIONAL_SIGNALS)

    if severity >= 2.0:
        l, v = 0.05, 0.80
    elif severity >= 1.0:
        l, v = 0.15, 0.55
    elif severity >= 0.5:
        l, v = 0.35, 0.35
    elif severity > 0:
        l, v = 0.50, 0.20
    else:
        l = 0.78 - len(unpro_hits) * 0.05
        v = 0.02 + len(unpro_hits) * 0.03

    l, v = _clamp(l), _clamp(v)
    u = _clamp(1.0 - l - v)

    if hits:
        expl = f"{len(hits)} exaggerated claim(s) (severity {severity:.1f}): {[h[1] for h in hits[:3]]}."
    elif unpro_hits:
        expl = f"No exaggerated claims, but {len(unpro_hits)} tone issue(s) detected."
    else:
        expl = "No exaggerated or superlative claims. Professional tone."

    return RuleResult(
        rule_id="FINRA-2210-d1-B",
        rule_name="No exaggerated or unwarranted claims",
        regulation="FINRA",
        opinion=ComplianceOpinion.create(l, v, u, 0.3),
        explanation=expl,
        flagged_phrases=[h[0] for h in hits],
        suggested_fixes=[f"Replace '{h[0]}' with measured, factual language" for h in hits],
    )


def check_no_performance_predictions(msg: str, ctx: ProspectContext) -> RuleResult:
    """FINRA 2210(d)(1)(D) — No predictions or projections of performance."""
    hits, severity = _scan_weighted(msg, PERFORMANCE_PREDICTION_PATTERNS)

    if severity >= 1.5:
        l, v = 0.03, 0.85
        expl = f"Strong performance predictions (severity {severity:.1f}): {[h[1] for h in hits[:3]]}."
    elif severity >= 0.8:
        l, v = 0.15, 0.60
        expl = f"Performance language detected: {[h[1] for h in hits[:2]]}."
    elif severity > 0:
        l, v = 0.40, 0.30
        expl = f"Mild performance implication: '{hits[0][1]}'. Consider rephrasing."
    else:
        # Bonus: check if message discusses strategy without numbers (good)
        has_strategy = bool(re.search(r"\b(strategy|approach|planning|optimization)\b", msg, re.I))
        l = 0.82 if has_strategy else 0.75
        v = 0.02
        expl = "No performance predictions." + (" Strategy discussion without projections — good." if has_strategy else "")

    u = _clamp(1.0 - l - v)
    return RuleResult(
        rule_id="FINRA-2210-d1-D",
        rule_name="No performance predictions or projections",
        regulation="FINRA",
        opinion=ComplianceOpinion.create(l, v, u, 0.3),
        explanation=expl,
        flagged_phrases=[h[0] for h in hits],
        suggested_fixes=[f"Remove '{h[0]}' — cannot predict specific returns" for h in hits],
    )


def check_no_pressure(msg: str, ctx: ProspectContext) -> RuleResult:
    """FINRA 2210(d)(1)(A) — No urgency/pressure/scarcity tactics."""
    hits, severity = _scan_weighted(msg, PRESSURE_PATTERNS)
    tone_hits = _scan_simple(msg, PROFESSIONAL_TONE_SIGNALS)

    if severity >= 2.0:
        l, v = 0.05, 0.75
    elif severity >= 1.0:
        l, v = 0.15, 0.55
    elif severity > 0:
        l, v = 0.40, 0.30
    else:
        # Bonus for consultative tone
        l = 0.78 + min(len(tone_hits) * 0.03, 0.10)
        v = 0.02
    
    l, v = _clamp(l), _clamp(v)
    u = _clamp(1.0 - l - v)

    if hits:
        expl = f"Pressure tactics (severity {severity:.1f}): {[h[1] for h in hits[:3]]}."
    elif tone_hits:
        expl = f"No pressure tactics. Consultative tone ({len(tone_hits)} positive signal(s))."
    else:
        expl = "No pressure or urgency tactics detected."

    return RuleResult(
        rule_id="FINRA-2210-d1-A-pressure",
        rule_name="No urgency or pressure tactics",
        regulation="FINRA",
        opinion=ComplianceOpinion.create(l, v, u, 0.3),
        explanation=expl,
        flagged_phrases=[h[0] for h in hits],
        suggested_fixes=[f"Remove '{h[0]}' — avoid artificial urgency" for h in hits],
    )


def check_message_length(msg: str, ctx: ProspectContext) -> RuleResult:
    """Best practice — concise outreach. Scoring is now a smooth curve."""
    wc = len(msg.split())
    sentence_count = len(re.findall(r'[.!?]+', msg))

    # Smooth scoring curve instead of flat buckets
    if wc <= 50:
        l = 0.90
        expl = f"Very concise ({wc} words, {sentence_count} sentences). Strong."
    elif wc <= 80:
        l = 0.88 - (wc - 50) * 0.002  # 0.88 → 0.82
        expl = f"Concise ({wc} words, {sentence_count} sentences). Good."
    elif wc <= 120:
        l = 0.75 - (wc - 80) * 0.004  # 0.75 → 0.59
        expl = f"Moderate length ({wc} words, {sentence_count} sentences)."
    elif wc <= 200:
        l = 0.50 - (wc - 120) * 0.003  # 0.50 → 0.26
        expl = f"Long ({wc} words). More compliance surface area."
    else:
        l = max(0.10, 0.26 - (wc - 200) * 0.001)
        expl = f"Very long ({wc} words). High surface area, low engagement."

    l = _clamp(l)
    v = _clamp(max(0.02, (1.0 - l) * 0.25))
    u = _clamp(1.0 - l - v)

    return RuleResult(
        rule_id="FINRA-BP-length",
        rule_name="Message conciseness",
        regulation="FINRA",
        opinion=ComplianceOpinion.create(l, v, u, 0.5),
        explanation=expl,
    )


def check_personalization(msg: str, ctx: ProspectContext) -> RuleResult:
    """Best practice — personalized outreach. Deep content analysis."""
    text_lower = msg.lower()
    signals = 0
    details = []

    # Name check
    if ctx.prospect_name:
        first_name = ctx.prospect_name.lower().split()[0]
        if first_name and first_name in text_lower:
            signals += 1
            details.append("name")

    # Role/title check
    if ctx.prospect_role:
        role_words = [w.lower() for w in ctx.prospect_role.split() if len(w) > 3]
        role_matched = [w for w in role_words if w in text_lower]
        if role_matched:
            signals += 1
            details.append("role")

    # Company check (separate from role)
    if ctx.prospect_company:
        comp_words = [w.lower() for w in ctx.prospect_company.split() if len(w) > 2]
        if any(w in text_lower for w in comp_words):
            signals += 1
            details.append("company")

    # Industry-specific language
    industry_terms = ["tax", "equity", "portfolio", "investment", "capital", "fund",
                      "estate", "wealth", "retirement", "compensation", "carried interest"]
    industry_count = sum(1 for t in industry_terms if t in text_lower)
    if industry_count >= 2:
        signals += 1
        details.append(f"industry({industry_count} terms)")

    # Scoring: 0-4 signal scale
    l = _clamp(0.25 + signals * 0.18)  # 0.25, 0.43, 0.61, 0.79, 0.97
    v = _clamp(max(0.02, 0.25 - signals * 0.06))
    u = _clamp(1.0 - l - v)

    if signals >= 3:
        expl = f"Well personalized: {', '.join(details)}. Strong compliance signal."
    elif signals == 2:
        expl = f"Good personalization: {', '.join(details)}."
    elif signals == 1:
        expl = f"Basic personalization: {', '.join(details)}. Could improve."
    else:
        expl = "Generic message. No personalization detected — spam risk."

    return RuleResult(
        rule_id="FINRA-BP-personalization",
        rule_name="Personalization quality",
        regulation="FINRA",
        opinion=ComplianceOpinion.create(l, v, u, 0.5),
        explanation=expl,
    )


def check_fair_balanced(msg: str, ctx: ProspectContext) -> RuleResult:
    """FINRA 2210(d)(1)(C) — Fair and balanced presentation.

    NEW RULE: Messages must not present only benefits without
    acknowledging limitations or that outcomes vary.
    """
    text_lower = msg.lower()

    benefit_words = ["benefit", "advantage", "opportunity", "gain", "profit",
                     "optimize", "maximize", "enhance", "improve", "boost"]
    risk_words = ["risk", "consider", "limitation", "may not", "no guarantee",
                  "varies", "individual", "consult", "situation"]

    benefit_count = sum(1 for w in benefit_words if w in text_lower)
    risk_count = sum(1 for w in risk_words if w in text_lower)

    if benefit_count >= 3 and risk_count == 0:
        l, v = 0.25, 0.40
        expl = f"Unbalanced: {benefit_count} benefit terms, 0 risk/limitation terms."
    elif benefit_count >= 2 and risk_count == 0:
        l, v = 0.45, 0.20
        expl = f"Slightly unbalanced: {benefit_count} benefits, 0 risk acknowledgments."
    elif benefit_count > 0 and risk_count > 0:
        l, v = 0.80, 0.02
        expl = f"Balanced presentation: {benefit_count} benefit, {risk_count} risk terms."
    else:
        l, v = 0.70, 0.03
        expl = "Neutral tone. No imbalance detected."

    u = _clamp(1.0 - l - v)
    return RuleResult(
        rule_id="FINRA-2210-d1-C",
        rule_name="Fair and balanced presentation",
        regulation="FINRA",
        opinion=ComplianceOpinion.create(l, v, u, 0.3),
        explanation=expl,
    )


def check_contact_info_compliance(msg: str, ctx: ProspectContext) -> RuleResult:
    """FINRA 2210(e) — Disclosure requirements for retail communications.

    NEW RULE: Check for appropriate identification / professional context.
    Cold outreach should identify the firm or professional capacity.
    """
    text_lower = msg.lower()
    has_firm_ref = bool(re.search(r"\b(our firm|we at|at our|my team|my practice)\b", text_lower))
    has_capacity = bool(re.search(r"\b(financial advisor|wealth|advisory|planning)\b", text_lower))

    if has_firm_ref and has_capacity:
        l, v = 0.82, 0.02
        expl = "Professional capacity and firm context established."
    elif has_firm_ref or has_capacity:
        l, v = 0.60, 0.08
        expl = "Partial professional context. Consider adding firm identification."
    else:
        l, v = 0.40, 0.15
        expl = "No firm or professional capacity mentioned. Unclear who is contacting the prospect."

    u = _clamp(1.0 - l - v)
    return RuleResult(
        rule_id="FINRA-2210-e",
        rule_name="Professional identification",
        regulation="FINRA",
        opinion=ComplianceOpinion.create(l, v, u, 0.3),
        explanation=expl,
    )


# ═══════════════════════════════════════════════════════════════════
# BUILD AND REGISTER
# ═══════════════════════════════════════════════════════════════════

FINRA_REGULATION = Regulation(
    regulation_id="FINRA",
    regulation_name="Financial Industry Regulatory Authority",
    base_rate=0.3,
    metadata={
        "api_base": "https://api.finra.org",
        "fip_token_url": "https://ews.fip.finra.org/fip/rest/ews/oauth2/access_token?grant_type=client_credentials",
        "rulebook_dataset": "finraRulebook",
        "key_rules": ["2210", "2211", "2090", "2111"],
        "first_tool_url": "https://www.finra.org/rules-guidance/rulebooks/finra-rulebook-search-tool-first",
    },
    rules=[
        RuleDefinition("FINRA-2210-d1-A", "No promissory or misleading statements",
            "FINRA 2210(d)(1)(A): No false, exaggerated, unwarranted, promissory, or misleading claims.",
            checker=check_no_promissory, severity="critical"),
        RuleDefinition("FINRA-2210-d1-B", "No exaggerated or unwarranted claims",
            "FINRA 2210(d)(1)(B): No exaggerated, unwarranted, or misleading statements.",
            checker=check_no_exaggerated, severity="critical"),
        RuleDefinition("FINRA-2210-d1-C", "Fair and balanced presentation",
            "FINRA 2210(d)(1)(C): Benefits must be balanced with risks/limitations.",
            checker=check_fair_balanced, severity="minor"),
        RuleDefinition("FINRA-2210-d1-D", "No performance predictions",
            "FINRA 2210(d)(1)(D): May not predict or project performance.",
            checker=check_no_performance_predictions, severity="critical"),
        RuleDefinition("FINRA-2210-d1-A-pressure", "No urgency or pressure tactics",
            "FINRA 2210(d)(1)(A): No high-pressure sales tactics.",
            checker=check_no_pressure, severity="major"),
        RuleDefinition("FINRA-2210-e", "Professional identification",
            "FINRA 2210(e): Retail communications must identify the firm/professional.",
            checker=check_contact_info_compliance, severity="minor"),
        RuleDefinition("FINRA-BP-length", "Message conciseness",
            "Best practice: concise outreach reduces compliance surface area.",
            checker=check_message_length, severity="advisory"),
        RuleDefinition("FINRA-BP-personalization", "Personalization quality",
            "Best practice: personalized messages align with FINRA fair dealing.",
            checker=check_personalization, severity="advisory"),
    ],
)

default_registry.register(FINRA_REGULATION)
