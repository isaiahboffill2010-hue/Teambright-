"""
SOX Recordkeeping Rules — Sarbanes-Oxley Act compliance.

Plugin regulation for the Compliant Prospector. SOX applies to
publicly traded firms and their communications. Focus on audit trail
integrity, record retention, and internal controls.

Key sections:
    - SOX §802: Criminal penalties for altering/destroying records
    - SOX §302: CEO/CFO certification of internal controls
    - SOX §404: Management assessment of internal controls
    - SEC Rule 17a-4: Record retention (broker-dealers)
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

EPHEMERAL_CHANNEL_PATTERNS = [
    (r"\b(snapchat|whatsapp|telegram|signal|discord)\b", "ephemeral messaging platform", 1.0),
    (r"\b(disappearing|self[- ]?destruct|auto[- ]?delete|vanish)\b", "message destruction", 1.0),
    (r"\b(delete (this|after)|destroy (this|after))\b", "deletion instruction", 1.0),
    (r"\b(off[- ]?(the[- ]?)?record|between us|just between)\b", "off-record request", 0.9),
    (r"\b(don't (save|keep|record|log|archive) this)\b", "anti-archival instruction", 1.0),
    (r"\b(dm me|text me|hit me up|message me privately)\b", "informal channel redirect", 0.7),
    (r"\b(personal (email|phone|cell))\b", "personal channel redirect", 0.5),
]

TAMPERING_PATTERNS = [
    (r"\b(edit|modify|change|alter|revise) (this|the|our|my) (record|message|email|communication)\b",
     "record modification", 0.8),
    (r"\b(don't (tell|mention|include|report|disclose))\b", "concealment instruction", 0.9),
    (r"\b(keep (this|it) (quiet|private|secret|confidential))\b", "secrecy request", 0.7),
    (r"\b(unofficial|off[- ]?book|unrecorded|undocumented)\b", "evasion language", 0.8),
    (r"\b(cover (up|this)|hide|conceal)\b", "cover-up language", 1.0),
]

INTERNAL_CONTROLS_SIGNALS = [
    (r"\b(compliance|compliance officer|legal|regulatory)\b", "compliance reference", -0.5),
    (r"\b(approved|reviewed|authorized|cleared)\b", "approval reference", -0.4),
    (r"\b(on behalf of|representing|as (an?|the) (advisor|representative))\b", "official capacity", -0.3),
    (r"\b(our firm|the firm|firm[- ]?approved)\b", "firm context", -0.3),
]

AUDIT_COMPLETENESS_SIGNALS = [
    (r"\b(as discussed|per our|following up|as mentioned)\b", "references prior context", 0.3),
    (r"\b(please (see|refer|review) (the |our )?attached)\b", "attachment reference", 0.2),
    (r"\b(for (your|the) record|for documentation)\b", "documentation intent", -0.5),
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

def check_communication_retention(msg: str, ctx: ProspectContext) -> RuleResult:
    """SOX §802 + SEC 17a-4 — Communication retention.

    All business communications must be retained and retrievable.
    Suggesting ephemeral channels or message deletion violates
    recordkeeping obligations.
    """
    hits, severity = _scan_weighted(msg, EPHEMERAL_CHANNEL_PATTERNS)

    if severity >= 2.0:
        l, v = 0.05, 0.80
        expl = (f"Severe recordkeeping violation — suggests non-retainable channels: "
                f"{[h[1] for h in hits[:3]]}. SOX §802 applies.")
    elif severity >= 1.0:
        l, v = 0.15, 0.55
        expl = f"Recordkeeping concern: {[h[1] for h in hits[:2]]}. All communications must be archivable."
    elif severity >= 0.5:
        l, v = 0.40, 0.25
        expl = f"Potential retention issue: '{hits[0][1]}'. Prefer firm-approved channels."
    elif severity > 0:
        l, v = 0.55, 0.12
        expl = f"Minor channel concern: '{hits[0][1]}'."
    else:
        l, v = 0.82, 0.02
        expl = "Communication is through retainable channels. Compliant with retention requirements."

    u = _clamp(1.0 - l - v)
    return RuleResult(
        rule_id="SOX-802-retention",
        rule_name="Communication retention compliance",
        regulation="SOX",
        opinion=ComplianceOpinion.create(l, v, u, 0.3),
        explanation=expl,
        flagged_phrases=[h[0] for h in hits],
        suggested_fixes=[f"Remove '{h[0]}' — use firm-approved, archivable channels" for h in hits],
    )


def check_tampering_prohibition(msg: str, ctx: ProspectContext) -> RuleResult:
    """SOX §802 — Tampering, destruction, concealment prohibition.

    Criminal penalties for altering, destroying, or concealing records.
    Messages must not suggest editing, deleting, or hiding communications.
    """
    hits, severity = _scan_weighted(msg, TAMPERING_PATTERNS)

    if severity >= 1.5:
        l, v = 0.03, 0.85
        expl = (f"SOX §802 VIOLATION — suggests record tampering/concealment: "
                f"{[h[1] for h in hits[:3]]}. Criminal penalties apply.")
    elif severity >= 0.7:
        l, v = 0.15, 0.55
        expl = f"Potential tampering concern: {[h[1] for h in hits[:2]]}."
    elif severity > 0:
        l, v = 0.45, 0.20
        expl = f"Minor concealment flag: '{hits[0][1]}'. Review for intent."
    else:
        l, v = 0.85, 0.02
        expl = "No tampering or concealment language. SOX-compliant."

    u = _clamp(1.0 - l - v)
    return RuleResult(
        rule_id="SOX-802-tampering",
        rule_name="No record tampering or concealment",
        regulation="SOX",
        opinion=ComplianceOpinion.create(l, v, u, 0.3),
        explanation=expl,
        flagged_phrases=[h[0] for h in hits],
        suggested_fixes=[f"Remove '{h[0]}' — SOX §802 prohibits record tampering" for h in hits],
    )


def check_internal_controls(msg: str, ctx: ProspectContext) -> RuleResult:
    """SOX §302/404 — Internal controls reference.

    If the advisor's firm is publicly traded, communications are subject
    to SOX internal controls. Messages should reflect that they are
    sent in official capacity with appropriate oversight.
    """
    ctrl_hits, ctrl_sev = _scan_weighted(msg, INTERNAL_CONTROLS_SIGNALS)

    has_compliance_ref = bool(re.search(
        r"\b(compliance|compliance officer|legal|approved|authorized)\b", msg, re.I
    ))
    has_firm_ref = bool(re.search(
        r"\b(our firm|the firm|firm[- ]?approved|on behalf of)\b", msg, re.I
    ))
    has_personal_framing = bool(re.search(
        r"\b(personally|just me|I (personally|myself)|my own)\b", msg, re.I
    ))

    if has_personal_framing and not has_firm_ref:
        l, v = 0.30, 0.30
        expl = "Personal framing without firm context. SOX requires communications reflect internal controls."
    elif has_firm_ref and has_compliance_ref:
        l, v = 0.82, 0.02
        expl = "Firm context with compliance awareness. Strong internal controls signal."
    elif has_firm_ref:
        l, v = 0.70, 0.05
        expl = "Firm context present. Internal controls implicitly acknowledged."
    else:
        l, v = 0.55, 0.08
        expl = "No explicit internal controls context. Acceptable for initial outreach."

    u = _clamp(1.0 - l - v)
    return RuleResult(
        rule_id="SOX-302-404-controls",
        rule_name="Internal controls compliance",
        regulation="SOX",
        opinion=ComplianceOpinion.create(l, v, u, 0.5),
        explanation=expl,
    )


def check_audit_trail_completeness(msg: str, ctx: ProspectContext) -> RuleResult:
    """SOX — Audit trail completeness.

    Message must be self-contained enough for an auditor to understand
    context without supplementary materials. Vague references to
    prior undocumented conversations are flagged.
    """
    text = msg.strip()
    issues = []

    # Too short to be meaningful
    if len(text) < 20:
        issues.append("too short for meaningful audit record")

    # References to undocumented prior context
    if re.search(r"\b(as (we|I) (discussed|mentioned|talked about))\b", text, re.I):
        if not re.search(r"\b(email|meeting|call on|per our \w+ (call|meeting))\b", text, re.I):
            issues.append("references undocumented prior conversation")

    # Vague pronoun references without antecedent
    if re.search(r"\b(that thing|the thing|you know what|the usual)\b", text, re.I):
        issues.append("vague references — auditor cannot determine context")

    # Abbreviations or code words that obscure meaning
    if re.search(r"\b(the package|the deal|the arrangement|our arrangement)\b", text, re.I):
        issues.append("ambiguous 'arrangement' language")

    if len(issues) >= 2:
        l, v = 0.20, 0.40
        expl = f"Audit trail gaps: {', '.join(issues)}."
    elif len(issues) == 1:
        l, v = 0.45, 0.18
        expl = f"Minor audit concern: {issues[0]}."
    else:
        # Positive signals for self-contained messages
        has_clear_purpose = bool(re.search(
            r"\b(I wanted to|reaching out|I'd like to|writing to)\b", text, re.I
        ))
        if has_clear_purpose:
            l, v = 0.85, 0.02
            expl = "Self-contained message with clear purpose. Good audit trail."
        else:
            l, v = 0.70, 0.03
            expl = "Message is reasonably self-contained for audit purposes."

    u = _clamp(1.0 - l - v)
    return RuleResult(
        rule_id="SOX-audit-completeness",
        rule_name="Audit trail completeness",
        regulation="SOX",
        opinion=ComplianceOpinion.create(l, v, u, 0.5),
        explanation=expl,
        flagged_phrases=issues,
        suggested_fixes=[f"Address: {i}" for i in issues],
    )


# ═══════════════════════════════════════════════════════════════════
# BUILD AND REGISTER
# ═══════════════════════════════════════════════════════════════════

SOX_REGULATION = Regulation(
    regulation_id="SOX",
    regulation_name="Sarbanes-Oxley Act — Recordkeeping & Internal Controls",
    base_rate=0.5,
    metadata={
        "jurisdiction": "United States (federal, publicly traded firms)",
        "key_sections": ["§802 (record destruction)", "§302 (CEO/CFO certification)", "§404 (internal controls)"],
        "regulator": "SEC + PCAOB",
        "note": "SOX §802 carries criminal penalties — up to 20 years imprisonment for record destruction.",
    },
    rules=[
        RuleDefinition("SOX-802-retention", "Communication retention compliance",
            "SOX §802: All business communications must be retained and retrievable.",
            checker=check_communication_retention, severity="critical"),
        RuleDefinition("SOX-802-tampering", "No record tampering or concealment",
            "SOX §802: Criminal penalties for altering, destroying, or concealing records.",
            checker=check_tampering_prohibition, severity="critical"),
        RuleDefinition("SOX-302-404-controls", "Internal controls compliance",
            "SOX §302/404: Communications must reflect appropriate internal controls.",
            checker=check_internal_controls, severity="major"),
        RuleDefinition("SOX-audit-completeness", "Audit trail completeness",
            "SOX: Messages must be self-contained enough for auditor review.",
            checker=check_audit_trail_completeness, severity="major"),
    ],
)

default_registry.register(SOX_REGULATION)
