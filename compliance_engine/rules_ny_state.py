"""
NY State Rules — Martin Act + DFS regulations.

Plugin regulation for the Compliant Prospector. New York has some of
the strictest securities laws in the US. The Martin Act (NY General
Business Law §352-353) is uniquely powerful: it does NOT require
proof of intent to defraud, unlike federal securities law.

Key statutes:
    - Martin Act (GBL §352-353): Broad anti-fraud, no intent required
    - 23 NYCRR 500: DFS cybersecurity requirements
    - NY fiduciary standard: Best-interest for annuity sales
    - State registration: Must be registered to solicit NY residents
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

# Martin Act — broader than federal fraud. ANY misleading statement counts.
MARTIN_ACT_PATTERNS = [
    # All the federal fraud patterns PLUS lower-threshold ones
    (r"\bguarantee[ds]?\b", "guarantee (strict liability)", 1.0),
    (r"\bpromise[ds]?\b", "promise (strict liability)", 1.0),
    (r"\brisk[- ]?free\b", "risk-free (strict liability)", 1.0),
    (r"\bensure[ds]?\b", "ensure — promissory under Martin Act", 0.8),
    (r"\bwill (increase|grow|improve|benefit)\b", "forward prediction", 0.7),
    (r"\b(best|top|leading|premier|elite|exclusive)\b", "superlative marketing", 0.5),
    (r"\b(proven|track record)\b", "unverified track record claim", 0.6),
    (r"\b(safe|secure|protected)\s+(investment|portfolio|wealth|assets)\b", "safety claim", 0.9),
    (r"\b(innovative|revolutionary|cutting[- ]?edge|proprietary)\b", "subjective marketing claim", 0.4),
    # Martin Act specifically: concealment or omission
    (r"\b(no (hidden|extra|additional) (fee|cost|charge))\b", "concealment denial", 0.6),
    (r"\b(full|complete|total) (disclosure|transparency)\b", "transparency claim requiring proof", 0.4),
]

# DFS cybersecurity — communications channel compliance
DFS_CYBER_PATTERNS = [
    (r"\b(text me|dm me|hit me up|message me on)\b", "informal channel solicitation", 0.8),
    (r"\b(whatsapp|telegram|signal|snapchat|discord)\b", "unregulated messaging platform", 1.0),
    (r"\b(personal (email|phone|cell|number))\b", "personal channel reference", 0.6),
    (r"\b(off[- ]?(the[- ]?)?record|between us|just between)\b", "off-record suggestion", 0.9),
    (r"\b(encrypted|private (channel|line|chat))\b", "private channel claim", 0.5),
]

# NY fiduciary / best-interest
NY_FIDUCIARY_PATTERNS = [
    (r"\b(annuit(y|ies))\b", "annuity mention — NY best interest applies", 0.6),
    (r"\b(insurance|life policy|variable (annuity|life))\b", "insurance product", 0.5),
    (r"\b(in your best interest|best for you|ideal for you)\b", "best interest claim", 0.4),
    (r"\b(suitab(le|ility)|appropriate for)\b", "suitability language", 0.3),
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


def _is_ny_prospect(ctx: ProspectContext) -> bool:
    """Check if prospect is likely in New York."""
    if not ctx.prospect_location:
        return False
    loc = ctx.prospect_location.lower()
    ny_indicators = ["new york", "ny", "nyc", "manhattan", "brooklyn",
                     "queens", "bronx", "staten island", "long island",
                     "westchester", "albany", "buffalo", "rochester"]
    return any(ind in loc for ind in ny_indicators)


# ═══════════════════════════════════════════════════════════════════
# RULE CHECKERS
# ═══════════════════════════════════════════════════════════════════

def check_martin_act_fraud(msg: str, ctx: ProspectContext) -> RuleResult:
    """Martin Act (GBL §352-353) — Broad anti-fraud, NO INTENT REQUIRED.

    This is the key differentiator from federal law. Under the Martin Act,
    the NY AG can pursue ANY misleading statement without proving the
    advisor intended to deceive. The threshold is much lower.
    """
    hits, severity = _scan_weighted(msg, MARTIN_ACT_PATTERNS)
    is_ny = _is_ny_prospect(ctx)

    # Martin Act applies more strictly to NY prospects
    severity_multiplier = 1.3 if is_ny else 1.0
    effective_severity = severity * severity_multiplier

    if effective_severity >= 3.0:
        l, v = 0.03, 0.80
        expl = (f"Martin Act risk — HIGH. {len(hits)} flagged elements "
                f"(effective severity {effective_severity:.1f}). No intent required for liability.")
    elif effective_severity >= 1.5:
        l, v = 0.15, 0.55
        expl = f"Martin Act concern: {[h[1] for h in hits[:3]]}. Strict liability applies."
    elif effective_severity >= 0.5:
        l, v = 0.40, 0.25
        expl = f"Minor Martin Act flag: '{hits[0][1]}'. Lower threshold than federal law."
    elif effective_severity > 0:
        l, v = 0.55, 0.10
        expl = f"Marginal concern under Martin Act: '{hits[0][1]}'."
    else:
        l, v = 0.78, 0.02
        expl = "No Martin Act concerns. Message is factual and non-misleading."

    if is_ny and hits:
        expl += f" [NY prospect — Martin Act applies with strict liability.]"

    u = _clamp(1.0 - l - v)
    return RuleResult(
        rule_id="NY-Martin-Act-352",
        rule_name="Martin Act broad anti-fraud (no intent required)",
        regulation="NY_State",
        opinion=ComplianceOpinion.create(l, v, u, 0.3),
        explanation=expl,
        flagged_phrases=[h[0] for h in hits],
        suggested_fixes=[f"Remove or soften '{h[0]}' — strict liability under Martin Act" for h in hits],
    )


def check_dfs_cybersecurity(msg: str, ctx: ProspectContext) -> RuleResult:
    """23 NYCRR 500 — DFS cybersecurity requirements.

    Communications must use compliant, auditable channels.
    References to unencrypted or ephemeral messaging platforms are flagged.
    """
    hits, severity = _scan_weighted(msg, DFS_CYBER_PATTERNS)

    if severity >= 1.5:
        l, v = 0.10, 0.65
        expl = f"DFS violation — suggests non-compliant channels: {[h[1] for h in hits[:3]]}."
    elif severity >= 0.5:
        l, v = 0.35, 0.30
        expl = f"Potential DFS concern: '{hits[0][1]}'. Use regulated communication channels."
    elif severity > 0:
        l, v = 0.55, 0.12
        expl = f"Minor channel concern: '{hits[0][1]}'. Prefer compliant channels."
    else:
        l, v = 0.82, 0.02
        expl = "No off-channel communication suggested. DFS-compliant."

    u = _clamp(1.0 - l - v)
    return RuleResult(
        rule_id="NY-DFS-500-cyber",
        rule_name="DFS cybersecurity — compliant channels",
        regulation="NY_State",
        opinion=ComplianceOpinion.create(l, v, u, 0.4),
        explanation=expl,
        flagged_phrases=[h[0] for h in hits],
        suggested_fixes=[f"Remove '{h[0]}' — use firm-approved communication channels" for h in hits],
    )


def check_ny_fiduciary(msg: str, ctx: ProspectContext) -> RuleResult:
    """NY fiduciary / best-interest standard.

    New York's Regulation 187 requires a best-interest standard for
    annuity sales and life insurance recommendations. Stricter than
    federal suitability standard.
    """
    hits, severity = _scan_weighted(msg, NY_FIDUCIARY_PATTERNS)

    has_product_mention = bool(re.search(
        r"\b(annuit|insurance|life policy|variable)\b", msg, re.I
    ))
    has_best_interest_claim = bool(re.search(
        r"\b(best interest|best for you|ideal for)\b", msg, re.I
    ))

    if has_product_mention and has_best_interest_claim:
        l, v = 0.30, 0.30
        expl = ("Product mentioned with best-interest claim. Under NY Reg 187, "
                "must demonstrate suitability analysis was performed.")
    elif has_product_mention:
        l, v = 0.50, 0.10
        expl = "Product reference without recommendation. Acceptable for initial outreach."
    elif has_best_interest_claim:
        l, v = 0.55, 0.10
        expl = "Best-interest claim without specific product. Verify before follow-up."
    else:
        l, v = 0.75, 0.02
        expl = "No product recommendations or best-interest claims. Compliant."

    u = _clamp(1.0 - l - v)
    return RuleResult(
        rule_id="NY-Reg187-fiduciary",
        rule_name="NY fiduciary / best-interest standard",
        regulation="NY_State",
        opinion=ComplianceOpinion.create(l, v, u, 0.4),
        explanation=expl,
        flagged_phrases=[h[0] for h in hits],
    )


def check_ny_registration(msg: str, ctx: ProspectContext) -> RuleResult:
    """NY State registration requirement.

    Advisor must be registered in NY to solicit NY residents.
    Outreach without registration is a violation. This rule checks
    whether the message acknowledges proper registration/licensing.
    """
    is_ny = _is_ny_prospect(ctx)

    has_registration_ref = bool(re.search(
        r"\b(registered|licensed|authorized|regulated)\b", msg, re.I
    ))
    has_firm_ref = bool(re.search(
        r"\b(our firm|we at|my practice|my team at)\b", msg, re.I
    ))

    if is_ny and not has_registration_ref and not has_firm_ref:
        l, v = 0.25, 0.30
        expl = (f"NY prospect ({ctx.prospect_location}) — no firm or registration "
                "reference. Must be registered to solicit in NY.")
    elif is_ny and (has_registration_ref or has_firm_ref):
        l, v = 0.70, 0.05
        expl = "NY prospect with firm/registration context present."
    elif not is_ny:
        l, v = 0.75, 0.02
        expl = "Non-NY prospect. State registration rule less relevant."
    else:
        l, v = 0.50, 0.10
        expl = "Location unclear. Cannot determine registration requirement applicability."

    u = _clamp(1.0 - l - v)
    return RuleResult(
        rule_id="NY-State-registration",
        rule_name="NY state registration requirement",
        regulation="NY_State",
        opinion=ComplianceOpinion.create(l, v, u, 0.5),
        explanation=expl,
    )


# ═══════════════════════════════════════════════════════════════════
# BUILD AND REGISTER
# ═══════════════════════════════════════════════════════════════════

NY_STATE_REGULATION = Regulation(
    regulation_id="NY_State",
    regulation_name="New York State (Martin Act + DFS)",
    base_rate=0.3,
    metadata={
        "jurisdiction": "New York State",
        "key_statutes": ["GBL §352-353 (Martin Act)", "23 NYCRR 500", "Regulation 187"],
        "regulator": "NY Attorney General + DFS",
        "note": "Martin Act does NOT require proof of intent — strict liability for misleading statements.",
    },
    rules=[
        RuleDefinition("NY-Martin-Act-352", "Martin Act broad anti-fraud",
            "NY GBL §352-353: Any misleading statement actionable without proof of intent.",
            checker=check_martin_act_fraud, severity="critical"),
        RuleDefinition("NY-DFS-500-cyber", "DFS cybersecurity — compliant channels",
            "23 NYCRR 500: Communications must use regulated, auditable channels.",
            checker=check_dfs_cybersecurity, severity="major"),
        RuleDefinition("NY-Reg187-fiduciary", "NY fiduciary / best-interest standard",
            "NY Reg 187: Best-interest standard for annuity/insurance recommendations.",
            checker=check_ny_fiduciary, severity="major"),
        RuleDefinition("NY-State-registration", "NY state registration requirement",
            "Must be registered in NY to solicit NY residents.",
            checker=check_ny_registration, severity="minor"),
    ],
)

default_registry.register(NY_STATE_REGULATION)
