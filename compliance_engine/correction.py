"""
Self-Correction Loop — fail → suggest fix → re-check.

Two correction modes:
    1. Static replacements (default): Deterministic, fast, auditable.
       100+ standard phrase replacements across all 7 regulations.
    2. Gemini-powered rewriting (optional): Context-aware rewrites
       that understand regulatory nuance. Uses the compliance algebra
       to verify each correction actually improves the opinion.

The core pipeline:
    1. Check message → get audit
    2. If NON_COMPLIANT or NEEDS_REVIEW:
       a. Collect all flagged phrases + suggested fixes
       b. Apply fixes (static or Gemini)
       c. Re-check the corrected message
       d. Return both: original audit + corrected audit
    3. Track correction history for the audit trail

This module also includes temporal decay from the compliance algebra:
assessment opinions degrade over time, modeling that compliance
checks become stale.
"""

from __future__ import annotations

import logging
import math
import re
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

from .opinion import ComplianceOpinion
from .operators import ComplianceAudit, RuleResult

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# TEMPORAL DECAY (from compliance algebra §8)
# ═══════════════════════════════════════════════════════════════════

def decay_opinion(
    opinion: ComplianceOpinion,
    elapsed_hours: float,
    half_life_hours: float = 720.0,  # 30 days default
) -> ComplianceOpinion:
    """Apply temporal decay to a compliance opinion.

    Per §8.1 of the compliance algebra: ω(t) = (λ(t)·l, λ(t)·v, 1−λ(t)(l+v), a)
    where λ(t) = 2^(-t/half_life) is exponential decay.

    The opinion converges to vacuity (pure uncertainty) over time,
    modeling that compliance assessments grow stale.
    """
    if elapsed_hours <= 0:
        return opinion

    lam = math.pow(2.0, -elapsed_hours / half_life_hours)
    lam = max(0.0, min(1.0, lam))

    l_new = lam * opinion.lawfulness
    v_new = lam * opinion.violation
    u_new = 1.0 - l_new - v_new

    return ComplianceOpinion.create(
        lawfulness=max(0.0, l_new),
        violation=max(0.0, v_new),
        uncertainty=max(0.0, u_new),
        base_rate=opinion.base_rate,
    )


def assess_staleness(
    assessment_timestamp: float,
    current_timestamp: Optional[float] = None,
    half_life_hours: float = 168.0,
) -> dict:
    """Evaluate how stale a compliance assessment is."""
    now = current_timestamp or time.time()
    elapsed_hours = (now - assessment_timestamp) / 3600.0

    lam = math.pow(2.0, -elapsed_hours / half_life_hours)

    if lam >= 0.9:
        freshness = "FRESH"
    elif lam >= 0.7:
        freshness = "RECENT"
    elif lam >= 0.5:
        freshness = "AGING"
    elif lam >= 0.25:
        freshness = "STALE"
    else:
        freshness = "EXPIRED"

    return {
        "elapsed_hours": round(elapsed_hours, 1),
        "decay_factor": round(lam, 4),
        "freshness": freshness,
        "half_life_hours": half_life_hours,
        "recommendation": (
            "Re-check recommended" if freshness in ("STALE", "EXPIRED")
            else "Assessment still valid" if freshness in ("FRESH", "RECENT")
            else "Consider re-checking soon"
        ),
    }


# ═══════════════════════════════════════════════════════════════════
# SELF-CORRECTION ENGINE
# ═══════════════════════════════════════════════════════════════════

@dataclass
class CorrectionStep:
    """One step in the correction history."""
    original_phrase: str
    replacement: str
    rule_id: str
    rule_name: str
    method: str = "static"  # "static" or "gemini"


