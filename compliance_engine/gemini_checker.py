"""
Gemini Deep Compliance Layer — LLM-powered compliance analysis.

Architecture:
    Layer 1 (regex):  Fast pre-screen → flagged phrases + initial signals
    Layer 2 (Gemini): Deep analysis → authoritative ComplianceOpinion per rule

Gemini is taught the compliance algebra (Subjective Logic). It reasons
about lawfulness, violation, and uncertainty as distinct evidence categories.
Its opinions feed directly into the existing algebra pipeline:
    - Weakest-link within regulation
    - Jurisdictional meet J⊓ across regulations

Call strategy: One Gemini call per regulation (2 calls per message).
Fallback: If Gemini fails, regex opinions are preserved.

Model: gemini-2.5-flash (via GEMINI_API_KEY env var)
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Dict, List, Optional, Tuple

from .opinion import ComplianceOpinion
from .operators import RuleResult
from .registry import (
    ProspectContext,
    RegulationRegistry,
    RuleDefinition,
    default_registry,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# GEMINI CLIENT SETUP
# ═══════════════════════════════════════════════════════════════════

_client = None


def _get_client():
    """Lazy-init Gemini client using GEMINI_API_KEY only."""
    global _client
    if _client is None:
        # Prevent SDK from auto-detecting the wrong key
        os.environ.pop("GOOGLE_API_KEY", None)
        from google import genai
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY not set. Cannot use Gemini compliance layer."
            )
        _client = genai.Client(api_key=api_key)
    return _client


GEMINI_MODEL = "gemini-2.5-flash"


# ═══════════════════════════════════════════════════════════════════
# SYSTEM PROMPT — teaches Gemini the compliance algebra
# ═══════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are a FINRA/SEC compliance analyst powered by the Compliance Algebra — 
a formal framework based on Subjective Logic (Jøsang 2016), published by 
Syed, Silaghi, Abujar & Alssadi (2026).

## Subjective Logic Opinions

Every compliance assessment is an opinion ω = (l, v, u, a) where:
  - l (lawfulness):  Evidence FOR compliance.  Range [0, 1].
  - v (violation):   Evidence AGAINST compliance / for violation.  Range [0, 1].
  - u (uncertainty): Absence of evidence — what we DON'T know.  Range [0, 1].
  - a (base_rate):   Prior probability of compliance.  Range [0, 1].
  - Constraint: l + v + u = 1

CRITICAL DISTINCTIONS:
  - l=0.8, v=0.1, u=0.1 → "Strong evidence of compliance, minor concern"
  - l=0.3, v=0.0, u=0.7 → "Weak evidence, mostly uncertain — NOT a violation"
  - l=0.1, v=0.7, u=0.2 → "Strong evidence of violation"
  - l=0.0, v=0.0, u=1.0 → "No evidence either way — vacuous opinion"

Binary compliance systems collapse the first two into "pass" and the 
last two into "fail." The algebra preserves the distinction between 
"probably compliant" and "uncertain" — which is exactly how a human 
compliance officer thinks.

## Your Task

For each rule provided, you must:
1. Analyze the outreach message against the specific rule text.
2. Assign l, v, u, a values with explicit reasoning for EACH component.
3. Identify specific phrases that constitute evidence for or against compliance.
4. Suggest fixes for any flagged phrases.

## Scoring Guidelines

l (lawfulness) — What evidence EXISTS that this message COMPLIES?
  - Positive compliance signals (complement language, professional tone, etc.)
  - Absence of prohibited content (this is evidence, not just lack of violation)
  - Contextual appropriateness for the rule's requirements

v (violation) — What evidence EXISTS that this message VIOLATES?
  - Specific phrases that match prohibited categories
  - Structural issues (e.g., all benefits, no risk acknowledgment)
  - Contextual violations (e.g., pressure disguised as urgency)
  - NOTE: v should be LOW if there are no violating phrases, even if l is also low

u (uncertainty) — What CAN'T we determine from the text alone?
  - Ambiguous phrasing that could go either way
  - Claims that require external verification (titles, AUM, awards)
  - Context-dependent interpretations
  - NOTE: high u is NOT a penalty — it's honest epistemic humility

a (base_rate) — Prior probability of compliance for this rule type:
  - 0.3 for critical rules (promissory, exaggerated claims) — most messages have issues
  - 0.4 for major rules (testimonials, performance) — common in outreach
  - 0.5 for minor/advisory rules — neutral prior

## Severity Levels
Each rule has a severity:
  - critical: Gatekeeping. Violations can block the message.
  - major: Important. Violations trigger human review.
  - minor: Noted in audit trail, doesn't block.
  - advisory: Best practice, informational only.

## Response Format

You MUST respond with ONLY valid JSON (no markdown, no backticks, no preamble). 
The JSON must be an array of objects, one per rule:

[
  {
    "rule_id": "FINRA-2210-d1-A",
    "lawfulness": 0.72,
    "lawfulness_reasoning": "Message uses measured language...",
    "violation": 0.08,
    "violation_reasoning": "Minor concern with 'exclusive' phrasing...",
    "uncertainty": 0.20,
    "uncertainty_reasoning": "Cannot verify if audience is retail or institutional...",
    "base_rate": 0.3,
    "flagged_phrases": ["exclusive opportunity"],
    "suggested_fixes": ["Replace 'exclusive opportunity' with 'a timely opportunity'"],
    "explanation": "Overall assessment summary for audit trail."
  }
]
"""


