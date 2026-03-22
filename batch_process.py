"""
Batch Processing — pre-compute compliance audits for all prospects.

COMPLIANCE ALGEBRA SHOWCASE:
    Every prospect's result includes the full algebra pipeline across
    MULTIPLE regulation combinations, so the dashboard can toggle
    regulations on/off and instantly show the impact on J⊓.

    Pre-computed regulation sets per prospect:
        - Individual: each of 7 regulations alone
        - Combos: FINRA, FINRA+SEC, FINRA+SEC+CAN-SPAM, All 7
        - Each set includes: per-rule opinions, weakest-link, J⊓ steps,
          binary comparison, temporal decay

Two phases:
    Phase 1: Template-based messages + regex compliance (no API cost, instant)
    Phase 2: Gemini-generated messages + Gemini deep analysis (API cost, slow)
             Optimized: 4 API calls per prospect (3 regulation checks + 1 message)
             Gemini only on FINRA, SEC, CAN-SPAM; regex for the other 4.
             Also produces a self-corrected (compliant) version per prospect.

Usage:
    python batch_process.py --template-only     # Phase 1 only
    python batch_process.py --limit 5           # Test with 5 (writes to test files)
    python batch_process.py                     # Full Phase 1 + Phase 2
    python batch_process.py --resume            # Resume Phase 2
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# PATHS
# ═══════════════════════════════════════════════════════════════════

PROJECT_ROOT = Path(__file__).parent
SCORED_JSON = PROJECT_ROOT.parent / "Pulse_Miami_Hackathon" / "datasets" / "scored.json"
OUTPUT_DIR = PROJECT_ROOT / "sample_output"
GEMINI_CACHE_DIR = OUTPUT_DIR / "gemini_cache"

GATEKEEPING_SEVERITIES = {"critical", "major"}
BINARY_VIOLATION_THRESHOLD = 0.3

# ═══════════════════════════════════════════════════════════════════
# REGULATION COMBOS TO PRE-COMPUTE
# ═══════════════════════════════════════════════════════════════════

ALL_REGULATION_IDS = ["FINRA", "SEC", "MiFID_II", "NY_State", "NASAA", "CAN_SPAM_TCPA", "SOX"]

REGULATION_COMBOS = {
    "FINRA_only": ["FINRA"],
    "SEC_only": ["SEC"],
    "CAN_SPAM_TCPA_only": ["CAN_SPAM_TCPA"],
    "MiFID_II_only": ["MiFID_II"],
    "NY_State_only": ["NY_State"],
    "NASAA_only": ["NASAA"],
    "SOX_only": ["SOX"],
    "FINRA_SEC": ["FINRA", "SEC"],
    "FINRA_SEC_CANSPAM": ["FINRA", "SEC", "CAN_SPAM_TCPA"],
    "US_full": ["FINRA", "SEC", "CAN_SPAM_TCPA", "NY_State", "NASAA", "SOX"],
    "all_7": ALL_REGULATION_IDS,
}

PRIMARY_COMBO = "FINRA_SEC_CANSPAM"

# ─── Phase 2 optimization: which combos get Gemini vs regex ─────
# Gemini is called once per regulation for: FINRA, SEC, CAN_SPAM_TCPA
# These 5 combos use Gemini opinions (assembled from cached per-reg results):
GEMINI_REGULATIONS = {"FINRA", "SEC", "CAN_SPAM_TCPA"}
GEMINI_COMBOS = {"FINRA_only", "SEC_only", "CAN_SPAM_TCPA_only", "FINRA_SEC", "FINRA_SEC_CANSPAM"}
# These 6 combos use regex opinions only:
REGEX_ONLY_COMBOS = {"MiFID_II_only", "NY_State_only", "NASAA_only", "SOX_only", "US_full", "all_7"}

# ═══════════════════════════════════════════════════════════════════
# ADVISOR FIRM DETAILS
# ═══════════════════════════════════════════════════════════════════

ADVISOR_FIRM = "Fortis Wealth Management"
ADVISOR_NAME = "The Fortis Advisory Team"
ADVISOR_ADDRESS = "250 Park Avenue, Suite 1200, New York, NY 10177"
ADVISOR_UNSUBSCRIBE = "If you prefer not to receive future communications, reply STOP or click here to unsubscribe."


# ═══════════════════════════════════════════════════════════════════
# ALGEBRA SHOWCASE
# ═══════════════════════════════════════════════════════════════════

def compute_algebra_showcase(audit, registry) -> Dict[str, Any]:
    from compliance_engine.opinion import ComplianceOpinion
    from compliance_engine.operators import jurisdictional_meet
    from compliance_engine.correction import decay_opinion, assess_staleness

    severity_map = {}
    for regulation in registry.get_all_regulations():
        for rule_def in regulation.enabled_rules:
            severity_map[rule_def.rule_id] = rule_def.severity

    per_rule = []
    for rr in audit.rule_results:
        per_rule.append({
            "rule_id": rr.rule_id, "rule_name": rr.rule_name,
            "regulation": rr.regulation,
            "severity": severity_map.get(rr.rule_id, "unknown"),
            "opinion": rr.opinion.to_dict(),
            "explanation": rr.explanation,
            "flagged_phrases": rr.flagged_phrases,
            "suggested_fixes": rr.suggested_fixes,
            "is_gatekeeping": severity_map.get(rr.rule_id, "major") in GATEKEEPING_SEVERITIES,
        })

    results_by_reg: Dict[str, list] = {}
    for rr in audit.rule_results:
        results_by_reg.setdefault(rr.regulation, []).append(rr)

    regulation_details = {}
    regulation_composites_for_meet: Dict[str, ComplianceOpinion] = {}

    for reg_id, results in results_by_reg.items():
        gatekeeping_rules = [
            rr for rr in results
            if severity_map.get(rr.rule_id, "major") in GATEKEEPING_SEVERITIES
        ]
        weakest = None
        if gatekeeping_rules:
            weakest = min(gatekeeping_rules, key=lambda r: (r.opinion.lawfulness, -r.opinion.violation))
            composite = weakest.opinion
        else:
            composite = ComplianceOpinion.create(0.0, 0.0, 1.0, 0.5)
        regulation_composites_for_meet[reg_id] = composite

        binary_pass = all(rr.opinion.violation < BINARY_VIOLATION_THRESHOLD for rr in gatekeeping_rules) if gatekeeping_rules else True
        binary_failures = [rr.rule_id for rr in gatekeeping_rules if rr.opinion.violation >= BINARY_VIOLATION_THRESHOLD]

        regulation_details[reg_id] = {
            "regulation_id": reg_id, "total_rules": len(results),
            "gatekeeping_rules": len(gatekeeping_rules),
            "composite_opinion": composite.to_dict(),
            "weakest_link": {
                "rule_id": weakest.rule_id if weakest else None,
                "rule_name": weakest.rule_name if weakest else None,
                "opinion": weakest.opinion.to_dict() if weakest else None,
                "explanation": weakest.explanation if weakest else None,
            },
            "binary_result": "PASS" if binary_pass else "FAIL",
            "binary_failures": binary_failures,
        }

    meet_steps = []
    reg_ids = list(regulation_composites_for_meet.keys())
    composites = list(regulation_composites_for_meet.values())

    if len(composites) >= 2:
        running = composites[0]
        meet_steps.append({"step": 0, "operation": f"Start with {reg_ids[0]}", "input_a": None, "input_b": None, "result": running.to_dict()})
        for i in range(1, len(composites)):
            prev = running
            running = jurisdictional_meet(running, composites[i])
            meet_steps.append({
                "step": i,
                "operation": f"J⊓({reg_ids[i-1] if i == 1 else 'running'}, {reg_ids[i]})",
                "input_a": prev.to_dict(), "input_b": composites[i].to_dict(),
                "result": running.to_dict(),
                "properties": {
                    "monotonic_restriction": running.lawfulness <= min(prev.lawfulness, composites[i].lawfulness),
                    "monotonic_violation": running.violation >= max(prev.violation, composites[i].violation),
                },
            })
        algebra_overall = running
    elif len(composites) == 1:
        algebra_overall = composites[0]
        meet_steps.append({"step": 0, "operation": f"Single regulation: {reg_ids[0]}", "result": algebra_overall.to_dict()})
    else:
        algebra_overall = ComplianceOpinion.create(0.0, 0.0, 1.0, 0.5)

    binary_any_fail = any(rd["binary_result"] == "FAIL" for rd in regulation_details.values())
    binary_overall = {
        "result": "NON_COMPLIANT" if binary_any_fail else "COMPLIANT",
        "opinion": {"lawfulness": 0.0 if binary_any_fail else 1.0, "violation": 1.0 if binary_any_fail else 0.0, "uncertainty": 0.0},
        "failing_regulations": [r for r, rd in regulation_details.items() if rd["binary_result"] == "FAIL"],
    }

    now = time.time()
    decay_snapshots = []
    for hours, label in [(0, "Now"), (24, "1 day"), (168, "1 week"), (720, "30 days"), (2160, "90 days")]:
        decayed = decay_opinion(algebra_overall, elapsed_hours=hours, half_life_hours=168.0)
        staleness = assess_staleness(now - hours * 3600, now, half_life_hours=168.0)
        decay_snapshots.append({"label": label, "hours": hours, "opinion": decayed.to_dict(), "freshness": staleness["freshness"], "decay_factor": staleness["decay_factor"]})

    alg_level = algebra_overall.compliance_level
    bin_level = binary_overall["result"]
    key_diffs = []
    if alg_level in ("LIKELY_COMPLIANT", "NEEDS_REVIEW") and bin_level == "COMPLIANT":
        key_diffs.append("Binary says COMPLIANT but algebra detects residual uncertainty.")
    elif alg_level == "LIKELY_COMPLIANT" and bin_level == "NON_COMPLIANT":
        key_diffs.append("Binary rejects but algebra recognizes LIKELY COMPLIANT with uncertainty.")
    elif alg_level == "HIGH_CONFIDENCE_COMPLIANT" and bin_level == "COMPLIANT":
        key_diffs.append("Both agree compliant. Algebra adds confidence + uncertainty quantification.")
    elif alg_level == "NON_COMPLIANT" and bin_level == "NON_COMPLIANT":
        key_diffs.append("Both agree non-compliant. Algebra shows HOW (l/v/u); binary just says FAIL.")
    elif alg_level == "INSUFFICIENT_EVIDENCE":
        key_diffs.append("Algebra: INSUFFICIENT EVIDENCE. Binary forces hard PASS or FAIL.")
    if algebra_overall.uncertainty > 0.3:
        key_diffs.append(f"High uncertainty (u={algebra_overall.uncertainty:.2f}) — algebra preserves; binary discards.")

    return {
        "per_rule_opinions": per_rule,
        "regulation_details": regulation_details,
        "jurisdictional_meet_steps": meet_steps,
        "algebra_overall": algebra_overall.to_dict(),
        "binary_overall": binary_overall,
        "temporal_decay": decay_snapshots,
        "comparison": {"algebra": {"overall": algebra_overall.to_dict(), "compliance_level": alg_level}, "binary": {"overall": binary_overall["opinion"], "compliance_level": bin_level}, "key_differences": key_diffs},
    }


# ═══════════════════════════════════════════════════════════════════
# MESSAGE GENERATORS
# ═══════════════════════════════════════════════════════════════════

def _extract_company(role: str) -> str:
    if " at " in role: return role.split(" at ", 1)[1].strip()
    if " - " in role: return role.split(" - ")[-1].strip()
    return ""

def _extract_title(role: str) -> str:
    if " at " in role: return role.split(" at ", 1)[0].strip()
    if " - " in role: return role.split(" - ", 1)[0].strip()
    return role

def _get_icp_hook(matched_icp: str) -> str:
    hooks = {
        "high_income_professional": "a tax-advantaged strategy designed for high-income professionals in your industry",
        "business_owners_exits": "an optimized approach to tax efficiency around business transitions and exit planning",
        "business_owners_succession": "creative tax strategies specifically designed for business owners navigating succession planning",
        "business_owner": "a specialized tax strategy tailored for business owners managing both personal and business wealth",
        "business_owners": "an approach to tax optimization for business owners in your sector",
        "tech_transitions": "a tax-efficient strategy for technology professionals managing equity compensation and transitions",
        "pre_retiree_wealth_transitioner": "an optimized wealth transition strategy designed for professionals at your career stage",
        "pre_retirees_wealth_transitioners": "a creative approach to tax-efficient wealth transition planning",
    }
    return hooks.get(matched_icp, "a creative tax-advantaged strategy relevant to professionals in your position")

def generate_template_message(prospect: Dict[str, Any]) -> str:
    role = prospect["current_role"]
    company = _extract_company(role)
    title = _extract_title(role)
    icp = prospect.get("matched_icp", "")
    hook = f"Given your role as {title} at {company}" if company else f"Given your experience as {title}"
    value_prop = _get_icp_hook(icp)
    body = (f"{hook}, I wanted to share {value_prop}. "
            f"This is designed as an ancillary opportunity to optimize your overall "
            f"tax efficiency without replacing your current advisory team. "
            f"Would you be open to a brief conversation about how this could complement your existing planning?")
    footer = (f"\n\n{ADVISOR_NAME} | {ADVISOR_FIRM}\n{ADVISOR_ADDRESS}\n{ADVISOR_UNSUBSCRIBE}")
    return body + footer


GEMINI_OUTREACH_PROMPT = f"""You are a financial advisor's outreach assistant. Generate a personalized,
compliant cold outreach email following the 3-sentence structure:
1. THE HOOK: Reference their specific firm, role, or industry.
2. THE VALUE: Pitch a creative tax strategy or optimized approach to tax efficiency.
3. THE GUARDRAIL: Explicitly state you complement—not replace—their existing advisory team.

