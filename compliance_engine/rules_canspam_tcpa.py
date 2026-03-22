"""
CAN-SPAM / TCPA Rules — Email & Phone Outreach Compliance.

Plugin regulation for the Compliant Prospector. These rules govern
the outreach CHANNEL itself, not just the content. Every commercial
email must comply with CAN-SPAM; every phone/text outreach must
comply with TCPA.

Key statutes:
    - CAN-SPAM Act (15 USC §7701-7713): Commercial email requirements
    - TCPA (47 USC §227): Telephone Consumer Protection Act
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

DECEPTIVE_HEADER_PATTERNS = [
    (r"\b(re:|fw:|fwd:)\s", "fake reply/forward prefix", 0.8),
    (r"\b(urgent|important|action required|time sensitive)\b.*\b(subject|regarding)\b",
     "urgency in header context", 0.6),
    (r"\b(your account|your order|invoice|receipt|confirm)\b", "transactional impersonation", 0.9),
    (r"\b(congratulations|you('ve)? won|selected|chosen)\b", "prize language", 1.0),
]

OPT_OUT_SIGNALS = [
    (r"\b(unsubscribe|opt[- ]?out|stop receiving)\b", "opt-out mechanism", -1.0),
    (r"\b(manage (your )?(preferences|subscriptions|emails))\b", "preference management", -0.8),
    (r"\b(if you (no longer|don't|do not) (wish|want))\b", "opt-out language", -0.7),
    (r"\b(remove (me|yourself) from)\b", "removal instruction", -0.6),
]

COMMERCIAL_ID_PATTERNS = [
    (r"\b(advertisement|sponsored|promotional|commercial)\b", "commercial identification", -0.5),
    (r"\b(this (is|message is) (a|an) (advertisement|solicitation))\b", "explicit ad ID", -1.0),
]

PHYSICAL_ADDRESS_PATTERNS = [
    (r"\d{1,5}\s+\w+\s+(st|street|ave|avenue|blvd|boulevard|rd|road|dr|drive|ln|lane)\b",
     "street address", -0.8),
    (r"\b\d{5}(-\d{4})?\b", "zip code", -0.3),
    (r"\b(suite|ste|floor|fl)\s*#?\s*\d+\b", "suite/floor number", -0.3),
]

TCPA_CONSENT_PATTERNS = [
    (r"\b(call(ing)? you|phone you|reach you (by|via) phone)\b", "phone outreach reference", 0.5),
    (r"\b(text(ing)?|sms|message you)\b", "text outreach reference", 0.6),
    (r"\b(automated|auto[- ]?dial|robo[- ]?call|pre[- ]?recorded)\b", "automated contact", 1.0),
    (r"\b(with your (permission|consent)|you (agreed|consented|opted in))\b",
     "consent acknowledgment", -0.8),
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

def check_accurate_headers(msg: str, ctx: ProspectContext) -> RuleResult:
    """CAN-SPAM §7704(a)(1-2) — Accurate header information.

    "From," "To," and routing info must not be deceptive.
    Subject lines must not mislead about content.
    """
    hits, severity = _scan_weighted(msg, DECEPTIVE_HEADER_PATTERNS)

    if severity >= 1.5:
        l, v = 0.10, 0.70
        expl = f"Deceptive header/subject patterns: {[h[1] for h in hits[:3]]}. CAN-SPAM violation."
    elif severity >= 0.6:
        l, v = 0.35, 0.35
        expl = f"Potentially deceptive framing: '{hits[0][1]}'."
    elif severity > 0:
        l, v = 0.55, 0.15
        expl = f"Minor header concern: '{hits[0][1]}'."
    else:
        l, v = 0.82, 0.02
        expl = "No deceptive header or subject line patterns."

    u = _clamp(1.0 - l - v)
    return RuleResult(
        rule_id="CANSPAM-7704-headers",
        rule_name="Accurate header information",
        regulation="CAN_SPAM_TCPA",
        opinion=ComplianceOpinion.create(l, v, u, 0.4),
        explanation=expl,
        flagged_phrases=[h[0] for h in hits],
        suggested_fixes=[f"Remove '{h[0]}' — deceptive header under CAN-SPAM" for h in hits],
    )


def check_opt_out_mechanism(msg: str, ctx: ProspectContext) -> RuleResult:
    """CAN-SPAM §7704(a)(3) — Opt-out mechanism required.

    Every commercial email must include a way to unsubscribe.
    This is a hard requirement — no exceptions for "relationship" emails.
    """
    has_opt_out = bool(re.search(
        r"\b(unsubscribe|opt[- ]?out|stop receiving|manage.*preferences)\b", msg, re.I
    ))

    if has_opt_out:
        l, v = 0.85, 0.02
        expl = "Opt-out mechanism present. CAN-SPAM compliant."
    else:
        l, v = 0.15, 0.55
        expl = "No opt-out mechanism detected. CAN-SPAM requires unsubscribe option in every commercial email."

    u = _clamp(1.0 - l - v)
    return RuleResult(
        rule_id="CANSPAM-7704-optout",
        rule_name="Opt-out mechanism required",
        regulation="CAN_SPAM_TCPA",
        opinion=ComplianceOpinion.create(l, v, u, 0.3),
        explanation=expl,
        flagged_phrases=[] if has_opt_out else ["(missing opt-out mechanism)"],
        suggested_fixes=[] if has_opt_out else [
            "Add unsubscribe link or opt-out instructions to the message."
        ],
    )


def check_commercial_identification(msg: str, ctx: ProspectContext) -> RuleResult:
    """CAN-SPAM §7704(a)(5) — Identify as advertisement.

    Commercial emails must be identifiable as solicitations.
    Disguising a sales message as personal correspondence violates this.
    """
    has_commercial_id = bool(re.search(
        r"\b(advertisement|solicitation|promotional|commercial message)\b", msg, re.I
    ))

    has_business_context = bool(re.search(
        r"\b(our firm|my practice|advisory|financial (advisor|planner)|wealth management)\b",
        msg, re.I
    ))

    has_personal_disguise = bool(re.search(
        r"\b(just (wanted to|thought|checking)|between (us|you and me)|as a friend)\b",
        msg, re.I
    ))

    if has_commercial_id:
        l, v = 0.85, 0.02
        expl = "Explicitly identified as commercial communication. Compliant."
    elif has_business_context and not has_personal_disguise:
        l, v = 0.70, 0.05
        expl = "Business context establishes commercial nature implicitly."
    elif has_personal_disguise:
        l, v = 0.20, 0.50
        expl = "Message disguised as personal correspondence. Must identify commercial purpose."
    else:
        l, v = 0.45, 0.15
        expl = "Commercial purpose not clearly established. Consider adding business context."

    u = _clamp(1.0 - l - v)
    return RuleResult(
        rule_id="CANSPAM-7704-commercial-id",
        rule_name="Commercial identification",
        regulation="CAN_SPAM_TCPA",
        opinion=ComplianceOpinion.create(l, v, u, 0.4),
        explanation=expl,
    )


def check_physical_address(msg: str, ctx: ProspectContext) -> RuleResult:
    """CAN-SPAM §7704(a)(5)(A)(iii) — Physical address required.

    Must include sender's valid physical postal address.
    """
    has_address = bool(re.search(
        r"\d{1,5}\s+\w+\s+(st|street|ave|avenue|blvd|boulevard|rd|road|dr|drive)",
        msg, re.I
    ))
    has_zip = bool(re.search(r"\b\d{5}(-\d{4})?\b", msg))

    if has_address and has_zip:
        l, v = 0.85, 0.02
        expl = "Physical address with zip code present. CAN-SPAM compliant."
    elif has_address:
        l, v = 0.70, 0.05
        expl = "Physical address present but zip code missing."
    else:
        l, v = 0.15, 0.55
        expl = "No physical address. CAN-SPAM requires valid postal address in every commercial email."

    u = _clamp(1.0 - l - v)
    return RuleResult(
        rule_id="CANSPAM-7704-address",
        rule_name="Physical address required",
        regulation="CAN_SPAM_TCPA",
        opinion=ComplianceOpinion.create(l, v, u, 0.3),
        explanation=expl,
        flagged_phrases=[] if has_address else ["(missing physical address)"],
        suggested_fixes=[] if has_address else [
            "Include firm's physical mailing address in the message."
        ],
    )


def check_tcpa_consent(msg: str, ctx: ProspectContext) -> RuleResult:
    """TCPA §227 — Prior express consent for phone/text outreach.

    Cannot cold-call or text without prior express consent.
    Messages referencing phone calls need consent acknowledgment.
    Automated/robocall references are especially scrutinized.
    """
    hits, severity = _scan_weighted(msg, TCPA_CONSENT_PATTERNS)

    has_phone_ref = bool(re.search(
        r"\b(call|phone|text|sms|reach you)\b", msg, re.I
    ))
    has_automated_ref = bool(re.search(
        r"\b(automated|auto[- ]?dial|robo|pre[- ]?recorded)\b", msg, re.I
    ))
    has_consent_ack = bool(re.search(
        r"\b(with your (permission|consent)|you (agreed|consented|opted))\b", msg, re.I
    ))

    if has_automated_ref:
        l, v = 0.05, 0.80
        expl = "References automated calling — requires prior express WRITTEN consent under TCPA."
    elif has_phone_ref and not has_consent_ack:
        l, v = 0.35, 0.25
        expl = "References phone/text contact without consent acknowledgment."
    elif has_phone_ref and has_consent_ack:
        l, v = 0.75, 0.05
        expl = "Phone reference with consent acknowledgment. Compliant if consent is documented."
    else:
        l, v = 0.78, 0.02
        expl = "No phone/text references. TCPA less applicable to email-only outreach."

    u = _clamp(1.0 - l - v)
    return RuleResult(
        rule_id="TCPA-227-consent",
        rule_name="Prior consent for phone/text contact",
        regulation="CAN_SPAM_TCPA",
        opinion=ComplianceOpinion.create(l, v, u, 0.4),
        explanation=expl,
        flagged_phrases=[h[0] for h in hits if h[1] != "consent acknowledgment"],
        suggested_fixes=["Add consent acknowledgment or remove phone/text reference" if has_phone_ref and not has_consent_ack else ""],
    )


# ═══════════════════════════════════════════════════════════════════
# BUILD AND REGISTER
# ═══════════════════════════════════════════════════════════════════

CANSPAM_TCPA_REGULATION = Regulation(
    regulation_id="CAN_SPAM_TCPA",
    regulation_name="CAN-SPAM Act & Telephone Consumer Protection Act",
    base_rate=0.4,
    metadata={
        "jurisdiction": "United States (federal)",
        "key_statutes": ["15 USC §7701-7713 (CAN-SPAM)", "47 USC §227 (TCPA)"],
        "regulator": "FTC (CAN-SPAM) + FCC (TCPA)",
        "note": "CAN-SPAM governs email; TCPA governs phone/text. Both apply to outreach.",
    },
    rules=[
        RuleDefinition("CANSPAM-7704-headers", "Accurate header information",
            "CAN-SPAM §7704(a)(1-2): No deceptive headers or subject lines.",
            checker=check_accurate_headers, severity="critical"),
        RuleDefinition("CANSPAM-7704-optout", "Opt-out mechanism required",
            "CAN-SPAM §7704(a)(3): Every commercial email must have unsubscribe option.",
            checker=check_opt_out_mechanism, severity="critical"),
        RuleDefinition("CANSPAM-7704-commercial-id", "Commercial identification",
            "CAN-SPAM §7704(a)(5): Must identify message as commercial/solicitation.",
            checker=check_commercial_identification, severity="major"),
        RuleDefinition("CANSPAM-7704-address", "Physical address required",
            "CAN-SPAM §7704(a)(5)(A)(iii): Must include valid physical postal address.",
            checker=check_physical_address, severity="major"),
        RuleDefinition("TCPA-227-consent", "Prior consent for phone/text contact",
            "TCPA §227: Cannot cold-call/text without prior express consent.",
            checker=check_tcpa_consent, severity="critical"),
    ],
)

default_registry.register(CANSPAM_TCPA_REGULATION)
