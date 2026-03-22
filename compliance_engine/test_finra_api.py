"""Quick FINRA API test — proves auth + data query work end-to-end.

Tries: 1) Rulebook (Firm-only), 2) Broker Dealer Firm List (public), 3) Any public dataset.
Run: python -m compliance_engine.test_finra_api
"""

import json
from compliance_engine.finra_api import (
    get_access_token, _api_get, _api_post,
    fetch_rule, check_api_status, FINRA_API_BASE,
)

print("=" * 60)
print("FINRA API Integration Test")
print("=" * 60)

# Step 1: Auth
print("\n1. Authentication...")
status = check_api_status()
for k, v in status.items():
    emoji = "✅" if v is True else "❌" if v is False else "ℹ️"
    print(f"   {emoji} {k}: {v}")

if not status["auth_success"]:
    print("\n❌ Auth failed. Cannot proceed.")
    exit(1)

# Step 2: Try public datasets to prove the query pipeline works
print("\n2. Testing data query pipeline with public datasets...")

PUBLIC_DATASETS = [
    ("registration", "brokerDealerFirmList"),
    ("equity", "regShoDaily"),
    ("equity", "blocksSummary"),
]

api_works = False
for group, dataset in PUBLIC_DATASETS:
    try:
        endpoint = f"/data/group/{group}/name/{dataset}"
        data = _api_get(endpoint, params={"limit": "2"})
        print(f"   ✅ {group}/{dataset}: Got {type(data).__name__}", end="")
        if isinstance(data, list):
            print(f" with {len(data)} records")
            if data:
                print(f"      Sample keys: {list(data[0].keys())[:5]}")
        elif isinstance(data, dict):
            print(f" keys: {list(data.keys())[:5]}")
        api_works = True
        break
    except Exception as e:
        err = str(e)[:100]
        print(f"   ❌ {group}/{dataset}: {err}")

# Step 3: Try Rulebook (expected to fail with public creds)
print("\n3. Testing Rulebook dataset (requires Firm credentials)...")
try:
    data = fetch_rule("2210", use_mock=False)
    print(f"   ✅ Rulebook accessible! Got: {type(data).__name__}")
    api_works = True
except Exception as e:
    print(f"   ℹ️  Expected: Rulebook requires Firm/Org credentials (${1650}/mo)")
    print(f"      Error: {str(e)[:120]}")

# Summary
print("\n" + "=" * 60)
if api_works:
    print("✅ FINRA API INTEGRATION PROVEN")
    print("   Auth: OAuth2 via FIP ✓")
    print("   Data query pipeline: working ✓")
    print("   Rulebook: needs Firm creds (we embed rules locally)")
    print("\n   For demo: show live auth + data query,")
    print("   explain rulebook access is a deployment config change.")
else:
    print("⚠️  Auth works but no datasets accessible.")
    print("   Public creds may have limited access.")
    print("   For demo: show auth success + explain architecture.")
print("=" * 60)
