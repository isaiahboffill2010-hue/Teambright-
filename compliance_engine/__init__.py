"""Compliance Engine — Subjective Logic compliance algebra for FINRA/SEC.

Ported from jsonld-ex (Syed, Silaghi, Abujar, Alssadi 2026).
Zero external dependencies (core). Gemini integration optional.
Pluggable regulation framework.

Features:
    - Subjective Logic opinions ω = (l, v, u, a) instead of binary pass/fail
    - Jurisdictional meet J⊓ across FINRA + SEC
    - Two-layer analysis: regex pre-screen + Gemini deep analysis
    - Pluggable regulation registry (add MiFID II, state regs, etc.)
    - Self-correction loop (fail → fix → re-check)
    - Temporal decay (assessments grow stale per §8 of the algebra)
    - FINRA API integration (OAuth2 via FIP)
"""

from .opinion import Opinion, ComplianceOpinion
from .operators import jurisdictional_meet, RuleResult, ComplianceAudit
from .registry import (
    Regulation, RuleDefinition, ProspectContext,
    RegulationRegistry, default_registry,
)
from .checker import check_compliance, check_compliance_quick
from .correction import (
    self_correct, CorrectionResult, CorrectionStep,
    decay_opinion, assess_staleness,
)
from .gemini_checker import gemini_check_regulation, gemini_check_all

__all__ = [
    "Opinion", "ComplianceOpinion",
    "jurisdictional_meet", "RuleResult", "ComplianceAudit",
    "Regulation", "RuleDefinition", "ProspectContext",
    "RegulationRegistry", "default_registry",
    "check_compliance", "check_compliance_quick",
    "self_correct", "CorrectionResult", "CorrectionStep",
    "decay_opinion", "assess_staleness",
    "gemini_check_regulation", "gemini_check_all",
]
