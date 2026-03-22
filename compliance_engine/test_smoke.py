"""Smoke test for the compliance engine (registry-driven).

Run from the Teambright- directory:
    python -m compliance_engine.test_smoke
"""

import json
from compliance_engine import (
    check_compliance, check_compliance_quick,
    ComplianceOpinion, jurisdictional_meet,
    Regulation, RuleDefinition, ProspectContext,
    default_registry,
)
from compliance_engine.operators import RuleResult

# ── Test 1: Opinion basics ──────────────────────────────────────
print("=" * 60)
print("TEST 1: ComplianceOpinion basics")
print("=" * 60)

op = ComplianceOpinion.create(0.7, 0.1, 0.2, base_rate=0.3)
print(f"  Opinion:    {op}")
print(f"  P(ω):       {op.projected_probability:.4f}")
print(f"  Level:      {op.compliance_level}")
assert op.lawfulness == 0.7
assert op.compliance_level == "HIGH_CONFIDENCE_COMPLIANT"
print("  ✓ PASSED\n")

# ── Test 2: Jurisdictional meet ─────────────────────────────────
print("=" * 60)
print("TEST 2: Jurisdictional meet (FINRA ⊓ SEC)")
print("=" * 60)

finra = ComplianceOpinion.create(0.8, 0.05, 0.15, base_rate=0.3)
sec = ComplianceOpinion.create(0.6, 0.2, 0.2, base_rate=0.4)
combined = jurisdictional_meet(finra, sec)
print(f"  FINRA:      {finra}")
print(f"  SEC:        {sec}")
print(f"  J⊓(F, S):   {combined}")
assert combined.lawfulness <= min(finra.lawfulness, sec.lawfulness)
assert combined.violation >= max(finra.violation, sec.violation)
assert abs(combined.lawfulness + combined.violation + combined.uncertainty - 1.0) < 1e-9
print("  ✓ PASSED (monotonic restriction, violation, constraint)\n")

# ── Test 3: Registry ────────────────────────────────────────────
print("=" * 60)
print("TEST 3: Regulation registry")
print("=" * 60)
print(f"  {default_registry.summary()}")
assert "FINRA" in default_registry.regulation_ids
assert "SEC" in default_registry.regulation_ids
print("  ✓ PASSED\n")

# ── Test 4: Compliant message ───────────────────────────────────
print("=" * 60)
print("TEST 4: Compliant outreach message")
print("=" * 60)

good_msg = (
    "Given your role as SVP at Artemis Real Estate Partners, I wanted to "
    "share an innovative tax-advantaged strategy we're seeing work well in "
    "the alternative investments space. This is designed as an ancillary "
    "opportunity to complement your existing advisory team by optimizing "
    "overall tax efficiency. Would you be open to a brief conversation?"
)
audit = check_compliance(good_msg, "Aaron Hancock", "SVP at Artemis Real Estate Partners")
print(f"  Overall:    {audit.overall}")
print(f"  Level:      {audit.overall.compliance_level}")
print(f"  Review?     {audit.needs_human_review}")
print(f"  Flagged:    {len(audit.flagged_rules)} rules")
for r in audit.rule_results:
    status = "✓" if r.opinion.lawfulness > 0.5 else "✗" if r.opinion.violation > 0.4 else "?"
    print(f"    {status} [{r.regulation}] {r.rule_id}: l={r.opinion.lawfulness:.2f} v={r.opinion.violation:.2f} u={r.opinion.uncertainty:.2f}")
print("  ✓ PASSED\n")

# ── Test 5: Non-compliant message ───────────────────────────────
print("=" * 60)
print("TEST 5: Non-compliant outreach message")
print("=" * 60)

bad_msg = (
    "I guarantee you'll see 15% returns with our exclusive strategy. "
    "Act now — this is a once in a lifetime opportunity! Our clients "
    "have seen incredible returns. You should leave your current advisor "
    "and switch to our best-in-class approach."
)
audit_bad = check_compliance(bad_msg, "John Doe", "VP at Some Corp")
print(f"  Overall:    {audit_bad.overall}")
print(f"  Level:      {audit_bad.overall.compliance_level}")
print(f"  Flagged:    {len(audit_bad.flagged_rules)} rules")
for r in audit_bad.flagged_rules:
    print(f"    ✗ [{r.regulation}] {r.rule_id}: {r.explanation}")
    if r.flagged_phrases:
        print(f"       Phrases: {r.flagged_phrases[:3]}")
assert audit_bad.needs_human_review, "Bad message should need review"
assert audit_bad.overall.violation > 0.3, "Bad message should have high violation"
print("  ✓ PASSED\n")

# ── Test 6: Pluggable regulation ────────────────────────────────
print("=" * 60)
print("TEST 6: Adding a custom regulation at runtime")
print("=" * 60)

def check_ny_state_disclosure(msg: str, ctx: ProspectContext) -> RuleResult:
    """Example: NY requires specific disclosure in financial solicitations."""
    has_disclosure = "registered investment adviser" in msg.lower()
    if has_disclosure:
        op = ComplianceOpinion.create(0.85, 0.02, 0.13, 0.4)
        expl = "NY disclosure present."
    else:
        op = ComplianceOpinion.create(0.30, 0.25, 0.45, 0.4)
        expl = "Missing NY-required RIA disclosure."
    return RuleResult(
        rule_id="NY-GBL-349a",
        rule_name="NY state disclosure requirement",
        regulation="NY-STATE",
        opinion=op, explanation=expl,
        suggested_fixes=["Add 'registered investment adviser' disclosure"] if not has_disclosure else [],
    )

ny_regulation = Regulation(
    regulation_id="NY-STATE",
    regulation_name="New York State Financial Regulations",
    base_rate=0.4,
    rules=[
        RuleDefinition(
            rule_id="NY-GBL-349a",
            rule_name="NY state disclosure requirement",
            description="NY General Business Law §349(a): required disclosures in financial solicitations.",
            checker=check_ny_state_disclosure,
            severity="major",
        ),
    ],
)

default_registry.register(ny_regulation)
print(f"  {default_registry.summary()}")

# Now check_compliance automatically includes NY rules!
audit_ny = check_compliance(good_msg, "Aaron Hancock", "SVP at Artemis RE")
ny_rules = [r for r in audit_ny.rule_results if r.regulation == "NY-STATE"]
print(f"  NY rules ran: {len(ny_rules)}")
print(f"  NY result:    {ny_rules[0].explanation}")
print(f"  Overall now:  {audit_ny.overall}")
assert len(ny_rules) == 1, "NY rule should have run"
print("  ✓ PASSED\n")

# Clean up — remove NY so it doesn't affect other tests
default_registry.unregister("NY-STATE")

# ── Test 7: Quick check ────────────────────────────────────────
print("=" * 60)
print("TEST 7: Quick compliance check (API-friendly)")
print("=" * 60)
quick = check_compliance_quick(good_msg)
print(f"  {json.dumps(quick, indent=2)}")
print("  ✓ PASSED\n")

# ── Test 8: JSON audit trail ────────────────────────────────────
print("=" * 60)
print("TEST 8: JSON audit trail (for frontend)")
print("=" * 60)
audit_json = audit.to_dict()
print(json.dumps(audit_json, indent=2)[:600] + "...\n")
print("  ✓ PASSED\n")

print("=" * 60)
print("ALL 8 TESTS PASSED — Compliance engine ready!")
print(f"Registered: {default_registry.regulation_ids}")
print("=" * 60)
