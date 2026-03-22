"""
MiFID II Rules — EU Markets in Financial Instruments Directive.

Plugin regulation for the Compliant Prospector. Demonstrates the
pluggable registry architecture: import this module and MiFID II
rules are automatically available alongside FINRA + SEC.

Target: Investor protection for EU-based prospects.
Key difference from US: "fair, clear, and not misleading" standard
applies to ALL communications, not just "retail communications."

Articles referenced:
    - Article 24(1): Best interest obligation
    - Article 24(3): Fair, clear, not misleading
    - Article 24(4): Cost & charges transparency
    - Article 25: Suitability assessment
    - Cross-border solicitation rules
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

SUITABILITY_ASSUMPTION_PATTERNS = [
    (r"\b(perfect|ideal|right) (for you|fit|match|solution)\b", "assumed suitability", 1.0),
    (r"\b(you (need|should|must)|what you're looking for)\b", "prescriptive advice", 0.8),
    (r"\b(tailored|customized|personalized) (to|for) (your|you)\b", "tailored claim", 0.5),
    (r"\b(based on your (situation|needs|goals|profile))\b", "assumed knowledge", 0.7),
    (r"\b(we know|we understand) (your|that you)\b", "assumed familiarity", 0.6),
    (r"\b(recommend|suggesting|advise)\b", "recommendation language", 0.7),
]

UNCLEAR_MISLEADING_PATTERNS = [
    (r"\b(guaranteed|risk[- ]?free|certain|assured)\b", "misleading certainty", 1.0),
    (r"\b(no (downside|loss|risk))\b", "misleading safety", 1.0),
    (r"\b(always|never|every time)\b", "absolute language", 0.6),
    (r"\b(simple|easy|straightforward) (way to|path to|route to)\b", "oversimplification", 0.5),
    (r"\b(just|only|merely)\s+(need|have|requires?)\b", "minimizing complexity", 0.4),
    (r"\b(secret|hidden|insider)\b", "opacity language", 0.7),
]

COST_TRANSPARENCY_PATTERNS = [
    (r"\b(free|no cost|no fee|complimentary|zero charge)\b", "free claim", 0.7),
    (r"\b(at no (additional|extra) (cost|charge|fee))\b", "hidden cost language", 0.6),
    (r"\b(fee[s]?|cost[s]?|charge[s]?|commission|expense)\b", "cost mention (positive)", -0.5),
    (r"\b(transparent|disclosed|upfront) (fee|pricing|cost)\b", "transparency signal (positive)", -0.8),
]

BEST_INTEREST_SIGNALS = [
    (r"\b(in your best interest|acting for you|on your behalf)\b", "best interest claim", 0.5),
    (r"\b(fiduciary|duty of care|duty of loyalty)\b", "fiduciary claim", 0.4),
    (r"\b(independent|unbiased|objective)\b", "independence claim", 0.4),
    (r"\b(conflict[s]? of interest)\b", "conflict disclosure (positive)", -0.6),
]

CROSS_BORDER_SIGNALS = [
    (r"\b(EU|European|Europe|EEA)\b", "EU reference", 0.3),
    (r"\b(MiFID|ESMA|FCA)\b", "regulatory reference", 0.2),
    (r"\b(passport|cross[- ]?border|international)\b", "cross-border signal", 0.4),
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

def check_suitability_assessment(msg: str, ctx: ProspectContext) -> RuleResult:
    """MiFID II Article 25 — Suitability assessment.

    Cold outreach cannot assume suitability. Messages that imply
    the advisor already knows the prospect's needs violate this.
    Consultative framing ("would you be open to discussing") is compliant.
    """
    hits, severity = _scan_weighted(msg, SUITABILITY_ASSUMPTION_PATTERNS)

    # Positive: consultative tone
    consultative = bool(re.search(
        r"\b(would you be (open|interested)|explore|discuss|conversation|learn more)\b",
        msg, re.I,
    ))

    if severity >= 1.5:
        l, v = 0.10, 0.60
        expl = f"Assumes suitability without assessment: {[h[1] for h in hits[:3]]}."
    elif severity >= 0.7:
        l, v = 0.30, 0.35
        expl = f"Implies knowledge of prospect's needs: '{hits[0][1]}'."
    elif severity > 0:
        l, v = 0.50, 0.15
        expl = f"Minor suitability assumption: '{hits[0][1]}'. Consider softening."
    elif consultative:
        l, v = 0.80, 0.02
        expl = "Consultative tone — no suitability assumptions. Compliant."
    else:
        l, v = 0.60, 0.05
        expl = "No explicit suitability claims. Neutral."

    u = _clamp(1.0 - l - v)
    return RuleResult(
        rule_id="MIFID2-Art25-suitability",
        rule_name="Suitability assessment required",
        regulation="MiFID_II",
        opinion=ComplianceOpinion.create(l, v, u, 0.4),
        explanation=expl,
        flagged_phrases=[h[0] for h in hits],
        suggested_fixes=[f"Replace '{h[0]}' with consultative language" for h in hits],
    )


def check_fair_clear_not_misleading(msg: str, ctx: ProspectContext) -> RuleResult:
    """MiFID II Article 24(3) — Fair, clear, and not misleading.

    Stricter than FINRA — applies to ALL communications.
    Tests for clarity, accuracy, and absence of misleading elements.
    """
    hits, severity = _scan_weighted(msg, UNCLEAR_MISLEADING_PATTERNS)

    if severity >= 2.0:
        l, v = 0.05, 0.75
        expl = f"Multiple misleading elements (severity {severity:.1f}): {[h[1] for h in hits[:3]]}."
    elif severity >= 1.0:
        l, v = 0.20, 0.50
        expl = f"Misleading language detected: {[h[1] for h in hits[:2]]}."
    elif severity >= 0.4:
        l, v = 0.45, 0.20
        expl = f"Minor clarity concern: '{hits[0][1]}'."
    elif severity > 0:
        l, v = 0.55, 0.10
        expl = f"Slight ambiguity: '{hits[0][1]}'. Consider clarifying."
    else:
        l, v = 0.78, 0.02
        expl = "Message is clear and not misleading."

    u = _clamp(1.0 - l - v)
    return RuleResult(
        rule_id="MIFID2-Art24-3-fair-clear",
        rule_name="Fair, clear, and not misleading",
        regulation="MiFID_II",
        opinion=ComplianceOpinion.create(l, v, u, 0.3),
        explanation=expl,
        flagged_phrases=[h[0] for h in hits],
        suggested_fixes=[f"Rephrase '{h[0]}' for clarity and accuracy" for h in hits],
    )


def check_cost_transparency(msg: str, ctx: ProspectContext) -> RuleResult:
    """MiFID II Article 24(4) — Cost and charges transparency.

    Cannot obscure that fees exist. Claims of "free" service are
    particularly problematic if the advisor earns commissions.
    Positive: mentioning fees/costs is a transparency signal.
    """
    hits, severity = _scan_weighted(msg, COST_TRANSPARENCY_PATTERNS)

    # Separate positive (cost mention) from negative (free claims)
    free_hits = [(h, s) for h, s in zip(hits, [p[2] for p in COST_TRANSPARENCY_PATTERNS for _ in re.finditer(p[0], msg.lower())]) if s > 0]
    transparency_hits = [(h, s) for h, s in zip(hits, [p[2] for p in COST_TRANSPARENCY_PATTERNS for _ in re.finditer(p[0], msg.lower())]) if s < 0]

    # Simpler approach: check for "free" claims vs cost mentions
    has_free_claim = bool(re.search(r"\b(free|no cost|no fee|complimentary)\b", msg, re.I))
    has_cost_mention = bool(re.search(r"\b(fee|cost|charge|commission|transparent|disclosed)\b", msg, re.I))

    if has_free_claim:
        l, v = 0.25, 0.40
        expl = "Claims 'free' service — must disclose all compensation sources."
    elif has_cost_mention:
        l, v = 0.82, 0.02
        expl = "Positively mentions costs/fees. Good transparency signal."
    else:
        # Initial outreach often doesn't mention fees — that's OK but noted
        l, v = 0.60, 0.05
        expl = "No fee discussion. Acceptable for initial outreach but note for follow-up."

    u = _clamp(1.0 - l - v)
    return RuleResult(
        rule_id="MIFID2-Art24-4-costs",
        rule_name="Cost and charges transparency",
        regulation="MiFID_II",
        opinion=ComplianceOpinion.create(l, v, u, 0.4),
        explanation=expl,
        flagged_phrases=[h[0] for h in hits if any(p[2] > 0 for p in COST_TRANSPARENCY_PATTERNS if re.search(p[0], h[0], re.I))],
        suggested_fixes=["Add disclosure about compensation structure" if has_free_claim else ""],
    )


def check_best_interest(msg: str, ctx: ProspectContext) -> RuleResult:
    """MiFID II Article 24(1) — Best interest obligation.

    Higher bar than US suitability. Advisor must act in client's best
    interest. Claims of independence or fiduciary duty must be accurate.
    Messages should not prioritize advisor's interests over client's.
    """
    hits, severity = _scan_weighted(msg, BEST_INTEREST_SIGNALS)

    # Check for self-serving language
    self_serving = bool(re.search(
        r"\b(our (growth|goal|target)|we need|bring in|our book)\b",
        msg, re.I,
    ))

    # Check for client-centric language
    client_centric = bool(re.search(
        r"\b(your (goals|needs|situation|interests)|help you|serve you|for you)\b",
        msg, re.I,
    ))

    if self_serving:
        l, v = 0.20, 0.45
        expl = "Self-serving language detected. Must prioritize client's best interest."
    elif client_centric and not hits:
        l, v = 0.80, 0.02
        expl = "Client-centric framing. Consistent with best interest obligation."
    elif hits:
        l, v = 0.55, 0.10
        expl = f"Claims requiring verification: {[h[1] for h in hits[:2]]}. Ensure accuracy."
    else:
        l, v = 0.60, 0.05
        expl = "Neutral tone. No best-interest red flags."

    u = _clamp(1.0 - l - v)
    return RuleResult(
        rule_id="MIFID2-Art24-1-best-interest",
        rule_name="Best interest obligation",
        regulation="MiFID_II",
        opinion=ComplianceOpinion.create(l, v, u, 0.4),
        explanation=expl,
        flagged_phrases=[h[0] for h in hits],
    )


def check_cross_border_solicitation(msg: str, ctx: ProspectContext) -> RuleResult:
    """MiFID II — Cross-border solicitation rules.

    Outreach to EU residents triggers MiFID II even from a US firm.
    Must have appropriate regulatory passport or exemption.
    Flag when message targets EU without acknowledging regulatory context.
    """
    hits, severity = _scan_weighted(msg, CROSS_BORDER_SIGNALS)

    # Check if prospect location suggests EU
    eu_location = False
    if ctx.prospect_location:
        eu_keywords = ["uk", "london", "eu", "europe", "germany", "france",
                       "netherlands", "ireland", "luxembourg", "switzerland",
                       "spain", "italy", "belgium", "austria", "sweden",
                       "denmark", "finland", "norway", "portugal"]
        loc_lower = ctx.prospect_location.lower()
        eu_location = any(kw in loc_lower for kw in eu_keywords)

    if eu_location and not hits:
        l, v = 0.30, 0.25
        expl = (f"Prospect in {ctx.prospect_location} — MiFID II likely applies. "
                "No regulatory acknowledgment in message.")
    elif eu_location and hits:
        l, v = 0.55, 0.10
        expl = f"EU prospect with some regulatory awareness: {[h[1] for h in hits[:2]]}."
    elif hits:
        l, v = 0.50, 0.10
        expl = f"Cross-border references detected: {[h[1] for h in hits[:2]]}. Verify passport."
    else:
        # Non-EU prospect — rule less relevant
        l, v = 0.75, 0.02
        expl = "No EU cross-border indicators. Rule may not apply."

    u = _clamp(1.0 - l - v)
    return RuleResult(
        rule_id="MIFID2-cross-border",
        rule_name="Cross-border solicitation compliance",
        regulation="MiFID_II",
        opinion=ComplianceOpinion.create(l, v, u, 0.5),
        explanation=expl,
        flagged_phrases=[h[0] for h in hits],
    )


# ═══════════════════════════════════════════════════════════════════
# BUILD AND REGISTER
# ═══════════════════════════════════════════════════════════════════

MIFID2_REGULATION = Regulation(
    regulation_id="MiFID_II",
    regulation_name="Markets in Financial Instruments Directive II (EU)",
    base_rate=0.4,
    metadata={
        "jurisdiction": "European Union / EEA",
        "key_articles": ["24(1)", "24(3)", "24(4)", "25"],
        "regulator": "ESMA + National Competent Authorities",
    },
    rules=[
        RuleDefinition("MIFID2-Art25-suitability", "Suitability assessment required",
            "MiFID II Article 25: Cannot assume suitability without proper assessment.",
            checker=check_suitability_assessment, severity="critical"),
        RuleDefinition("MIFID2-Art24-3-fair-clear", "Fair, clear, and not misleading",
            "MiFID II Article 24(3): All communications must be fair, clear, and not misleading.",
            checker=check_fair_clear_not_misleading, severity="critical"),
        RuleDefinition("MIFID2-Art24-4-costs", "Cost and charges transparency",
            "MiFID II Article 24(4): Must not obscure costs; 'free' claims require full disclosure.",
            checker=check_cost_transparency, severity="major"),
        RuleDefinition("MIFID2-Art24-1-best-interest", "Best interest obligation",
            "MiFID II Article 24(1): Must act in client's best interest, not advisor's.",
            checker=check_best_interest, severity="major"),
        RuleDefinition("MIFID2-cross-border", "Cross-border solicitation compliance",
            "MiFID II: EU solicitation triggers MiFID II regardless of advisor's domicile.",
            checker=check_cross_border_solicitation, severity="minor"),
    ],
)

default_registry.register(MIFID2_REGULATION)
