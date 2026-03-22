"""
Compliance Checker — registry-driven, severity-aware.

Aggregation strategy (when use_algebra=True, the default):

    WITHIN a regulation (severity-weighted weakest link):
        - CRITICAL + MAJOR rules determine the composite via weakest-link.
        - MINOR + ADVISORY rules are informational only.

    ACROSS regulations (jurisdictional meet J⊓):
        - The multiplicative conjunction from the algebra.
        - FINRA ⊓ SEC ⊓ MiFID II ⊓ ...: all must be satisfied.

Binary mode (when use_algebra=False):
    - Each rule: PASS (v < 0.3) or FAIL (v >= 0.3)
    - Within regulation: AND (all must pass)
    - Across regulations: AND (all must pass)
    - 2-level output: COMPLIANT or NON_COMPLIANT

Two-layer analysis (when use_gemini=True):
    Layer 1 (regex):  Fast pre-screen → flagged phrases + initial signals
    Layer 2 (Gemini): Deep analysis → authoritative ComplianceOpinion per rule
    Gemini overrides regex. If Gemini fails, regex opinion is kept.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Set

from .operators import ComplianceAudit, RuleResult, jurisdictional_meet
from .opinion import ComplianceOpinion
from .registry import ProspectContext, RuleDefinition, RegulationRegistry, default_registry

# Import core regulation modules to trigger auto-registration
from . import rules_finra  # noqa: F401
from . import rules_sec    # noqa: F401

logger = logging.getLogger(__name__)

# Severities that count toward the composite (gatekeeping)
GATEKEEPING_SEVERITIES = {"critical", "major"}

# Binary mode threshold: violation >= this means FAIL
BINARY_VIOLATION_THRESHOLD = 0.3


def _weakest_link(opinions: List[ComplianceOpinion]) -> ComplianceOpinion:
    """Within-regulation: weakest link of gatekeeping rules only."""
    if not opinions:
        return ComplianceOpinion.create(0.0, 0.0, 1.0, 0.5)
    if len(opinions) == 1:
        return opinions[0]
    return min(opinions, key=lambda o: (o.lawfulness, -o.violation))


def _binary_result(rule_results: List[RuleResult], severity_map: Dict[str, str]) -> ComplianceOpinion:
    """Binary mode: PASS/FAIL per rule with AND logic.

    Returns dogmatic belief (1,0,0) if all pass, dogmatic disbelief (0,1,0) if any fail.
    This is what compliance looks like WITHOUT the algebra — a blunt instrument.
    """
    for rr in rule_results:
        severity = severity_map.get(rr.rule_id, "major")
        if severity in GATEKEEPING_SEVERITIES:
            if rr.opinion.violation >= BINARY_VIOLATION_THRESHOLD:
                return ComplianceOpinion.create(0.0, 1.0, 0.0, 0.5)
    return ComplianceOpinion.create(1.0, 0.0, 0.0, 0.5)


def check_compliance(
    message: str,
    prospect_name: str = "",
    prospect_role: str = "",
    prospect_company: str = "",
    prospect_location: str = "",
    registry: Optional[RegulationRegistry] = None,
    use_gemini: bool = False,
    use_algebra: bool = True,
    regulation_ids: Optional[List[str]] = None,
) -> ComplianceAudit:
    """Run selected regulations and compute composite opinions.

    Args:
        message:           The outreach message to check.
        prospect_name:     Prospect's name (for personalization checks).
        prospect_role:     Prospect's role/title.
        prospect_company:  Prospect's company.
        prospect_location: Prospect's location.
        registry:          Regulation registry (defaults to global).
        use_gemini:        If True, Gemini deep analysis overrides regex.
        use_algebra:       If True, use compliance algebra (SL opinions + J⊓).
                           If False, binary pass/fail with AND logic.
        regulation_ids:    List of regulation IDs to check (e.g. ["FINRA", "SEC"]).
                           None means check all registered regulations.

    Returns:
        ComplianceAudit with full per-rule trail and composite opinions.
    """
    reg = registry or default_registry
    ctx = ProspectContext(
        prospect_name=prospect_name,
        prospect_role=prospect_role,
        prospect_company=prospect_company,
        prospect_location=prospect_location,
    )

    audit = ComplianceAudit(
        message_text=message,
        prospect_name=prospect_name,
    )

    # Filter regulations by selected IDs
    selected_ids: Optional[Set[str]] = set(regulation_ids) if regulation_ids else None
    regulations = [
        r for r in reg.get_all_regulations()
        if selected_ids is None or r.regulation_id in selected_ids
    ]

    if not regulations:
        logger.warning("No regulations selected or registered.")
        audit.overall = ComplianceOpinion.create(0.0, 0.0, 1.0, 0.5)
        return audit

    # ── Layer 1: Regex pre-screen (always runs) ──────────────────
    regex_results: List[RuleResult] = []
    for regulation in regulations:
        for rule_def in regulation.enabled_rules:
            result = rule_def.checker(message, ctx)
            regex_results.append(result)

    # ── Layer 2: Gemini deep analysis (overrides regex) ──────────
    if use_gemini:
        try:
            from .gemini_checker import gemini_check_all

            gemini_results = gemini_check_all(
                message=message,
                regex_results=regex_results,
                ctx=ctx,
                registry=reg,
            )

            if gemini_results:
                logger.info(
                    "Gemini analyzed %d/%d rules. Overriding regex opinions.",
                    len(gemini_results), len(regex_results),
                )
                final_results = []
                for rr in regex_results:
                    if rr.rule_id in gemini_results:
                        final_results.append(gemini_results[rr.rule_id])
                    else:
                        logger.debug(
                            "Keeping regex opinion for %s (Gemini did not cover)",
                            rr.rule_id,
                        )
                        final_results.append(rr)
            else:
                logger.warning("Gemini returned no results. Using regex opinions.")
                final_results = regex_results

        except Exception as e:
            logger.error("Gemini layer failed: %s. Falling back to regex.", e)
            final_results = regex_results
    else:
        final_results = regex_results

    # ── Store results in audit ───────────────────────────────────
    audit.rule_results = final_results

    # Build severity map from selected regulations
    severity_map: Dict[str, str] = {}
    for regulation in regulations:
        for rule_def in regulation.enabled_rules:
            severity_map[rule_def.rule_id] = rule_def.severity

    # Group results by regulation
    results_by_reg: Dict[str, List[RuleResult]] = {}
    for rr in final_results:
        results_by_reg.setdefault(rr.regulation, []).append(rr)

    # ── Aggregate: Algebra mode vs Binary mode ───────────────────
    regulation_composites: Dict[str, ComplianceOpinion] = {}

    if use_algebra:
        # === COMPLIANCE ALGEBRA MODE ===
        # Within regulation: weakest-link of gatekeeping rules
        # Across regulations: jurisdictional meet J⊓
        for reg_id, results in results_by_reg.items():
            gatekeeping_opinions = []
            for rr in results:
                severity = severity_map.get(rr.rule_id, "major")
                if severity in GATEKEEPING_SEVERITIES:
                    gatekeeping_opinions.append(rr.opinion)

            if gatekeeping_opinions:
                composite = _weakest_link(gatekeeping_opinions)
                regulation_composites[reg_id] = composite

        # ACROSS regulations: jurisdictional meet J⊓
        all_composites = list(regulation_composites.values())
        if len(all_composites) >= 2:
            audit.overall = jurisdictional_meet(*all_composites)
        elif len(all_composites) == 1:
            audit.overall = all_composites[0]
        else:
            audit.overall = ComplianceOpinion.create(0.0, 0.0, 1.0, 0.5)

    else:
        # === BINARY MODE ===
        # Within regulation: AND (any gatekeeping fail = regulation fail)
        # Across regulations: AND (any regulation fail = overall fail)
        for reg_id, results in results_by_reg.items():
            regulation_composites[reg_id] = _binary_result(results, severity_map)

        all_composites = list(regulation_composites.values())
        if all_composites:
            any_fail = any(c.violation > 0.5 for c in all_composites)
            if any_fail:
                audit.overall = ComplianceOpinion.create(0.0, 1.0, 0.0, 0.5)
            else:
                audit.overall = ComplianceOpinion.create(1.0, 0.0, 0.0, 0.5)
        else:
            audit.overall = ComplianceOpinion.create(0.0, 0.0, 1.0, 0.5)

    # Set named composites (for backward compatibility)
    audit.finra_composite = regulation_composites.get(
        "FINRA", ComplianceOpinion.create(1.0, 0.0, 0.0, 1.0)
    )
    audit.sec_composite = regulation_composites.get(
        "SEC", ComplianceOpinion.create(1.0, 0.0, 0.0, 1.0)
    )

    return audit


def check_compliance_quick(
    message: str,
    use_gemini: bool = False,
    use_algebra: bool = True,
    regulation_ids: Optional[List[str]] = None,
) -> dict:
    """Quick check — just the routing decision, no full audit."""
    audit = check_compliance(
        message,
        use_gemini=use_gemini,
        use_algebra=use_algebra,
        regulation_ids=regulation_ids,
    )
    return {
        "compliance_level": audit.overall.compliance_level if audit.overall else "NEEDS_REVIEW",
        "projected_probability": audit.overall.projected_probability if audit.overall else 0.0,
        "needs_human_review": audit.needs_human_review,
        "num_flagged_rules": len(audit.flagged_rules),
        "registered_regulations": default_registry.regulation_ids,
        "selected_regulations": regulation_ids or default_registry.regulation_ids,
        "mode": "algebra" if use_algebra else "binary",
    }