@dataclass
class CorrectionResult:
    """Result of the self-correction loop."""

    original_message: str
    original_audit: ComplianceAudit
    corrected_message: Optional[str] = None
    corrected_audit: Optional[ComplianceAudit] = None
    corrections_applied: List[CorrectionStep] = field(default_factory=list)
    iterations: int = 0
    max_iterations: int = 3
    fully_resolved: bool = False
    correction_method: str = "static"  # "static" or "gemini"

    def to_dict(self) -> dict:
        return {
            "original_message": self.original_message,
            "original_audit": self.original_audit.to_dict(),
            "corrected_message": self.corrected_message,
            "corrected_audit": self.corrected_audit.to_dict() if self.corrected_audit else None,
            "corrections_applied": [
                {
                    "original": c.original_phrase,
                    "replacement": c.replacement,
                    "rule_id": c.rule_id,
                    "rule_name": c.rule_name,
                    "method": c.method,
                }
                for c in self.corrections_applied
            ],
            "iterations": self.iterations,
            "fully_resolved": self.fully_resolved,
            "correction_method": self.correction_method,
            "improvement": self._improvement(),
        }

    def _improvement(self) -> Optional[dict]:
        if not self.corrected_audit or not self.corrected_audit.overall:
            return None
        orig = self.original_audit.overall
        corr = self.corrected_audit.overall
        if not orig:
            return None
        return {
            "lawfulness_delta": round(corr.lawfulness - orig.lawfulness, 4),
            "violation_delta": round(corr.violation - orig.violation, 4),
            "uncertainty_delta": round(corr.uncertainty - orig.uncertainty, 4),
        }


# ═══════════════════════════════════════════════════════════════════
# STATIC REPLACEMENTS — expanded for all 7 regulations
# ═══════════════════════════════════════════════════════════════════

