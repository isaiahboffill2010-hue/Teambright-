"""
Subjective Logic Opinion — standalone port for hackathon.

Ported from jsonld-ex compliance_algebra (Syed, Silaghi, Abujar, Alssadi 2026).
Zero external dependencies. Implements Jøsang's Subjective Logic (2016)
opinion model with compliance-domain semantics for FINRA/SEC assessment.

An opinion ω = (b, d, u, a) represents:
    b = belief      (evidence FOR compliance)
    d = disbelief   (evidence AGAINST compliance / for violation)
    u = uncertainty  (absence of evidence)
    a = base rate    (prior probability of compliance)
    Constraint: b + d + u = 1

Key insight: unlike scalar confidence, opinions distinguish between
"probably compliant (strong evidence)" and "uncertain (no evidence)" —
states that binary compliance systems collapse into one classification.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

_ADDITIVITY_TOL = 1e-9
_BOUNDARY_TOL = 1e-12


def _validate(value: Any, name: str) -> float:
    """Validate a single opinion component is in [0, 1]."""
    if isinstance(value, bool):
        raise TypeError(f"{name} must be a number, got bool")
    if not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number, got {type(value).__name__}")
    if math.isnan(value) or math.isinf(value):
        raise ValueError(f"{name} must be finite, got {value}")
    fval = float(value)
    # Clamp IEEE 754 boundary overshoots
    if -_BOUNDARY_TOL <= fval < 0.0:
        fval = 0.0
    elif 1.0 < fval <= 1.0 + _BOUNDARY_TOL:
        fval = 1.0
    if fval < 0.0 or fval > 1.0:
        raise ValueError(f"{name} must be in [0, 1], got {value}")
    return fval


@dataclass(frozen=True, eq=True)
class Opinion:
    """ω = (b, d, u, a) per Jøsang's Subjective Logic (2016).

    b + d + u = 1, all in [0, 1]. a is the base rate (prior).
    Projected probability: P(ω) = b + a·u.
    """

    belief: float
    disbelief: float
    uncertainty: float
    base_rate: float = 0.5

    def __post_init__(self) -> None:
        b = _validate(self.belief, "belief")
        d = _validate(self.disbelief, "disbelief")
        u = _validate(self.uncertainty, "uncertainty")
        a = _validate(self.base_rate, "base_rate")
        object.__setattr__(self, "belief", b)
        object.__setattr__(self, "disbelief", d)
        object.__setattr__(self, "uncertainty", u)
        object.__setattr__(self, "base_rate", a)
        total = b + d + u
        if abs(total - 1.0) > _ADDITIVITY_TOL:
            raise ValueError(
                f"b + d + u must equal 1, got {b} + {d} + {u} = {total}"
            )

    @property
    def projected_probability(self) -> float:
        """P(ω) = b + a·u — point estimate, reverts to base rate under ignorance."""
        return self.belief + self.base_rate * self.uncertainty

    def to_dict(self) -> dict:
        """JSON-serializable representation."""
        return {
            "belief": round(self.belief, 4),
            "disbelief": round(self.disbelief, 4),
            "uncertainty": round(self.uncertainty, 4),
            "base_rate": round(self.base_rate, 4),
            "projected_probability": round(self.projected_probability, 4),
        }

    @classmethod
    def vacuous(cls, base_rate: float = 0.5) -> Opinion:
        """Complete ignorance: ω_V = (0, 0, 1, a)."""
        return cls(0.0, 0.0, 1.0, base_rate)

    @classmethod
    def dogmatic_belief(cls, base_rate: float = 0.5) -> Opinion:
        """Certain compliance: (1, 0, 0, a)."""
        return cls(1.0, 0.0, 0.0, base_rate)

    @classmethod
    def dogmatic_disbelief(cls, base_rate: float = 0.5) -> Opinion:
        """Certain violation: (0, 1, 0, a)."""
        return cls(0.0, 1.0, 0.0, base_rate)


@dataclass(frozen=True, eq=False)
class ComplianceOpinion(Opinion):
    """ω = (l, v, u, a) — compliance-domain semantics.

    l = lawfulness (belief), v = violation (disbelief), u = uncertainty.
    Three-valued output: COMPLIANT / NON_COMPLIANT / INSUFFICIENT_EVIDENCE.
    """

    @property
    def lawfulness(self) -> float:
        """Evidence of compliance (alias for belief)."""
        return self.belief

    @property
    def violation(self) -> float:
        """Evidence of violation (alias for disbelief)."""
        return self.disbelief

    @classmethod
    def create(
        cls,
        lawfulness: float,
        violation: float,
        uncertainty: float,
        base_rate: float = 0.5,
    ) -> ComplianceOpinion:
        """Create from compliance-domain parameters (l, v, u, a)."""
        return cls(
            belief=lawfulness,
            disbelief=violation,
            uncertainty=uncertainty,
            base_rate=base_rate,
        )

    @classmethod
    def from_opinion(cls, op: Opinion) -> ComplianceOpinion:
        """Wrap an existing Opinion as a ComplianceOpinion."""
        return cls(op.belief, op.disbelief, op.uncertainty, op.base_rate)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Opinion):
            return (
                self.belief == other.belief
                and self.disbelief == other.disbelief
                and self.uncertainty == other.uncertainty
                and self.base_rate == other.base_rate
            )
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self.belief, self.disbelief, self.uncertainty, self.base_rate))

    def __repr__(self) -> str:
        return (
            f"ComplianceOpinion(l={self.lawfulness:.4f}, "
            f"v={self.violation:.4f}, u={self.uncertainty:.4f}, "
            f"a={self.base_rate:.4f})"
        )

    def to_dict(self) -> dict:
        """JSON-serializable with compliance-domain field names."""
        return {
            "lawfulness": round(self.lawfulness, 4),
            "violation": round(self.violation, 4),
            "uncertainty": round(self.uncertainty, 4),
            "base_rate": round(self.base_rate, 4),
            "projected_probability": round(self.projected_probability, 4),
            "compliance_level": self.compliance_level,
        }

    @property
    def compliance_level(self) -> str:
        """Three-valued + nuanced compliance status for UI and routing.

        Returns one of:
            HIGH_CONFIDENCE_COMPLIANT — auto-approve path
            LIKELY_COMPLIANT         — auto-approve with note
            NEEDS_REVIEW             — human-in-the-loop path
            INSUFFICIENT_EVIDENCE    — cannot determine, needs more info
            NON_COMPLIANT            — block / rewrite required
        """
        if self.lawfulness >= 0.7 and self.uncertainty <= 0.2:
            return "HIGH_CONFIDENCE_COMPLIANT"
        elif self.violation >= 0.5:
            return "NON_COMPLIANT"
        elif self.uncertainty >= 0.5:
            return "INSUFFICIENT_EVIDENCE"
        elif self.lawfulness >= 0.5:
            return "LIKELY_COMPLIANT"
        else:
            return "NEEDS_REVIEW"