RULES: 3-4 sentences MAX body. NO promissory/pressure language. DO use "complement", "ancillary".
ALWAYS include this footer:

{ADVISOR_NAME} | {ADVISOR_FIRM}
{ADVISOR_ADDRESS}
{ADVISOR_UNSUBSCRIBE}

Return ONLY the message text with footer."""

def generate_gemini_message(prospect: Dict[str, Any]) -> Optional[str]:
    name, role = prospect["name"], prospect["current_role"]
    location, icp = prospect.get("location", ""), prospect.get("matched_icp", "")
    match_reasons, why_now = prospect.get("match_reasons", []), prospect.get("why_now_reasons", [])
    outreach_angle = prospect.get("recommended_outreach_angle", "")
    user_prompt = f"""Generate a personalized outreach email:
Name: {name} | Role: {role} | Location: {location} | Profile: {icp}
Fit: {json.dumps(match_reasons[:3])} | Why now: {json.dumps(why_now[:2])}
Angle: {outreach_angle[:200]}
Return ONLY the message with footer."""
    try:
        os.environ.pop("GOOGLE_API_KEY", None)
        from google import genai
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        response = client.models.generate_content(model="gemini-2.5-flash", contents=user_prompt, config={"system_instruction": GEMINI_OUTREACH_PROMPT, "temperature": 0.7})
        return response.text.strip().strip('"')
    except Exception as e:
        print(f"  [ERROR] Gemini message gen failed: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════
# MULTI-COMBO PROCESSING
# ═══════════════════════════════════════════════════════════════════

def compute_all_combos(message, prospect, check_fn, registry, use_gemini=False):
    """Original: calls check_compliance per combo. Used by Phase 1 (regex only)."""
    name, role = prospect["name"], prospect["current_role"]
    company, location = _extract_company(role), prospect.get("location", "")
    combo_results = {}
    for combo_name, reg_ids in REGULATION_COMBOS.items():
        available = set(registry.regulation_ids)
        if not all(r in available for r in reg_ids): continue
        audit = check_fn(message=message, prospect_name=name, prospect_role=role,
                         prospect_company=company, prospect_location=location,
                         use_gemini=use_gemini, use_algebra=True, regulation_ids=reg_ids)
        showcase = compute_algebra_showcase(audit, registry)
        combo_results[combo_name] = {"regulation_ids": reg_ids,
            "compliance_level": showcase["comparison"]["algebra"]["compliance_level"],
            "binary_level": showcase["comparison"]["binary"]["compliance_level"],
            "algebra_showcase": showcase}
    return combo_results


def compute_all_combos_optimized(
    message: str,
    prospect: Dict[str, Any],
    regex_results_all: List,
    gemini_opinions: Dict[str, Dict],
    registry,
) -> Dict[str, Any]:
    """Optimized Phase 2: assemble 11 combos from cached per-regulation results.

    Args:
        message:           The outreach message.
        prospect:          Prospect dict.
        regex_results_all: List of RuleResult from regex on ALL 7 regulations.
        gemini_opinions:   Dict of regulation_id -> Dict[rule_id -> RuleResult]
                           from gemini_check_regulation() for FINRA, SEC, CAN_SPAM_TCPA.
        registry:          The RegulationRegistry.

    Returns:
        Dict of combo_name -> combo result (same format as compute_all_combos).
    """
    from compliance_engine.operators import ComplianceAudit

    # Build lookup: rule_id -> regex RuleResult
    regex_by_rule = {rr.rule_id: rr for rr in regex_results_all}

    # Build lookup: rule_id -> regulation_id
    rule_to_reg = {}
    for regulation in registry.get_all_regulations():
        for rule_def in regulation.enabled_rules:
            rule_to_reg[rule_def.rule_id] = regulation.regulation_id

    # For each combo, assemble the final rule results
    combo_results = {}
    available = set(registry.regulation_ids)

    for combo_name, reg_ids in REGULATION_COMBOS.items():
        if not all(r in available for r in reg_ids):
            continue

        reg_id_set = set(reg_ids)
        use_gemini_for_combo = combo_name in GEMINI_COMBOS

        # Assemble rule results for this combo
        final_results = []
        for rr in regex_results_all:
            rule_reg = rule_to_reg.get(rr.rule_id, rr.regulation)
            # Only include rules from regulations in this combo
            if rule_reg not in reg_id_set:
                continue

            if use_gemini_for_combo and rule_reg in GEMINI_REGULATIONS:
                # Use Gemini opinion if available, else fallback to regex
                gemini_reg = gemini_opinions.get(rule_reg, {})
                gemini_rr = gemini_reg.get(rr.rule_id)
                final_results.append(gemini_rr if gemini_rr else rr)
            else:
                final_results.append(rr)

        # Build a synthetic audit
        name = prospect["name"]
        audit = ComplianceAudit(message_text=message, prospect_name=name)
        audit.rule_results = final_results

        # Compute overall from the assembled results (algebra mode)
        from compliance_engine.opinion import ComplianceOpinion
        from compliance_engine.operators import jurisdictional_meet

        severity_map = {}
        for regulation in registry.get_all_regulations():
            for rule_def in regulation.enabled_rules:
                severity_map[rule_def.rule_id] = rule_def.severity

        results_by_reg: Dict[str, list] = {}
        for rr in final_results:
            results_by_reg.setdefault(rr.regulation, []).append(rr)

        regulation_composites = {}
        for rid, results in results_by_reg.items():
            gatekeeping = [
                rr for rr in results
                if severity_map.get(rr.rule_id, "major") in GATEKEEPING_SEVERITIES
            ]
            if gatekeeping:
                weakest = min(gatekeeping, key=lambda r: (r.opinion.lawfulness, -r.opinion.violation))
                regulation_composites[rid] = weakest.opinion
            else:
                regulation_composites[rid] = ComplianceOpinion.create(0.0, 0.0, 1.0, 0.5)

        all_composites = list(regulation_composites.values())
        if len(all_composites) >= 2:
            audit.overall = jurisdictional_meet(*all_composites)
        elif len(all_composites) == 1:
            audit.overall = all_composites[0]
        else:
            audit.overall = ComplianceOpinion.create(0.0, 0.0, 1.0, 0.5)

        showcase = compute_algebra_showcase(audit, registry)
        combo_results[combo_name] = {
            "regulation_ids": reg_ids,
            "compliance_level": showcase["comparison"]["algebra"]["compliance_level"],
            "binary_level": showcase["comparison"]["binary"]["compliance_level"],
            "uses_gemini": use_gemini_for_combo,
            "algebra_showcase": showcase,
        }

    return combo_results


# ═══════════════════════════════════════════════════════════════════
# PROSPECT DATA HELPERS
# ═══════════════════════════════════════════════════════════════════

def load_prospects(path): return json.loads(Path(path).read_text(encoding="utf-8"))

def build_prospect_data(p):
    return {"name": p["name"], "current_role": p["current_role"], "location": p.get("location", ""),
        "linkedin_url": p.get("linkedin_url", ""),
        "icp_match_score": p.get("icp_match_score", 0), "urgency_score": p.get("urgency_score", 0),
        "composite_score": round(p.get("icp_match_score", 0)*0.6 + p.get("urgency_score", 0)*0.4, 1),
        "matched_icp": p.get("matched_icp", ""),
        "recommended_outreach_angle": p.get("recommended_outreach_angle", ""),
        "match_reasons": p.get("match_reasons", []), "why_now_reasons": p.get("why_now_reasons", []),
        "concerns": p.get("concerns", [])}


# ═══════════════════════════════════════════════════════════════════
# PHASE 1: Template + Regex (unchanged)
# ═══════════════════════════════════════════════════════════════════

def process_prospect_template(prospect, check_fn, correct_fn, registry):
    name, role = prospect["name"], prospect["current_role"]
    message = generate_template_message(prospect)
    correction = correct_fn(message=message,
        check_fn=lambda **kw: check_fn(**kw, regulation_ids=REGULATION_COMBOS[PRIMARY_COMBO]),
        prospect_name=name, prospect_role=role, use_gemini=False)
    regulation_combos = compute_all_combos(message, prospect, check_fn, registry, use_gemini=False)
    primary = regulation_combos.get(PRIMARY_COMBO, {})
    return {"prospect": build_prospect_data(prospect), "template_message": message,
        "correction": correction.to_dict(), "regulation_combos": regulation_combos,
        "compliance_level": primary.get("compliance_level", "UNKNOWN"),
        "binary_level": primary.get("binary_level", "UNKNOWN"),
        "needs_review": primary.get("compliance_level", "") not in ("HIGH_CONFIDENCE_COMPLIANT", "LIKELY_COMPLIANT"),
        "method": "template_regex", "timestamp": time.time()}


# ═══════════════════════════════════════════════════════════════════
# PHASE 2: Gemini Deep Analysis (OPTIMIZED — 4 API calls/prospect)
# ═══════════════════════════════════════════════════════════════════

def process_prospect_gemini(prospect, template_result, check_fn, correct_fn, registry):
    """Optimized Phase 2 processing.

    API calls per prospect:
        1. generate_gemini_message()          → 1 call (outreach draft)
        2. gemini_check_regulation("FINRA")   → 1 call
        3. gemini_check_regulation("SEC")     → 1 call
        4. gemini_check_regulation("CAN_SPAM_TCPA") → 1 call
        TOTAL: 4 API calls

    Then locally (zero API cost):
        - Assemble 11 combos from cached per-regulation opinions
        - Self-correct the message (static replacements)
        - Re-check corrected message (regex only) across all combos
    """
    from compliance_engine.gemini_checker import gemini_check_regulation
    from compliance_engine.registry import ProspectContext

    name, role = prospect["name"], prospect["current_role"]
    company = _extract_company(role)
    location = prospect.get("location", "")

    ctx = ProspectContext(
        prospect_name=name,
        prospect_role=role,
        prospect_company=company,
        prospect_location=location,
    )

    # ── Step 1: Generate Gemini outreach message (1 API call) ────
    gemini_message = generate_gemini_message(prospect)
    if not gemini_message:
        gemini_message = template_result["template_message"]

    # ── Step 2: Regex pre-screen on ALL 7 regulations (0 API calls) ──
    regex_results_all = []
    for regulation in registry.get_all_regulations():
        for rule_def in regulation.enabled_rules:
            result = rule_def.checker(gemini_message, ctx)
            regex_results_all.append(result)

    # ── Step 3: Gemini deep analysis — 3 regulations only (3 API calls) ──
    gemini_opinions: Dict[str, Dict] = {}
    for reg_id in GEMINI_REGULATIONS:
        try:
            gemini_rr = gemini_check_regulation(
                regulation_id=reg_id,
                message=gemini_message,
                regex_results=regex_results_all,
                ctx=ctx,
                registry=registry,
            )
            if gemini_rr:
                gemini_opinions[reg_id] = gemini_rr
                logger.info("  Gemini OK for %s (%d rules)", reg_id, len(gemini_rr))
            else:
                logger.warning("  Gemini empty for %s — using regex", reg_id)
        except Exception as e:
            logger.error("  Gemini failed for %s: %s — using regex", reg_id, e)

    # ── Step 4: Assemble all 11 combos (0 API calls) ────────────
    regulation_combos = compute_all_combos_optimized(
        message=gemini_message,
        prospect=prospect,
        regex_results_all=regex_results_all,
        gemini_opinions=gemini_opinions,
        registry=registry,
    )

    primary = regulation_combos.get(PRIMARY_COMBO, {})

    # ── Step 5: Self-correct the message (static, 0 API calls) ──
    correction = correct_fn(
        message=gemini_message,
        check_fn=lambda **kw: check_fn(**kw, regulation_ids=REGULATION_COMBOS[PRIMARY_COMBO]),
        prospect_name=name, prospect_role=role, use_gemini=False,
    )

    # ── Step 6: Re-check corrected message across all combos (regex, 0 API calls) ──
    corrected_message = correction.corrected_message or gemini_message
    corrected_combos = None

    if corrected_message != gemini_message:
        # Run regex on corrected message for all 7 regulations
        corrected_regex_all = []
        for regulation in registry.get_all_regulations():
            for rule_def in regulation.enabled_rules:
                result = rule_def.checker(corrected_message, ctx)
                corrected_regex_all.append(result)

        # Assemble all combos — reuse cached Gemini opinions + fresh regex
        corrected_combos = compute_all_combos_optimized(
            message=corrected_message,
            prospect=prospect,
            regex_results_all=corrected_regex_all,
            gemini_opinions=gemini_opinions,  # Reuse cached Gemini opinions for corrected msg
            registry=registry,
        )

    corrected_primary = corrected_combos.get(PRIMARY_COMBO, {}) if corrected_combos else primary

    return {
        "prospect": build_prospect_data(prospect),
        "gemini_message": gemini_message,
        "template_message": template_result["template_message"],
        "correction": correction.to_dict(),
        "regulation_combos": regulation_combos,
        "corrected_regulation_combos": corrected_combos,
        "compliance_level": primary.get("compliance_level", "UNKNOWN"),
        "corrected_compliance_level": corrected_primary.get("compliance_level", "UNKNOWN"),
        "binary_level": primary.get("binary_level", "UNKNOWN"),
        "needs_review": primary.get("compliance_level", "") not in ("HIGH_CONFIDENCE_COMPLIANT", "LIKELY_COMPLIANT"),
        "corrected_needs_review": corrected_primary.get("compliance_level", "") not in ("HIGH_CONFIDENCE_COMPLIANT", "LIKELY_COMPLIANT"),
        "gemini_regulations_analyzed": list(gemini_opinions.keys()),
        "gemini_api_calls": 1 + len(gemini_opinions),  # 1 for message + N for regulations
        "method": "gemini_deep_optimized",
        "timestamp": time.time(),
    }


# ═══════════════════════════════════════════════════════════════════
# PHASE RUNNERS
# ═══════════════════════════════════════════════════════════════════

def run_phase1(prospects):
    from compliance_engine import plugins  # noqa: F401
    from compliance_engine import check_compliance, default_registry
    from compliance_engine.correction import self_correct

    print(f"\n{'='*60}")
    print(f"PHASE 1: Template + Regex | {len(prospects)} prospects | {len(REGULATION_COMBOS)} combos each")
    print(f"{'='*60}\n")

    results = []
    start = time.time()
    for i, prospect in enumerate(prospects):
        result = process_prospect_template(prospect, check_compliance, self_correct, default_registry)
        results.append(result)
        if (i + 1) % 100 == 0 or i == 0:
            elapsed = time.time() - start
            combos = result["regulation_combos"]
            finra = combos.get("FINRA_only", {}).get("compliance_level", "?")[:12]
            fsec = combos.get("FINRA_SEC", {}).get("compliance_level", "?")[:12]
            all7 = combos.get("all_7", {}).get("compliance_level", "?")[:12]
            print(f"  [{i+1:>5}/{len(prospects)}] {prospect['name'][:25]:<25} FINRA:{finra:<12} +SEC:{fsec:<12} All7:{all7:<12} ({elapsed:.1f}s)")

    elapsed = time.time() - start
    print(f"\nPhase 1: {len(results)} in {elapsed:.1f}s")

    print(f"\n{'─'*60}")
    print("REGULATION TOGGLE IMPACT:")
    print(f"{'─'*60}")
    for cn in REGULATION_COMBOS:
        levels = {}
        for r in results:
            lvl = r["regulation_combos"].get(cn, {}).get("compliance_level", "N/A")
            levels[lvl] = levels.get(lvl, 0) + 1
        summary = " | ".join(f"{l}:{c}" for l, c in sorted(levels.items(), key=lambda x: -x[1]))
        print(f"  {cn:<25} {summary}")

    return results


def run_phase2(prospects, template_results, resume=False):
    from compliance_engine import plugins  # noqa: F401
    from compliance_engine import check_compliance, default_registry
    from compliance_engine.correction import self_correct

    GEMINI_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached_count = sum(1 for f in GEMINI_CACHE_DIR.glob("*.json")) if resume else 0
    remaining = len(prospects) - cached_count

    # Optimized: 4 API calls per prospect (1 message + 3 regulations)
    est_calls = remaining * 4
    est_cost = est_calls * 0.00085  # rough avg cost per call
    print(f"\n{'='*60}")
    print(f"PHASE 2: Gemini Deep (OPTIMIZED) | {remaining} remaining")
    print(f"  API calls: ~{est_calls} (4/prospect: 1 msg + 3 regs)")
    print(f"  Est. cost: ~${est_cost:.2f}")
    print(f"  Gemini regs: {', '.join(sorted(GEMINI_REGULATIONS))}")
    print(f"  Regex only:  {', '.join(sorted(r for r in ALL_REGULATION_IDS if r not in GEMINI_REGULATIONS))}")
    print(f"{'='*60}\n")

    results = []
    api_calls_total = 0
    start = time.time()

    for i, (prospect, tmpl) in enumerate(zip(prospects, template_results)):
        cache_file = GEMINI_CACHE_DIR / f"{i:05d}.json"

        if resume and cache_file.exists():
            results.append(json.loads(cache_file.read_text(encoding="utf-8")))
            continue

        result = process_prospect_gemini(
            prospect, tmpl, check_compliance, self_correct, default_registry
        )
        results.append(result)

        calls_this = result.get("gemini_api_calls", 4)
        api_calls_total += calls_this

        cache_file.write_text(json.dumps(result, indent=2), encoding="utf-8")

        # Lighter sleep — fewer calls per prospect now
        time.sleep(0.5)

        if (i + 1) % 10 == 0 or i == 0:
            elapsed = time.time() - start
            processed = i + 1 - cached_count
            rate = processed / elapsed if processed > 0 and elapsed > 0 else 1
            eta = (len(prospects) - i - 1) / rate if rate > 0 else 0
            orig_lvl = result.get("compliance_level", "?")[:15]
            corr_lvl = result.get("corrected_compliance_level", "?")[:15]
            print(
                f"  [{i+1:>5}/{len(prospects)}] {prospect['name'][:30]:<30} "
                f"orig:{orig_lvl:<15} fixed:{corr_lvl:<15} "
                f"(~{api_calls_total} calls, ETA {eta/60:.1f}min)"
            )

    elapsed = time.time() - start
    print(f"\nPhase 2: {len(results)} in {elapsed:.1f}s (~{api_calls_total} API calls)")

    # Summary: original vs corrected
    print(f"\n{'─'*60}")
    print("ORIGINAL vs CORRECTED (primary combo: FINRA+SEC+CAN-SPAM):")
    print(f"{'─'*60}")
    orig_levels, corr_levels = {}, {}
    for r in results:
        ol = r.get("compliance_level", "N/A")
        cl = r.get("corrected_compliance_level", "N/A")
        orig_levels[ol] = orig_levels.get(ol, 0) + 1
        corr_levels[cl] = corr_levels.get(cl, 0) + 1
    print(f"  Original:  {' | '.join(f'{l}:{c}' for l, c in sorted(orig_levels.items(), key=lambda x: -x[1]))}")
    print(f"  Corrected: {' | '.join(f'{l}:{c}' for l, c in sorted(corr_levels.items(), key=lambda x: -x[1]))}")

    return results


# ═══════════════════════════════════════════════════════════════════
# MAIN — --limit writes to test files, never overwrites full batch
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Batch process with compliance algebra")
    parser.add_argument("--template-only", action="store_true", help="Phase 1 only")
    parser.add_argument("--resume", action="store_true", help="Resume Phase 2 from cache")
    parser.add_argument("--limit", type=int, default=None, help="Test with N prospects (separate output files)")
    args = parser.parse_args()

    if not SCORED_JSON.exists():
        print(f"ERROR: scored.json not found at {SCORED_JSON}")
        sys.exit(1)

    prospects = load_prospects(SCORED_JSON)
    print(f"Loaded {len(prospects)} prospects")

    is_test = args.limit is not None
    if is_test:
        prospects = prospects[:args.limit]
        print(f"TEST MODE: limited to {args.limit} prospects (output to test files)")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Phase 1
    template_results = run_phase1(prospects)

    # Output filename: test file if --limit, production file if not
    if is_test:
        template_output = OUTPUT_DIR / f"batch_template_test_{args.limit}.json"
    else:
        template_output = OUTPUT_DIR / "batch_template.json"

    template_output.write_text(json.dumps(template_results, indent=2), encoding="utf-8")
    print(f"\nPhase 1 saved to {template_output}")
    print(f"File size: {template_output.stat().st_size / 1024 / 1024:.1f} MB")

    if args.template_only:
        print("\n--template-only: skipping Phase 2.")
        return

    # Phase 2
    gemini_results = run_phase2(prospects, template_results, resume=args.resume)

    if is_test:
        gemini_output = OUTPUT_DIR / f"batch_gemini_test_{args.limit}.json"
    else:
        gemini_output = OUTPUT_DIR / "batch_gemini.json"

    gemini_output.write_text(json.dumps(gemini_results, indent=2), encoding="utf-8")
    print(f"\nPhase 2 saved to {gemini_output}")
    print(f"File size: {gemini_output.stat().st_size / 1024 / 1024:.1f} MB")

    print(f"\n{'='*60}")
    print(f"BATCH COMPLETE — {len(REGULATION_COMBOS)} combos per prospect")
    print(f"  Original + Corrected versions for each prospect")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