STANDARD_REPLACEMENTS = {
    # ─── FINRA: Promissory → neutral ────────────────────────────
    "guarantee": "aim to provide",
    "guaranteed": "designed to support",
    "guarantees": "is designed to offer",
    "promise": "intend to offer",
    "promised": "outlined",
    "risk-free": "carefully structured",
    "risk free": "carefully structured",
    "no-risk": "measured approach to",
    "no risk": "thoughtfully managed",
    "safe investment": "considered strategy",
    "certain return": "targeted approach",
    "never lose": "focus on downside management",
    "ensure": "work toward",
    "assured": "designed with the goal of",
    "can't lose": "focuses on risk management",
    "no way to lose": "aims to manage downside risk",
    "sure thing": "an opportunity worth exploring",
    "safe bet": "a considered approach",
    "set for life": "designed for long-term stability",
    "worry-free": "structured with care",
    "peace of mind": "thoughtful planning",

    # ─── FINRA: Exaggerated → measured ──────────────────────────
    "best investment": "a well-suited investment",
    "best strategy": "an effective strategy",
    "best approach": "a sound approach",
    "best returns": "competitive returns",
    "best advisor": "a dedicated advisor",
    "best firm": "a well-established firm",
    "top advisor": "an experienced advisor",
    "top rated": "well-regarded",
    "number one": "a leading",
    "#1": "a leading",
    "unbeatable": "compelling",
    "extraordinary returns": "meaningful returns",
    "exceptional returns": "competitive returns",
    "incredible returns": "solid returns",
    "incredible performance": "consistent performance",
    "amazing results": "positive results",
    "exclusive opportunity": "a timely opportunity",
    "exclusive access": "access to",
    "exclusive deal": "an available opportunity",
    "proven strategy": "a well-researched approach",
    "proven method": "an established methodology",
    "proven system": "a tested approach",
    "revolutionary": "innovative",
    "secret strategy": "a specialized approach",
    "secret method": "an advanced methodology",
    "cutting-edge": "modern",
    "proprietary": "our firm's",

    # ─── FINRA: Performance predictions → neutral ───────────────
    "will return": "has historically targeted",
    "will yield": "is designed to target",
    "will generate": "aims to generate",
    "will double": "seeks meaningful growth for",
    "will triple": "targets significant growth for",
    "projected return": "historical range",
    "expected return": "targeted range",
    "forecast": "analysis suggests",

    # ─── FINRA: Pressure → consultative ─────────────────────────
    "act now": "when you have a moment",
    "limited time": "at your convenience",
    "last chance": "an opportunity worth considering",
    "once in a lifetime": "a noteworthy development",
    "don't miss": "you may find value in",
    "hurry": "at your earliest convenience",
    "immediately": "when it suits your schedule",
    "right now": "at a time that works for you",
    "before it's too late": "while this may be relevant to your situation",
    "window closing": "an opportunity to explore",
    "running out": "available for discussion",
    "now or never": "worth considering at your convenience",
    "limited spots": "available appointments",
    "first come": "scheduling is flexible",

    # ─── SEC: Relationship → complementary ──────────────────────
    "leave your current advisor": "complement your existing advisory team",
    "switch from your advisor": "work alongside your current advisor",
    "replace your advisor": "add a complementary perspective to your team",
    "better than your advisor": "a different angle to complement your team",
    "fire your advisor": "consider an additional perspective alongside your advisor",
    "drop your advisor": "explore a complementary advisory relationship",
    "ditch your advisor": "consider adding to your advisory team",
    "your advisor isn't": "your existing team may benefit from",
    "your advisor can't": "an additional perspective could",
    "your advisor won't": "a complementary approach might",
    "your advisor failed": "there may be additional angles worth exploring",
    "your advisor missed": "there are additional opportunities to consider",
    "why are you still with": "have you considered complementing",
    "underperforming": "may benefit from a fresh perspective",
    "underserving": "could be enhanced with additional expertise",

    # ─── SEC: Testimonial → factual ─────────────────────────────
    "our clients have seen": "in our experience, strategies like this are designed for",
    "our clients have experienced": "our approach focuses on",
    "our clients have achieved": "our methodology targets",
    "our clients have earned": "our strategies aim to deliver",
    "other clients have": "our approach is designed to",
    "many clients have": "our methodology focuses on",
    "a client recently": "our practice specializes in",
    "success stories": "case studies available upon request",
    "results speak": "our approach is documented",

    # ─── MiFID II: Suitability assumptions → consultative ───────
    "perfect for you": "potentially relevant to your situation",
    "ideal for you": "worth exploring given your profile",
    "right for you": "may align with your objectives",
    "what you need": "what may be worth exploring",
    "you need": "you may benefit from",
    "you should invest": "it may be worth exploring",
    "you must": "you may want to consider",
    "exactly what you need": "potentially well-aligned with your situation",
    "tailored to your": "designed with situations like yours in mind",
    "based on your situation": "considering profiles similar to yours",
    "we know your": "based on publicly available information about your",
    "we understand your": "we appreciate that professionals in your position",
    "recommend": "suggest exploring",

    # ─── MiFID II: Misleading → clear ───────────────────────────
    "simple way to": "one approach to",
    "easy path to": "a structured path toward",
    "just need to": "one option is to",
    "only have to": "one approach involves",
    "no downside": "with managed risk considerations",
    "no loss": "with risk management measures",
    "always profits": "aims for consistent performance",
    "never fails": "has a strong track record",

    # ─── MiFID II: Free claims → transparent ────────────────────
    "free": "complimentary initial",
    "no cost": "no fee for the initial consultation",
    "no fee": "waived for the introductory meeting",
    "complimentary": "at no charge for the initial discussion",
    "at no cost": "with no obligation for the first meeting",

    # ─── NY State: Martin Act (lower threshold) ─────────────────
    "innovative": "a specialized",
    "premier": "an established",
    "elite": "experienced",
    "leading": "well-established",

    # ─── NY State: Off-channel → compliant channel ──────────────
    "text me": "reach out through our firm's contact channels",
    "dm me": "contact us through official channels",
    "hit me up": "feel free to reach out",
    "message me on": "contact our office at",
    "call my cell": "reach our office at",
    "personal email": "firm email",
    "off the record": "for your reference",
    "between us": "for your consideration",
    "just between": "for your review",

    # ─── NASAA: Blanket recommendations → exploratory ───────────
    "everyone should": "many professionals find value in",
    "everybody should": "it's worth considering",
    "everyone can benefit": "many professionals benefit from",
    "can't go wrong": "this approach has merit",
    "no-brainer": "a compelling option",
    "obvious choice": "a strong candidate",
    "regardless of your": "depending on your specific",
    "no matter your": "considering your unique",

    # ─── NASAA: Insider language → transparent ──────────────────
    "insider": "informed",
    "confidential tip": "publicly available insight",
    "non-public": "recently published",
    "keep this quiet": "for your review",
    "I shouldn't be telling": "I wanted to share",

    # ─── NASAA: Senior targeting → respectful ───────────────────
    "at your age": "at this stage of your career",
    "at your stage": "given your experience level",
    "your generation": "professionals with your depth of experience",
    "don't wait": "when the timing is right",
    "don't delay": "at a pace that works for you",

    # ─── CAN-SPAM: Deceptive headers → honest ──────────────────
    "re:": "",  # Remove fake reply prefix
    "fw:": "",  # Remove fake forward prefix
    "fwd:": "",  # Remove fake forward prefix
    "congratulations": "an opportunity",
    "you won": "you may be interested in",
    "you've been selected": "based on your professional profile",
    "you've been chosen": "given your background",

    # ─── SOX: Ephemeral channels → archivable ──────────────────
    "delete this": "please keep this for your records",
    "destroy this": "please retain this communication",
    "don't save this": "this is for your records",
    "don't keep this": "please retain for compliance",
    "off-record": "on the record",
    "unofficial": "through official channels",
    "unrecorded": "documented",
    "undocumented": "for the record",

    # ─── SOX: Concealment → transparent ─────────────────────────
    "don't tell": "please share with your team as appropriate",
    "don't mention": "feel free to discuss",
    "don't include": "please include for the record",
    "don't report": "please document accordingly",
    "don't disclose": "disclosure is available",
    "cover up": "address transparently",
    "hide": "document",
    "conceal": "disclose",
    "the arrangement": "the proposed advisory relationship",
    "the deal": "the proposed engagement",
    "the package": "the service offering",
}