# ═══════════════════════════════════════════════════════════════════
# PROMPT CONSTRUCTION
# ═══════════════════════════════════════════════════════════════════

def _build_regulation_prompt(
    regulation_id: str,
    message: str,
    rules: List[RuleDefinition],
    regex_results: List[RuleResult],
    ctx: ProspectContext,
) -> str:
    """Build the user prompt for one regulation's Gemini call."""

    # Rule texts section
    rule_texts = []
    for rule in rules:
        rule_texts.append(
            f"  - Rule ID: {rule.rule_id}\n"
            f"    Name: {rule.rule_name}\n"
            f"    Description: {rule.description}\n"
            f"    Severity: {rule.severity}"
        )
    rules_block = "\n".join(rule_texts)

    # Regex pre-screen section
    regex_block_parts = []
    for rr in regex_results:
        if rr.regulation == regulation_id:
            flags = ", ".join(rr.flagged_phrases[:5]) if rr.flagged_phrases else "none"
            regex_block_parts.append(
                f"  - {rr.rule_id}: l={rr.opinion.lawfulness:.2f}, "
                f"v={rr.opinion.violation:.2f}, u={rr.opinion.uncertainty:.2f} | "
                f"flagged: [{flags}] | {rr.explanation}"
            )
    regex_block = "\n".join(regex_block_parts) if regex_block_parts else "  (no regex pre-screen results)"

    # Prospect context
    ctx_parts = []
    if ctx.prospect_name:
        ctx_parts.append(f"Name: {ctx.prospect_name}")
    if ctx.prospect_role:
        ctx_parts.append(f"Role: {ctx.prospect_role}")
    if ctx.prospect_company:
        ctx_parts.append(f"Company: {ctx.prospect_company}")
    if ctx.prospect_location:
        ctx_parts.append(f"Location: {ctx.prospect_location}")
    ctx_block = "; ".join(ctx_parts) if ctx_parts else "No context provided"

    return f"""Analyze this outreach message for {regulation_id} compliance.

## Message
\"\"\"{message}\"\"\"

## Prospect Context
{ctx_block}

## {regulation_id} Rules to Evaluate
{rules_block}

## Regex Pre-Screen Results (for reference — you may agree or override)
{regex_block}

Evaluate the message against EACH rule above. Return ONLY a JSON array 
with one object per rule. Follow the Subjective Logic opinion framework 
exactly: l + v + u must equal 1.0 for each rule.
"""


# ═══════════════════════════════════════════════════════════════════
# GEMINI CALL + RESPONSE PARSING
# ═══════════════════════════════════════════════════════════════════

def _parse_gemini_response(response_text: str) -> Optional[List[dict]]:
    """Parse Gemini's JSON response, handling common formatting issues."""
    text = response_text.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        # Remove opening fence (with optional language tag)
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        # Remove closing fence
        text = re.sub(r"\n?```\s*$", "", text)
        text = text.strip()

    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        elif isinstance(parsed, dict) and "rules" in parsed:
            return parsed["rules"]
        else:
            logger.warning("Gemini returned unexpected JSON structure: %s", type(parsed))
            return None
    except json.JSONDecodeError as e:
        logger.error("Failed to parse Gemini JSON response: %s", e)
        logger.debug("Raw response: %s", text[:500])
        return None


def _validate_opinion_values(item: dict) -> Tuple[float, float, float, float]:
    """Extract and validate l, v, u, a from a parsed rule result.

    Ensures l + v + u = 1.0 (with tolerance). Normalizes if close.
    Returns (l, v, u, a) or raises ValueError.
    """
    l = float(item.get("lawfulness", 0.0))
    v = float(item.get("violation", 0.0))
    u = float(item.get("uncertainty", 0.0))
    a = float(item.get("base_rate", 0.5))

    # Clamp to [0, 1]
    l = max(0.0, min(1.0, l))
    v = max(0.0, min(1.0, v))
    u = max(0.0, min(1.0, u))
    a = max(0.0, min(1.0, a))

    total = l + v + u
    if abs(total - 1.0) > 0.05:
        raise ValueError(
            f"l + v + u = {total:.4f}, too far from 1.0 "
            f"(l={l:.4f}, v={v:.4f}, u={u:.4f})"
        )

    # Normalize to exactly 1.0
    if total != 1.0 and total > 0:
        l, v, u = l / total, v / total, u / total

    return l, v, u, a


