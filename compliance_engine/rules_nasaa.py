"""
NASAA Rules — North American Securities Administrators Association.

Plugin regulation for the Compliant Prospector. NASAA represents
state securities regulators across the US, Canada, and Mexico.
Their model rules provide a baseline that most states adopt.

Key rules:
    - Model Rule 102(a)(4): Dishonest/unethical practices
    - Unsuitable recommendations
    - Fee disclosure
    - Senior investor protections
"""

from __future__ import annotations

import re
from typing import List, Tuple

from .opinion import ComplianceOpinion
from .operators import RuleResult
from .registry import (
    Regulation, RuleDefinition, ProspectContext, default_registry,
)


# ═══════════════════════════════════════════════════════════════════
# PATTERN LIBRARIES
# ═══════════════════════════════════════════════════════════════════

DISHONEST_PRACTICES_PATTERNS = [
    (r"\b(guarantee[ds]?|promise[ds]?|assured|certain)\b", "promissory language", 1.0),
    (r"\b(risk[- ]?free|no[- ]?risk|safe bet|sure thing)\b", "false safety claim", 1.0),
    (r"\b(insider|confidential|non[- ]?public)\s+(info|information|tip|knowledge)\b", "insider info claim", 1.0),
    (r"\b(secret|hidden|undisclosed)\s+(strategy|method|opportunity)\b", "secrecy language", 0.8),
    (r"\b(can't lose|no way to lose|win[- ]?win)\b", "no-loss claim", 0.9),
    (r"\b(everyone is|everybody's|all (my|our) clients)\b", "false consensus", 0.6),
    (r"\b(once in a lifetime|now or never|last chance)\b", "artificial scarcity", 0.7),
    (r"\b(I shouldn't be telling|between you and me|keep this quiet)\b", "secrecy pressure", 0.9),
]

UNSUITABLE_RECOMMENDATION_PATTERNS = [
    (r"\b(you (need|must|should) (invest|buy|get|own))\b", "directive recommendation", 0.9),
    (r"\b(perfect (for|fit)|exactly what you need)\b", "assumed suitability", 0.8),
    (r"\b(everyone (should|needs|can benefit))\b", "blanket recommendation", 0.7),
    (r"\b(can't go wrong|no[- ]?brainer|obvious choice)\b", "oversimplified recommendation", 0.8),
    (r"\b(regardless of your|no matter your|whatever your)\b", "ignoring individual circumstances", 0.6),
]

FEE_CONCEALMENT_PATTERNS = [
    (r"\b(no (fee|cost|charge|commission|expense)s?)\b", "no-fee claim", 0.8),
    (r"\b(free|complimentary|at no cost)\b", "free service claim", 0.7),
    (r"\b(low[- ]?cost|affordable|budget[- ]?friendly)\b", "vague cost language", 0.3),
    (r"\b(hidden|surprise|unexpected)\s+(fee|cost|charge)\b", "hidden fee reference", 0.5),
]

FEE_DISCLOSURE_SIGNALS = [
    (r"\b(fee|cost|charge|commission|compensation|expense ratio)\b", "fee mention", -0.5),
    (r"\b(fee[- ]?based|fee[- ]?only|flat[- ]?fee)\b", "compensation structure", -0.6),
    (r"\b(disclosed|transparent|upfront)\b", "transparency signal", -0.4),
]

SENIOR_VULNERABILITY_PATTERNS = [
    (r"\b(retire|retirement|pension|social security|medicare)\b", "retirement reference", 0.3),
    (r"\b(estate|inheritance|legacy|trust|will)\b", "estate reference", 0.3),
    (r"\b(fixed income|annuit|reverse mortgage)\b", "senior-targeted product", 0.4),
    (r"\b(limited time|act now|don't (wait|delay)|hurry|urgent)\b", "urgency with senior", 0.9),
    (r"\b(confus|overwhelm|complicated|difficult to understand)\b", "complexity exploitation", 0.6),
    (r"\b(your (age|generation)|at your stage|at this point in life)\b", "age reference", 0.5),
]


# ═══════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════

def _scan_weighted(text: str, patterns: List[Tuple[str, str, float]]) -> Tuple[List[Tuple[str, str]], float]:
    text_lower = text.lower()
    hits = []
    severity = 0.0
    for pattern, label, weight in patterns:
        for m in re.finditer(pattern, text_lower):
            hits.append((m.group(), label))
            severity += weight
    return hits, severity


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