def _apply_replacements(message: str, flagged_rules: List[RuleResult]) -> Tuple[str, List[CorrectionStep]]:
    """Apply standard replacements for flagged phrases.

    Returns the corrected message and a list of corrections made.
    """
    corrected = message
    steps = []

    for rule in flagged_rules:
        for phrase in rule.flagged_phrases:
            phrase_lower = phrase.lower().strip()
            replacement = STANDARD_REPLACEMENTS.get(phrase_lower)

            if replacement:
                pattern = re.compile(re.escape(phrase), re.IGNORECASE)
                if pattern.search(corrected):
                    corrected = pattern.sub(replacement, corrected, count=1)
                    steps.append(CorrectionStep(
                        original_phrase=phrase,
                        replacement=replacement,
                        rule_id=rule.rule_id,
                        rule_name=rule.rule_name,
                        method="static",
                    ))

    return corrected, steps


# ═══════════════════════════════════════════════════════════════════
# GEMINI-POWERED CORRECTION (optional upgrade)
# ═══════════════════════════════════════════════════════════════════

GEMINI_CORRECTION_PROMPT = """You are a FINRA/SEC compliance editor. Your job is to rewrite 
flagged phrases in a financial advisor's outreach message to make them compliant 
while preserving the message's persuasive intent and natural tone.

## Rules
1. ONLY rewrite the specific flagged phrases — do NOT rewrite the entire message.
2. Each replacement must be compliant with the specific rule that flagged it.
3. Replacements should sound natural, not robotic or overly cautious.
4. Maintain the advisor's voice and the message's persuasive purpose.
5. Do NOT add disclaimers, disclosures, or legal language — just fix the phrases.

## Response Format
Return ONLY valid JSON (no markdown, no backticks). An array of objects:
[
  {
    "original_phrase": "the exact flagged phrase",
    "replacement": "the compliant replacement",
    "rule_id": "the rule that flagged it",
    "reasoning": "why this replacement is compliant"
  }
]

If a flagged phrase doesn't need changing (false positive), omit it from the array.
"""