def _gemini_results_to_rule_results(
    parsed: List[dict],
    regulation_id: str,
    rules: List[RuleDefinition],
) -> Dict[str, RuleResult]:
    """Convert parsed Gemini JSON into RuleResult objects.

    Returns a dict keyed by rule_id for easy lookup.
    """
    results = {}
    rule_map = {r.rule_id: r for r in rules}

    for item in parsed:
        rule_id = item.get("rule_id", "")
        if rule_id not in rule_map:
            logger.warning("Gemini returned unknown rule_id: %s", rule_id)
            continue

        try:
            l, v, u, a = _validate_opinion_values(item)
        except (ValueError, TypeError) as e:
            logger.warning("Invalid opinion values for %s: %s", rule_id, e)
            continue

        rule_def = rule_map[rule_id]
        opinion = ComplianceOpinion.create(l, v, u, a)

        # Build rich explanation from Gemini's reasoning
        explanation_parts = []
        if item.get("explanation"):
            explanation_parts.append(item["explanation"])
        if item.get("lawfulness_reasoning"):
            explanation_parts.append(f"[Lawfulness] {item['lawfulness_reasoning']}")
        if item.get("violation_reasoning"):
            explanation_parts.append(f"[Violation] {item['violation_reasoning']}")
        if item.get("uncertainty_reasoning"):
            explanation_parts.append(f"[Uncertainty] {item['uncertainty_reasoning']}")

        explanation = " | ".join(explanation_parts) if explanation_parts else "Gemini analysis."

        results[rule_id] = RuleResult(
            rule_id=rule_id,
            rule_name=rule_def.rule_name,
            regulation=regulation_id,
            opinion=opinion,
            explanation=f"[Gemini] {explanation}",
            flagged_phrases=item.get("flagged_phrases", []),
            suggested_fixes=item.get("suggested_fixes", []),
        )

    return results


def gemini_check_regulation(
    regulation_id: str,
    message: str,
    regex_results: List[RuleResult],
    ctx: ProspectContext,
    registry: Optional[RegulationRegistry] = None,
) -> Dict[str, RuleResult]:
    """Run Gemini deep analysis for one regulation.

    Args:
        regulation_id:  'FINRA' or 'SEC'
        message:        The outreach message to check
        regex_results:  Pre-screen results from the regex layer
        ctx:            Prospect context
        registry:       Regulation registry (defaults to global)

    Returns:
        Dict of rule_id → RuleResult from Gemini analysis.
        Empty dict if Gemini call fails (caller falls back to regex).
    """
    reg = (registry or default_registry).get(regulation_id)
    if not reg:
        logger.warning("Regulation %s not found in registry", regulation_id)
        return {}

    rules = reg.enabled_rules
    if not rules:
        return {}

    # Build prompt
    prompt = _build_regulation_prompt(
        regulation_id, message, rules, regex_results, ctx
    )

    # Call Gemini
    try:
        client = _get_client()
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config={
                "system_instruction": SYSTEM_PROMPT,
                "temperature": 0.1,  # Low temp for consistent compliance analysis
            },
        )
        response_text = response.text
    except Exception as e:
        logger.error("Gemini API call failed for %s: %s", regulation_id, e)
        return {}

    # Parse response
    parsed = _parse_gemini_response(response_text)
    if parsed is None:
        logger.error("Failed to parse Gemini response for %s", regulation_id)
        return {}

    # Convert to RuleResults
    return _gemini_results_to_rule_results(parsed, regulation_id, rules)


# ═══════════════════════════════════════════════════════════════════
# FULL GEMINI CHECK — both regulations
# ═══════════════════════════════════════════════════════════════════

def gemini_check_all(
    message: str,
    regex_results: List[RuleResult],
    ctx: ProspectContext,
    registry: Optional[RegulationRegistry] = None,
) -> Dict[str, RuleResult]:
    """Run Gemini analysis across all registered regulations.

    Returns dict of rule_id → RuleResult for all rules Gemini analyzed.
    Rules not covered (due to errors) are absent — caller keeps regex opinion.
    """
    reg = registry or default_registry
    all_results = {}

    for regulation in reg.get_all_regulations():
        gemini_results = gemini_check_regulation(
            regulation.regulation_id, message, regex_results, ctx, reg
        )
        all_results.update(gemini_results)

    return all_results
