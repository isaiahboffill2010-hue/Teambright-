"""
SEC Rules — granular, context-aware compliance checking.

Expanded with additional rules beyond 206(4)-1:
    - Anti-fraud (§206)
    - Marketing Rule testimonials
    - Cherry-picked performance
    - Misleading relationship framing
    - Title accuracy
    - Recordkeeping implications (17a-4)
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
# PATTERNS (weighted)
# ═══════════════════════════════════════════════════════════════════

TESTIMONIAL_PATTERNS = [
    (r"\b(my|our) clients? (have|has) (seen|experienced|achieved|earned|made)\b", "implied testimonial", 1.0),
    (r"\bjust like (client|investor|mr|ms|dr)\b", "named testimonial", 1.0),
    (r"\b(other|many|several|some) (clients?|investors?) (have|has|are)\b", "group testimonial", 0.8),
    (r"\b(a client|one investor) (recently|just|of mine)\b", "anecdotal testimonial", 0.7),
    (r"\b(success stor(y|ies)|case stud(y|ies))\b", "success story reference", 0.5),
    (r"\b(results? (speak|show))\b", "implied track record", 0.4),
]

MISLEADING_RELATIONSHIP_PATTERNS = [
    (r"\b(replace|switch from|leave|fire|drop|ditch|dump)\s+(your|their)\s+(current\s+)?(advisor|adviser|planner|manager)\b", "replacement suggestion", 1.0),
    (r"\b(better than|superior to|more than)\s+(your|their)\s+(current\s+)?(advisor|adviser)\b", "comparative disparagement", 1.0),
    (r"\byour (advisor|adviser) (is|isn't|can't|won't|doesn't|failed|missed)\b", "advisor criticism", 0.9),
    (r"\b(why (are you|still) (with|using|paying))\b", "questioning current advisor", 0.8),
    (r"\b(underperform|underserv|neglect|overlook)(s|ed|ing)?\b", "disparagement", 0.6),
]

COMPLEMENT_SIGNALS = [
    (r"\bcomplement\b", "complement language", 1.0),
    (r"\bancillary\b", "ancillary positioning", 1.0),
    (r"\bin addition to\b", "additive framing", 0.8),
    (r"\balongside\b", "alongside framing", 0.8),
    (r"\bnot (to )?(replace|replacing)\b", "explicit non-replacement", 1.0),
    (r"\bexisting (advisor|adviser|team|relationship)\b", "acknowledges existing", 0.9),
    (r"\bwithout disrupting\b", "non-disruptive", 0.7),
]

CHERRY_PICKING_PATTERNS = [
    (r"\b(our best|top performing|highest return|strongest)\s+(fund|strategy|portfolio|account|quarter)\b", "cherry-picked performance", 1.0),
    (r"\bup \d+% (this|last) (year|quarter|month)\b", "selective timeframe", 0.8),
    (r"\b(since|from) (inception|launch|2020|2021|2022|2023|2024|2025)\b", "selective start date", 0.5),
    (r"\b(handpicked|selected|curated) (results|performance|track record)\b", "curated results", 0.7),
]

MISLEADING_TITLE_PATTERNS = [
    (r"\bcertified financial planner\b", "CFP usage", 0.8),
    (r"\bchartered financial analyst\b", "CFA usage", 0.8),
    (r"\bfiduciary\b", "fiduciary claim", 0.7),
    (r"\bcertified (public accountant|wealth)\b", "CPA/CWS usage", 0.6),
    (r"\bregistered investment advis[eo]r\b", "RIA claim", 0.5),
]

MATERIAL_MISREPRESENTATION_PATTERNS = [
    (r"\b(we manage|managing)\s+\$?\d+\s*(billion|million|B|M)\b", "AUM claim", 0.6),
    (r"\b(award[- ]winning|nationally recognized)\b", "award claim", 0.5),
    (r"\b(founded|established)\s+in\s+\d{4}\b", "founding claim", 0.3),
    (r"\b\d+\+?\s+(years?|decades?)\s+(of experience|experience|serving)\b", "experience claim", 0.3),
]


# ═══════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════

def _scan_w(text: str, patterns: List[Tuple[str, str, float]]) -> Tuple[List[Tuple[str, str]], float]:
    text_lower = text.lower()
    hits = []
    severity = 0.0
    for pattern, label, weight in patterns:
        for m in re.finditer(pattern, text_lower):
            hits.append((m.group(), label))
            severity += weight
    return hits, severity


def _clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


# ═══════════════════════════════════════════════════════════════════
# RULE CHECKERS
# ═══════════════════════════════════════════════════════════════════

def check_no_testimonials(msg: str, ctx: ProspectContext) -> RuleResult:
    """SEC 206(4)-1 — Testimonials/endorsements (Marketing Rule)."""
    hits, severity = _scan_w(msg, TESTIMONIAL_PATTERNS)

    if severity >= 1.5:
        l, v = 0.05, 0.70
        expl = f"Multiple testimonial references (severity {severity:.1f}). High risk in cold outreach."
    elif severity >= 0.8:
        l, v = 0.15, 0.50
        expl = f"Testimonial language: {[h[1] for h in hits[:2]]}. Requires proper disclosures."
    elif severity > 0:
        l, v = 0.35, 0.25
        expl = f"Mild testimonial implication: '{hits[0][1]}'. Consider rephrasing."
    else:
        l, v = 0.78, 0.02
        expl = "No testimonial or endorsement language."

    u = _clamp(1.0 - l - v)
    return RuleResult(
        rule_id="SEC-206-4-1-testimonials",
        rule_name="No improper testimonials or endorsements",
        regulation="SEC",
        opinion=ComplianceOpinion.create(l, v, u, 0.4),
        explanation=expl,
        flagged_phrases=[h[0] for h in hits],
        suggested_fixes=[f"Remove '{h[0]}' — testimonials need specific disclosures" for h in hits],
    )


def check_no_misleading_relationship(msg: str, ctx: ProspectContext) -> RuleResult:
    """SEC §206 anti-fraud + Advisers Act — relationship framing."""
    neg_hits, neg_sev = _scan_w(msg, MISLEADING_RELATIONSHIP_PATTERNS)
    pos_hits, pos_sev = _scan_w(msg, COMPLEMENT_SIGNALS)

    if neg_sev >= 1.5:
        l, v = 0.03, 0.85
        expl = f"Strongly suggests replacing advisor (severity {neg_sev:.1f}). Anti-fraud violation."
    elif neg_sev >= 0.8:
        l, v = 0.10, 0.65
        expl = f"Replacement language detected: {[h[1] for h in neg_hits[:2]]}."
    elif neg_sev > 0:
        l, v = 0.30, 0.35
        expl = f"Potentially disparaging: '{neg_hits[0][1]}'. Needs softer framing."
    elif pos_sev >= 1.5:
        l, v = 0.88, 0.01
        expl = f"Strong complementary positioning ({len(pos_hits)} signals). Excellent."
    elif pos_sev > 0:
        l, v = 0.80, 0.02
        expl = f"Complementary framing present: {[h[1] for h in pos_hits[:2]]}."
    else:
        l, v = 0.50, 0.10
        expl = "No replacement or complement language. Add ancillary framing."

    u = _clamp(1.0 - l - v)
    return RuleResult(
        rule_id="SEC-206-relationship",
        rule_name="No misleading advisory relationship framing",
        regulation="SEC",
        opinion=ComplianceOpinion.create(l, v, u, 0.3),
        explanation=expl,
        flagged_phrases=[h[0] for h in neg_hits],
        suggested_fixes=[f"Replace '{h[0]}' with complementary framing" for h in neg_hits]
            + (["Add 'complement' or 'ancillary' language"] if not pos_hits and not neg_hits else []),
    )


def check_no_cherry_picking(msg: str, ctx: ProspectContext) -> RuleResult:
    """SEC 206(4)-1(a)(2) — No misleading performance data."""
    hits, severity = _scan_w(msg, CHERRY_PICKING_PATTERNS)

    if severity >= 1.5:
        l, v = 0.05, 0.70
    elif severity >= 0.8:
        l, v = 0.20, 0.45
    elif severity > 0:
        l, v = 0.45, 0.20
    else:
        l, v = 0.80, 0.02

    u = _clamp(1.0 - l - v)
    expl = f"Cherry-picked data: {[h[1] for h in hits[:2]]}." if hits else "No cherry-picked performance."

    return RuleResult(
        rule_id="SEC-206-4-1-performance",
        rule_name="No cherry-picked performance data",
        regulation="SEC",
        opinion=ComplianceOpinion.create(l, v, u, 0.4),
        explanation=expl,
        flagged_phrases=[h[0] for h in hits],
        suggested_fixes=[f"Remove '{h[0]}' or include full performance context" for h in hits],
    )


def check_title_accuracy(msg: str, ctx: ProspectContext) -> RuleResult:
    """SEC — Professional titles must be accurate."""
    hits, severity = _scan_w(msg, MISLEADING_TITLE_PATTERNS)

    if severity >= 1.5:
        l, v = 0.20, 0.20
        expl = f"Multiple designations used ({len(hits)}). Each must be verified current."
    elif severity > 0:
        l, v = 0.35, 0.10
        expl = f"Designation: '{hits[0][1]}'. Verify current and accurate."
    else:
        l, v = 0.82, 0.02
        expl = "No professional designations to verify."

    u = _clamp(1.0 - l - v)
    return RuleResult(
        rule_id="SEC-title-accuracy",
        rule_name="Professional title accuracy",
        regulation="SEC",
        opinion=ComplianceOpinion.create(l, v, u, 0.5),
        explanation=expl,
        flagged_phrases=[h[0] for h in hits],
        suggested_fixes=[f"Verify '{h[0]}' is current and properly registered" for h in hits],
    )


def check_material_misrepresentation(msg: str, ctx: ProspectContext) -> RuleResult:
    """SEC §206 — No material misrepresentations about firm/advisor.

    NEW RULE: Claims about AUM, awards, experience must be verifiable.
    """
    hits, severity = _scan_w(msg, MATERIAL_MISREPRESENTATION_PATTERNS)

    if severity >= 1.0:
        l, v = 0.30, 0.15
        expl = f"Verifiable claims detected: {[h[1] for h in hits[:3]]}. Must be accurate and current."
    elif severity > 0:
        l, v = 0.50, 0.08
        expl = f"Claim '{hits[0][1]}' — ensure documentation supports this."
    else:
        l, v = 0.82, 0.02
        expl = "No material claims about firm or advisor to verify."

    u = _clamp(1.0 - l - v)
    return RuleResult(
        rule_id="SEC-206-material",
        rule_name="No material misrepresentation",
        regulation="SEC",
        opinion=ComplianceOpinion.create(l, v, u, 0.4),
        explanation=expl,
        flagged_phrases=[h[0] for h in hits],
        suggested_fixes=[f"Document evidence for '{h[0]}' claim" for h in hits],
    )


def check_recordkeeping_ready(msg: str, ctx: ProspectContext) -> RuleResult:
    """SEC 17a-4 / 204-2 — Recordkeeping readiness.

    NEW RULE: Every outreach message should be structured for archival.
    This is an advisory check — the system itself handles recordkeeping,
    but we flag messages that would be problematic to archive.
    """
    issues = []
    text = msg.strip()

    # Check: message is non-empty
    if len(text) < 20:
        issues.append("too short to constitute meaningful communication")

    # Check: no informal language that suggests off-channel communication
    if re.search(r"\b(text me|DM me|hit me up|slide into)\b", text, re.I):
        issues.append("suggests off-channel communication")

    # Check: no references to ephemeral channels
    if re.search(r"\b(snapchat|whatsapp|signal|telegram|disappearing)\b", text, re.I):
        issues.append("references ephemeral messaging platform")

    if len(issues) >= 2:
        l, v = 0.20, 0.45
    elif len(issues) == 1:
        l, v = 0.45, 0.20
    else:
        l, v = 0.85, 0.02

    u = _clamp(1.0 - l - v)
    expl = f"Recordkeeping issues: {', '.join(issues)}." if issues else "Message is structured for compliant archival."

    return RuleResult(
        rule_id="SEC-17a4-recordkeeping",
        rule_name="Recordkeeping readiness",
        regulation="SEC",
        opinion=ComplianceOpinion.create(l, v, u, 0.5),
        explanation=expl,
        flagged_phrases=issues,
        suggested_fixes=[f"Address: {i}" for i in issues],
    )


# ═══════════════════════════════════════════════════════════════════
# BUILD AND REGISTER
# ═══════════════════════════════════════════════════════════════════

SEC_REGULATION = Regulation(
    regulation_id="SEC",
    regulation_name="Securities and Exchange Commission",
    base_rate=0.4,
    metadata={
        "data_api": "https://data.sec.gov",
        "key_rules": ["206(4)-1", "17a-4", "204-2"],
    },
    rules=[
        RuleDefinition("SEC-206-4-1-testimonials", "No improper testimonials",
            "SEC Marketing Rule 206(4)-1: Testimonials need disclosures.",
            checker=check_no_testimonials, severity="critical"),
        RuleDefinition("SEC-206-relationship", "No misleading relationship framing",
            "SEC §206: Cannot mislead about advisory relationship.",
            checker=check_no_misleading_relationship, severity="critical"),
        RuleDefinition("SEC-206-4-1-performance", "No cherry-picked performance",
            "SEC 206(4)-1(a)(2): Performance must not be misleading.",
            checker=check_no_cherry_picking, severity="major"),
        RuleDefinition("SEC-206-material", "No material misrepresentation",
            "SEC §206: Claims about firm/advisor must be verifiable.",
            checker=check_material_misrepresentation, severity="major"),
        RuleDefinition("SEC-title-accuracy", "Professional title accuracy",
            "SEC: Designations must be current and accurate.",
            checker=check_title_accuracy, severity="minor"),
        RuleDefinition("SEC-17a4-recordkeeping", "Recordkeeping readiness",
            "SEC 17a-4/204-2: Communications must be archivable.",
            checker=check_recordkeeping_ready, severity="advisory"),
    ],
)

default_registry.register(SEC_REGULATION)