def _gemini_correct(
    message: str,
    flagged_rules: List[RuleResult],
) -> Tuple[str, List[CorrectionStep]]:
    """Use Gemini to contextually rewrite flagged phrases.

    Falls back to static replacements if Gemini fails.
    """
    import json
    import os

    # Build the correction request
    flags_block = []
    for rule in flagged_rules:
        for phrase in rule.flagged_phrases:
            flags_block.append({
                "phrase": phrase,
                "rule_id": rule.rule_id,
                "rule_name": rule.rule_name,
                "regulation": rule.regulation,
                "explanation": rule.explanation[:200],
            })

    if not flags_block:
        return message, []

    user_prompt = f"""Rewrite the flagged phrases in this message to be compliant.

## Message
\"\"\"{message}\"\"\"

## Flagged Phrases
{json.dumps(flags_block, indent=2)}

Return ONLY a JSON array of replacements.
"""

    try:
        os.environ.pop("GOOGLE_API_KEY", None)
        from google import genai
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_prompt,
            config={
                "system_instruction": GEMINI_CORRECTION_PROMPT,
                "temperature": 0.3,
            },
        )

        # Parse response
        text = response.text.strip()
        if text.startswith("```"):
            import re as re_mod
            text = re_mod.sub(r"^```(?:json)?\s*\n?", "", text)
            text = re_mod.sub(r"\n?```\s*$", "", text)
            text = text.strip()

        replacements = json.loads(text)
        if not isinstance(replacements, list):
            logger.warning("Gemini correction returned non-list: %s", type(replacements))
            return _apply_replacements(message, flagged_rules)

    except Exception as e:
        logger.error("Gemini correction failed: %s. Falling back to static.", e)
        return _apply_replacements(message, flagged_rules)

    # Apply Gemini's replacements
    corrected = message
    steps = []

    for item in replacements:
        original = item.get("original_phrase", "")
        replacement = item.get("replacement", "")
        rule_id = item.get("rule_id", "unknown")

        if not original or not replacement:
            continue

        pattern = re.compile(re.escape(original), re.IGNORECASE)
        if pattern.search(corrected):
            corrected = pattern.sub(replacement, corrected, count=1)
            steps.append(CorrectionStep(
                original_phrase=original,
                replacement=replacement,
                rule_id=rule_id,
                rule_name=item.get("rule_name", ""),
                method="gemini",
            ))

    # If Gemini produced no usable replacements, fall back to static
    if not steps:
        logger.info("Gemini produced no replacements. Falling back to static.")
        return _apply_replacements(message, flagged_rules)

    return corrected, steps


# ═══════════════════════════════════════════════════════════════════
# MAIN SELF-CORRECTION LOOP
# ═══════════════════════════════════════════════════════════════════

def self_correct(
    message: str,
    check_fn: Callable,
    prospect_name: str = "",
    prospect_role: str = "",
    max_iterations: int = 3,
    use_gemini: bool = False,
) -> CorrectionResult:
    """Run the self-correction loop.

    Pipeline:
        1. Check original message
        2. If issues found:
           a. use_gemini=False → apply static replacements
           b. use_gemini=True → Gemini rewrites flagged phrases
              (falls back to static if Gemini fails)
        3. Re-check corrected message
        4. Repeat up to max_iterations
        5. Return full correction history with improvement delta

    Args:
        message:          The original outreach message.
        check_fn:         The check_compliance function.
        prospect_name:    Prospect name for personalization check.
        prospect_role:    Prospect role for personalization check.
        max_iterations:   Maximum correction attempts.
        use_gemini:       If True, use Gemini for contextual rewrites.

    Returns:
        CorrectionResult with original and corrected audits.
    """
    # Step 1: Initial check
    initial_audit = check_fn(
        message=message,
        prospect_name=prospect_name,
        prospect_role=prospect_role,
    )

    result = CorrectionResult(
        original_message=message,
        original_audit=initial_audit,
        max_iterations=max_iterations,
        correction_method="gemini" if use_gemini else "static",
    )

    # If already compliant, no correction needed
    if not initial_audit.needs_human_review:
        result.fully_resolved = True
        result.corrected_message = message
        result.corrected_audit = initial_audit
        return result

    # Step 2-4: Correction loop
    current_message = message
    current_audit = initial_audit
    all_steps: List[CorrectionStep] = []

    for iteration in range(max_iterations):
        result.iterations = iteration + 1

        # Apply corrections — static or Gemini
        if use_gemini:
            corrected_msg, steps = _gemini_correct(
                current_message, current_audit.flagged_rules
            )
        else:
            corrected_msg, steps = _apply_replacements(
                current_message, current_audit.flagged_rules
            )

        if not steps:
            # No more corrections available
            break

        all_steps.extend(steps)

        # Re-check
        new_audit = check_fn(
            message=corrected_msg,
            prospect_name=prospect_name,
            prospect_role=prospect_role,
        )

        current_message = corrected_msg
        current_audit = new_audit

        if not new_audit.needs_human_review:
            break

    result.corrected_message = current_message
    result.corrected_audit = current_audit
    result.corrections_applied = all_steps
    result.fully_resolved = not current_audit.needs_human_review

    return result
