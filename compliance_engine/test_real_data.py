"""
Real data integration test — runs compliance engine against scored.json prospects.

Tests:
    1. Load and rank prospects from scored.json
    2. Generate sample outreach per the advisor's 3-sentence template
    3. Run compliance engine on each generated message
    4. Verify compliant messages pass, bad messages fail
    5. Show full audit trail for top prospects

Run from Teambright- directory:
    python -m compliance_engine.test_real_data
"""

import json
import os
from pathlib import Path

from compliance_engine import check_compliance, default_registry


# ═══════════════════════════════════════════════════════════════════
# STEP 1: Load and rank prospects
# ═══════════════════════════════════════════════════════════════════

# Pulse_Miami_Hackathon is a sibling of Teambright-, so go up two levels from this file
DATA_PATH = Path(__file__).parent.parent.parent / "Pulse_Miami_Hackathon" / "datasets" / "scored.json"

print("=" * 70)
print("REAL DATA TEST — Compliance Engine × scored.json")
print("=" * 70)
print(f"\nRegistry: {default_registry.summary()}\n")

with open(DATA_PATH, "r", encoding="utf-8") as f:
    prospects = json.load(f)

print(f"Loaded {len(prospects)} prospects from scored.json")

# Rank by composite score: 60% ICP match + 40% urgency
for p in prospects:
    p["composite_score"] = 0.6 * p["icp_match_score"] + 0.4 * p["urgency_score"]

ranked = sorted(prospects, key=lambda p: p["composite_score"], reverse=True)

# Filter: only prospects with recommended outreach (not "Not recommended")
actionable = [
    p for p in ranked
    if not p["recommended_outreach_angle"].lower().startswith("not recommended")
]

print(f"Actionable prospects (not 'not recommended'): {len(actionable)}")
print(f"Top 5 by composite score:")
for i, p in enumerate(actionable[:5]):
    print(f"  {i+1}. {p['name']} — ICP:{p['icp_match_score']} Urg:{p['urgency_score']} "
          f"Comp:{p['composite_score']:.0f} ({p['matched_icp']})")
    print(f"     {p['current_role']}")
    if p['why_now_reasons']:
        print(f"     Why now: {p['why_now_reasons'][0][:80]}...")
print()


# ═══════════════════════════════════════════════════════════════════
# STEP 2: Generate outreach using the advisor's 3-sentence template
# ═══════════════════════════════════════════════════════════════════

def generate_outreach(prospect: dict) -> str:
    """Generate a compliant outreach message following the advisor's template.

    3-sentence structure:
        1. The Hook — mention their firm/industry
        2. The Value — creative tax strategy / tax efficiency
        3. The Guardrail — complement, not replace
    """
    name = prospect["name"].split()[0]  # First name
    role = prospect["current_role"]

    # Extract company from role (after "at")
    company = ""
    if " at " in role:
        company = role.split(" at ")[-1]
    elif " of " in role:
        company = role.split(" of ")[-1]

    # Pick the outreach angle or generate from why_now
    if prospect["why_now_reasons"]:
        why_now = prospect["why_now_reasons"][0]
        # Simplify into a hook
        hook_detail = why_now.split("—")[0].strip() if "—" in why_now else why_now[:60]
    else:
        hook_detail = f"your track record in {prospect.get('matched_icp', 'finance').replace('_', ' ')}"

    msg = (
        f"Hi {name}, given your role at {company}, I wanted to share an innovative "
        f"tax-advantaged strategy we're seeing resonate with professionals in your space — "
        f"particularly given {hook_detail.lower() if not hook_detail[0].isupper() else hook_detail.lower()}. "
        f"This is designed as an ancillary opportunity to optimize your overall tax efficiency "
        f"without disrupting your current setup. "
        f"Would you be open to a brief conversation to see if it's a fit to complement "
        f"your existing advisory team?"
    )
    return msg


def generate_bad_outreach(prospect: dict) -> str:
    """Generate a deliberately non-compliant message for testing."""
    name = prospect["name"].split()[0]
    return (
        f"Hi {name}, I guarantee you'll see exceptional returns with our exclusive "
        f"strategy. Our clients have seen incredible performance — you should leave "
        f"your current advisor immediately. Act now, this is a once in a lifetime "
        f"opportunity that will double your money. Don't miss out!"
    )


# ═══════════════════════════════════════════════════════════════════
# STEP 3: Run compliance checks on top prospects
# ═══════════════════════════════════════════════════════════════════

print("=" * 70)
print("COMPLIANCE RESULTS — Top 10 Prospects (Good Messages)")
print("=" * 70)

results_good = []
for p in actionable[:10]:
    msg = generate_outreach(p)
    audit = check_compliance(
        message=msg,
        prospect_name=p["name"],
        prospect_role=p["current_role"],
        prospect_company=p["current_role"].split(" at ")[-1] if " at " in p["current_role"] else "",
        prospect_location=p.get("location", ""),
    )
    results_good.append((p, msg, audit))

    level = audit.overall.compliance_level
    emoji = "✅" if not audit.needs_human_review else "⚠️" if level != "NON_COMPLIANT" else "❌"

    print(f"\n{emoji} {p['name']} (ICP:{p['icp_match_score']} Urg:{p['urgency_score']})")
    print(f"   Role: {p['current_role']}")
    print(f"   Overall: l={audit.overall.lawfulness:.3f}  v={audit.overall.violation:.3f}  "
          f"u={audit.overall.uncertainty:.3f}  →  {level}")
    print(f"   P(compliant): {audit.overall.projected_probability:.3f}")
    print(f"   FINRA: l={audit.finra_composite.lawfulness:.3f}  SEC: l={audit.sec_composite.lawfulness:.3f}")
    print(f"   Review needed: {audit.needs_human_review}")

    if audit.flagged_rules:
        for r in audit.flagged_rules:
            print(f"   ⚡ {r.rule_id}: {r.explanation[:70]}...")

