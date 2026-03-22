"""
Compliance Algebra Operators — ported from jsonld-ex.

Implements the core operators from the compliance algebra
(Syed, Silaghi, Abujar, Alssadi 2026), adapted for FINRA/SEC
financial advisor outreach compliance.

Operators ported:
    §5  jurisdictional_meet  — conjunction across FINRA + SEC
    §6  compliance_propagation (reserved for future enrichment chains)

The jurisdictional meet is the key differentiator: it computes composite
compliance across both FINRA and SEC simultaneously, producing an opinion
that reflects the strictest applicable requirements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .opinion import ComplianceOpinion, Opinion


# ═══════════════════════════════════════════════════════════════════
# §5 — JURISDICTIONAL MEET (Definition 3, Theorem 1)
# ═══════════════════════════════════════════════════════════════════


def _jurisdictional_meet_pair(
    w1: Opinion, w2: Opinion,
) -> ComplianceOpinion:
    """Binary jurisdictional meet per Definition 3.

    l⊓ = l₁ · l₂           (conjunction: both must be satisfied)
    v⊓ = v₁ + v₂ − v₁·v₂   (disjunction: either constitutes violation)
    u⊓ = (1−v₁)(1−v₂) − l₁·l₂
    a⊓ = a₁ · a₂
    """
    l1, v1 = w1.belief, w1.disbelief
    l2, v2 = w2.belief, w2.disbelief

    l_meet = l1 * l2
    v_meet = v1 + v2 - v1 * v2
    u_meet = (1.0 - v1) * (1.0 - v2) - l1 * l2
    a_meet = w1.base_rate * w2.base_rate

    # Clamp for floating-point safety
    if u_meet < 0.0:
        u_meet = 0.0

    return ComplianceOpinion(
        belief=l_meet,
        disbelief=v_meet,
        uncertainty=u_meet,
        base_rate=a_meet,
    )


def jurisdictional_meet(*opinions: Opinion) -> ComplianceOpinion:
    """Jurisdictional meet — conjunction of compliance requirements.

    Models composite compliance across multiple regulatory jurisdictions
    (FINRA + SEC). Satisfaction of ALL requirements is needed.

    Algebraic structure: bounded commutative monoid.
        Identity:     ω∅ = (1, 0, 0, 1)   — no regulation
        Annihilator:  ω⊥ = (0, 1, 0, 0)   — certain violation

    Properties (Theorem 1):
        - Monotonic restriction: l⊓ ≤ min(l₁, l₂)
        - Monotonic violation:  v⊓ ≥ max(v₁, v₂)
        - Commutative, associative

    Args:
        *opinions: One or more compliance opinions to combine.

    Returns:
        ComplianceOpinion representing composite compliance.
    """
    if len(opinions) == 0:
        raise ValueError("jurisdictional_meet requires at least one opinion")
    if len(opinions) == 1:
        return _as_compliance(opinions[0])

    result = opinions[0]
    for i in range(1, len(opinions)):
        result = _jurisdictional_meet_pair(result, opinions[i])
    return result  # type: ignore[return-value]


def _as_compliance(op: Opinion) -> ComplianceOpinion:
    """Normalize any Opinion to ComplianceOpinion."""
    if isinstance(op, ComplianceOpinion):
        return op
    return ComplianceOpinion.from_opinion(op)


# ═══════════════════════════════════════════════════════════════════
# AUDIT TRAIL — Provenance for explainable compliance
# ═══════════════════════════════════════════════════════════════════


@dataclass
class RuleResult:
    """Result from a single compliance rule check."""

    rule_id: str
    """Unique identifier, e.g. 'FINRA-2210-d1' or 'SEC-206-4'."""

    rule_name: str
    """Human-readable rule name."""

    regulation: str
    """Governing body: 'FINRA' or 'SEC'."""

    opinion: ComplianceOpinion
    """The compliance opinion for this specific rule."""

    explanation: str
    """Why this opinion was assigned — the audit trail text."""

    flagged_phrases: List[str] = field(default_factory=list)
    """Specific phrases in the message that triggered this rule."""

    suggested_fixes: List[str] = field(default_factory=list)
    """Compliant alternative phrasings."""


@dataclass
class ComplianceAudit:
    """Full audit trail for a compliance assessment.

    This is what gets shown in the Rapid Reviewer UI and stored
    for compliance officer oversight.
    """

    message_text: str
    """The outreach message that was assessed."""

    prospect_name: str
    """Who the message is addressed to."""

    rule_results: List[RuleResult] = field(default_factory=list)
    """Per-rule assessments."""

    finra_composite: Optional[ComplianceOpinion] = None
    """Composite FINRA opinion (meet of all FINRA rules)."""

    sec_composite: Optional[ComplianceOpinion] = None
    """Composite SEC opinion (meet of all SEC rules)."""

    overall: Optional[ComplianceOpinion] = None
    """Overall opinion: J⊓(FINRA, SEC)."""

    def compute_composites(self) -> None:
        """Compute composite opinions from individual rule results."""
        finra_rules = [r.opinion for r in self.rule_results if r.regulation == "FINRA"]
        sec_rules = [r.opinion for r in self.rule_results if r.regulation == "SEC"]

        if finra_rules:
            self.finra_composite = jurisdictional_meet(*finra_rules)
        else:
            self.finra_composite = ComplianceOpinion.create(1.0, 0.0, 0.0, 1.0)

        if sec_rules:
            self.sec_composite = jurisdictional_meet(*sec_rules)
        else:
            self.sec_composite = ComplianceOpinion.create(1.0, 0.0, 0.0, 1.0)

        # Overall: FINRA ⊓ SEC
        self.overall = jurisdictional_meet(self.finra_composite, self.sec_composite)

    @property
    def needs_human_review(self) -> bool:
        """Whether this message should route to the Rapid Reviewer."""
        if self.overall is None:
            return True
        return self.overall.compliance_level not in (
            "HIGH_CONFIDENCE_COMPLIANT",
            "LIKELY_COMPLIANT",
        )

    @property
    def flagged_rules(self) -> List[RuleResult]:
        """Rules that flagged issues (violation > 0.3 or uncertainty > 0.5)."""
        return [
            r for r in self.rule_results
            if r.opinion.violation > 0.3 or r.opinion.uncertainty > 0.5
        ]

    def to_dict(self) -> dict:
        """JSON-serializable audit trail for the frontend."""
        return {
            "prospect_name": self.prospect_name,
            "message_preview": self.message_text[:100] + "..."
                if len(self.message_text) > 100 else self.message_text,
            "overall": self.overall.to_dict() if self.overall else None,
            "finra_composite": self.finra_composite.to_dict() if self.finra_composite else None,
            "sec_composite": self.sec_composite.to_dict() if self.sec_composite else None,
            "needs_human_review": self.needs_human_review,
            "flagged_rules": [
                {
                    "rule_id": r.rule_id,
                    "rule_name": r.rule_name,
                    "regulation": r.regulation,
                    "opinion": r.opinion.to_dict(),
                    "explanation": r.explanation,
                    "flagged_phrases": r.flagged_phrases,
                    "suggested_fixes": r.suggested_fixes,
                }
                for r in self.flagged_rules
            ],
            "all_rules": [
                {
                    "rule_id": r.rule_id,
                    "rule_name": r.rule_name,
                    "regulation": r.regulation,
                    "opinion": r.opinion.to_dict(),
                    "explanation": r.explanation,
                }
                for r in self.rule_results
            ],
        }
