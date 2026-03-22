"""Test self-correction with expanded static replacements across all 7 regulations.

Run: python test_correction.py
"""

from compliance_engine import plugins  # load all 7 regulations
from compliance_engine import check_compliance, self_correct

# Bad message with violations across multiple regulations
bad_msg = (
    "I guarantee this exclusive opportunity will double your money. "
    "Act now - limited time! Leave your current advisor. "
    "Our clients have seen incredible returns. "
    "Text me for the secret strategy. Delete this after reading."
)

print("=" * 60)
print("TEST: Self-Correction (Static Replacements)")
print("=" * 60)

result = self_correct(
    message=bad_msg,
    check_fn=check_compliance,
    prospect_name="Jane Doe",
    prospect_role="VP Finance",
    use_gemini=False,
)

print(f"Original:  l={result.original_audit.overall.lawfulness:.3f} v={result.original_audit.overall.violation:.3f} => {result.original_audit.overall.compliance_level}")
print(f"Corrected: l={result.corrected_audit.overall.lawfulness:.3f} v={result.corrected_audit.overall.violation:.3f} => {result.corrected_audit.overall.compliance_level}")
print(f"Iterations: {result.iterations}")
print(f"Resolved: {result.fully_resolved}")
print(f"Corrections: {len(result.corrections_applied)}")
for c in result.corrections_applied:
    print(f'  [{c.method}] "{c.original_phrase}" -> "{c.replacement}"')
print()
print(f"Improvement: {result._improvement()}")
print()

# Also test: FINRA+SEC only (original scope)
print("=" * 60)
print("TEST: Self-Correction (FINRA+SEC only)")
print("=" * 60)

result2 = self_correct(
    message=bad_msg,
    check_fn=lambda **kw: check_compliance(**kw, regulation_ids=["FINRA", "SEC"]),
    prospect_name="Jane Doe",
    prospect_role="VP Finance",
    use_gemini=False,
)

print(f"Original:  l={result2.original_audit.overall.lawfulness:.3f} v={result2.original_audit.overall.violation:.3f} => {result2.original_audit.overall.compliance_level}")
print(f"Corrected: l={result2.corrected_audit.overall.lawfulness:.3f} v={result2.corrected_audit.overall.violation:.3f} => {result2.corrected_audit.overall.compliance_level}")
print(f"Resolved: {result2.fully_resolved}")
print(f"Corrections: {len(result2.corrections_applied)}")

print()
print("ALL TESTS COMPLETE")