# ═══════════════════════════════════════════════════════════════════
# STEP 4: Run bad messages to verify detection
# ═══════════════════════════════════════════════════════════════════

print("\n\n" + "=" * 70)
print("COMPLIANCE RESULTS — Bad Messages (should all be flagged)")
print("=" * 70)

bad_count = 0
for p in actionable[:3]:
    bad_msg = generate_bad_outreach(p)
    audit_bad = check_compliance(
        message=bad_msg,
        prospect_name=p["name"],
        prospect_role=p["current_role"],
    )

    level = audit_bad.overall.compliance_level
    print(f"\n❌ {p['name']} — BAD MESSAGE")
    print(f"   Overall: l={audit_bad.overall.lawfulness:.3f}  v={audit_bad.overall.violation:.3f}  "
          f"u={audit_bad.overall.uncertainty:.3f}  →  {level}")
    print(f"   Flagged rules: {len(audit_bad.flagged_rules)}")
    for r in audit_bad.flagged_rules:
        print(f"   ✗ {r.rule_id}: {r.explanation[:70]}")
        if r.flagged_phrases:
            print(f"     Phrases: {r.flagged_phrases[:3]}")

    if audit_bad.needs_human_review:
        bad_count += 1

assert bad_count == 3, f"All 3 bad messages should need review, got {bad_count}"


# ═══════════════════════════════════════════════════════════════════
# STEP 5: Detailed audit trail for the #1 prospect
# ═══════════════════════════════════════════════════════════════════

print("\n\n" + "=" * 70)
print("DETAILED AUDIT TRAIL — #1 Prospect")
print("=" * 70)

top_prospect, top_msg, top_audit = results_good[0]
print(f"\nProspect: {top_prospect['name']}")
print(f"Role: {top_prospect['current_role']}")
print(f"ICP: {top_prospect['icp_match_score']}  Urgency: {top_prospect['urgency_score']}")
print(f"\nGenerated message:\n  \"{top_msg}\"\n")
print(f"Overall opinion: {top_audit.overall}")
print(f"Compliance level: {top_audit.overall.compliance_level}")
print(f"\nAll rule assessments:")
for r in top_audit.rule_results:
    bar_l = "█" * int(r.opinion.lawfulness * 20)
    bar_v = "█" * int(r.opinion.violation * 20)
    bar_u = "░" * int(r.opinion.uncertainty * 20)
    print(f"  [{r.regulation:5s}] {r.rule_id:30s}  l={r.opinion.lawfulness:.2f} {bar_l}")
    print(f"  {'':5s}  {'':30s}  v={r.opinion.violation:.2f} {bar_v}")
    print(f"  {'':5s}  {'':30s}  u={r.opinion.uncertainty:.2f} {bar_u}")
    print(f"  {'':5s}  {'':30s}  → {r.explanation[:60]}")
    print()


# ═══════════════════════════════════════════════════════════════════
# STEP 6: Statistics summary
# ═══════════════════════════════════════════════════════════════════

print("=" * 70)
print("SUMMARY STATISTICS")
print("=" * 70)

auto_approve = sum(1 for _, _, a in results_good if not a.needs_human_review)
needs_review = sum(1 for _, _, a in results_good if a.needs_human_review)
avg_lawfulness = sum(a.overall.lawfulness for _, _, a in results_good) / len(results_good)
avg_violation = sum(a.overall.violation for _, _, a in results_good) / len(results_good)
avg_uncertainty = sum(a.overall.uncertainty for _, _, a in results_good) / len(results_good)

print(f"  Prospects tested (good msgs):  {len(results_good)}")
print(f"  Auto-approve path:             {auto_approve}")
print(f"  Needs human review:            {needs_review}")
print(f"  Avg lawfulness:                {avg_lawfulness:.3f}")
print(f"  Avg violation:                 {avg_violation:.3f}")
print(f"  Avg uncertainty:               {avg_uncertainty:.3f}")
print(f"  Bad messages caught:           {bad_count}/3")
print(f"  Total prospects in dataset:    {len(prospects)}")
print(f"  Actionable prospects:          {len(actionable)}")
print()

# ═══════════════════════════════════════════════════════════════════
# STEP 7: Export sample audit JSON (for frontend dev)
# ═══════════════════════════════════════════════════════════════════

output_dir = Path(__file__).parent.parent / "sample_output"
output_dir.mkdir(exist_ok=True)

# Export top 5 audits as JSON
sample_audits = []
for p, msg, audit in results_good[:5]:
    entry = audit.to_dict()
    entry["prospect"] = {
        "name": p["name"],
        "role": p["current_role"],
        "location": p.get("location", ""),
        "icp_match_score": p["icp_match_score"],
        "urgency_score": p["urgency_score"],
        "composite_score": p["composite_score"],
        "why_now_reasons": p.get("why_now_reasons", []),
        "recommended_outreach_angle": p.get("recommended_outreach_angle", ""),
    }
    entry["generated_message"] = msg
    sample_audits.append(entry)

output_file = output_dir / "sample_audits.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(sample_audits, f, indent=2)

print(f"Exported {len(sample_audits)} sample audits to {output_file}")
print("\n✅ ALL REAL DATA TESTS PASSED")