# ═══════════════════════════════════════════════════════════════════
# RULE CHECKERS
# ═══════════════════════════════════════════════════════════════════

def check_dishonest_practices(msg: str, ctx: ProspectContext) -> RuleResult:
    """NASAA Model Rule 102(a)(4) — Dishonest or unethical practices.

    Catch-all for misleading conduct not covered by specific federal rules.
    Broader than SEC §206 — covers any practice that would constitute
    "dishonest or unethical conduct" in the securities business.
    """
    hits, severity = _scan_weighted(msg, DISHONEST_PRACTICES_PATTERNS)

    if severity >= 3.0:
        l, v = 0.03, 0.85
        expl = f"Severely dishonest content ({len(hits)} flags, severity {severity:.1f}). NASAA violation."
    elif severity >= 1.5:
        l, v = 0.15, 0.55
        expl = f"Dishonest practices detected: {[h[1] for h in hits[:3]]}."
    elif severity >= 0.6:
        l, v = 0.40, 0.25
        expl = f"Potential ethical concern: {[h[1] for h in hits[:2]]}."
    elif severity > 0:
        l, v = 0.55, 0.12
        expl = f"Minor ethical flag: '{hits[0][1]}'."
    else:
        l, v = 0.78, 0.02
        expl = "No dishonest or unethical practice indicators."

    u = _clamp(1.0 - l - v)
    return RuleResult(
        rule_id="NASAA-102a4-dishonest",
        rule_name="No dishonest or unethical practices",
        regulation="NASAA",
        opinion=ComplianceOpinion.create(l, v, u, 0.3),
        explanation=expl,
        flagged_phrases=[h[0] for h in hits],
        suggested_fixes=[f"Remove '{h[0]}' — dishonest practice under NASAA 102(a)(4)" for h in hits],
    )


def check_unsuitable_recommendations(msg: str, ctx: ProspectContext) -> RuleResult:
    """NASAA — Unsuitable recommendations.

    Must have reasonable basis before recommending. Cold outreach that
    implies a recommendation without knowing the prospect's situation
    violates suitability requirements.
    """
    hits, severity = _scan_weighted(msg, UNSUITABLE_RECOMMENDATION_PATTERNS)

    # Positive: consultative / exploratory language
    consultative = bool(re.search(
        r"\b(would you (be open|like|consider)|explore|discuss|conversation|learn|curious)\b",
        msg, re.I,
    ))

    if severity >= 1.5:
        l, v = 0.10, 0.60
        expl = f"Directive recommendation without suitability basis: {[h[1] for h in hits[:3]]}."
    elif severity >= 0.7:
        l, v = 0.30, 0.35
        expl = f"Implied recommendation: '{hits[0][1]}'. No suitability analysis evident."
    elif severity > 0 and consultative:
        l, v = 0.55, 0.12
        expl = f"Minor suitability concern ('{hits[0][1]}') softened by consultative tone."
    elif severity > 0:
        l, v = 0.45, 0.20
        expl = f"Recommendation language without consultative framing: '{hits[0][1]}'."
    elif consultative:
        l, v = 0.80, 0.02
        expl = "Consultative approach — no suitability concerns. Well-framed."
    else:
        l, v = 0.65, 0.05
        expl = "No explicit recommendations. Neutral."

    u = _clamp(1.0 - l - v)
    return RuleResult(
        rule_id="NASAA-suitability",
        rule_name="No unsuitable recommendations",
        regulation="NASAA",
        opinion=ComplianceOpinion.create(l, v, u, 0.4),
        explanation=expl,
        flagged_phrases=[h[0] for h in hits],
        suggested_fixes=[f"Replace '{h[0]}' with exploratory language" for h in hits],
    )


def check_fee_disclosure(msg: str, ctx: ProspectContext) -> RuleResult:
    """NASAA — Fee disclosure requirements.

    Cannot omit material information about compensation.
    Claims of "free" or "no cost" are particularly scrutinized
    when the advisor earns commissions or has other compensation.
    """
    neg_hits, neg_sev = _scan_weighted(msg, FEE_CONCEALMENT_PATTERNS)
    pos_hits, pos_sev = _scan_weighted(msg, FEE_DISCLOSURE_SIGNALS)

    has_free_claim = bool(re.search(r"\b(free|no (fee|cost|charge)|complimentary)\b", msg, re.I))
    has_fee_mention = bool(re.search(r"\b(fee|cost|charge|commission|compensation)\b", msg, re.I))

    if has_free_claim and not has_fee_mention:
        l, v = 0.20, 0.45
        expl = "Claims free service without disclosing compensation structure."
    elif has_free_claim and has_fee_mention:
        l, v = 0.40, 0.20
        expl = "'Free' claim present but fee structure also mentioned."
    elif has_fee_mention:
        l, v = 0.80, 0.02
        expl = "Compensation/fee structure referenced. Good transparency."
    else:
        # Initial outreach typically doesn't mention fees — acceptable but noted
        l, v = 0.60, 0.05
        expl = "No fee discussion in initial outreach. Acceptable but note for follow-up."

    u = _clamp(1.0 - l - v)
    return RuleResult(
        rule_id="NASAA-fee-disclosure",
        rule_name="Fee and compensation disclosure",
        regulation="NASAA",
        opinion=ComplianceOpinion.create(l, v, u, 0.4),
        explanation=expl,
        flagged_phrases=[h[0] for h in neg_hits],
        suggested_fixes=["Disclose compensation structure" if has_free_claim else ""],
    )


def check_senior_protections(msg: str, ctx: ProspectContext) -> RuleResult:
    """NASAA — Enhanced senior investor protections.

    Stricter scrutiny on communications with seniors (65+).
    Urgency language, complexity exploitation, and age-targeting
    are particularly flagged. Senior-specific products require
    additional care in outreach.
    """
    hits, severity = _scan_weighted(msg, SENIOR_VULNERABILITY_PATTERNS)

    # Check for urgency + retirement context (especially dangerous)
    has_retirement_ref = bool(re.search(r"\b(retire|retirement|pension|senior)\b", msg, re.I))
    has_urgency = bool(re.search(r"\b(act now|limited time|hurry|urgent|don't wait)\b", msg, re.I))

    if has_retirement_ref and has_urgency:
        l, v = 0.10, 0.70
        expl = "CRITICAL: Urgency tactics combined with retirement context. Senior exploitation risk."
    elif severity >= 2.0:
        l, v = 0.20, 0.45
        expl = f"Multiple senior-relevant flags: {[h[1] for h in hits[:3]]}. Enhanced scrutiny."
    elif severity >= 0.8:
        l, v = 0.40, 0.25
        expl = f"Senior-relevant content: {[h[1] for h in hits[:2]]}. Ensure appropriate tone."
    elif severity > 0:
        l, v = 0.60, 0.08
        expl = f"Minor senior context: '{hits[0][1]}'. Standard care applies."
    else:
        l, v = 0.78, 0.02
        expl = "No senior-specific concerns detected."

    u = _clamp(1.0 - l - v)
    return RuleResult(
        rule_id="NASAA-senior-protections",
        rule_name="Senior investor protections",
        regulation="NASAA",
        opinion=ComplianceOpinion.create(l, v, u, 0.4),
        explanation=expl,
        flagged_phrases=[h[0] for h in hits],
        suggested_fixes=[f"Review '{h[0]}' for senior-appropriate communication" for h in hits],
    )


# ═══════════════════════════════════════════════════════════════════
# BUILD AND REGISTER
# ═══════════════════════════════════════════════════════════════════

NASAA_REGULATION = Regulation(
    regulation_id="NASAA",
    regulation_name="North American Securities Administrators Association",
    base_rate=0.4,
    metadata={
        "jurisdiction": "US States / Canada / Mexico",
        "key_rules": ["Model Rule 102(a)(4)", "Suitability", "Senior Protections"],
        "regulator": "State Securities Administrators",
    },
    rules=[
        RuleDefinition("NASAA-102a4-dishonest", "No dishonest or unethical practices",
            "NASAA Model Rule 102(a)(4): Catch-all for misleading conduct.",
            checker=check_dishonest_practices, severity="critical"),
        RuleDefinition("NASAA-suitability", "No unsuitable recommendations",
            "NASAA: Must have reasonable basis before recommending.",
            checker=check_unsuitable_recommendations, severity="major"),
        RuleDefinition("NASAA-fee-disclosure", "Fee and compensation disclosure",
            "NASAA: Cannot omit material information about compensation.",
            checker=check_fee_disclosure, severity="major"),
        RuleDefinition("NASAA-senior-protections", "Senior investor protections",
            "NASAA: Enhanced protections for senior investors (65+).",
            checker=check_senior_protections, severity="major"),
    ],
)

default_registry.register(NASAA_REGULATION)
