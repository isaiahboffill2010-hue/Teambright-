"""
FINRA Rulebook API Integration — live rule text from api.finra.org.

This module connects to FINRA's machine-readable rulebook (FIRST™)
to fetch live rule text and taxonomy terms for Rule 2210 and others.

Auth flow (OAuth2 client credentials):
    1. POST to FIP token endpoint with Basic auth (client_id:client_secret)
    2. Receive access_token (JWT, 30 min TTL)
    3. Use Bearer token on api.finra.org data endpoints

FINRA API docs: https://developer.finra.org/docs
Auth docs: https://developer.finra.org/docs#getting_started-api_platform_basics-authorization
"""

from __future__ import annotations

import base64
import json
import os
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

# Token endpoint — FINRA Identity Platform (FIP), NOT api.finra.org
FINRA_TOKEN_URL = "https://ews.fip.finra.org/fip/rest/ews/oauth2/access_token?grant_type=client_credentials"

# Data query endpoint
FINRA_API_BASE = "https://api.finra.org"

# Rulebook dataset names
FINRA_RULEBOOK_DATASET = "finraRulebook"
FINRA_RULEBOOK_MOCK = "finraRulebookMock"

# Key rules for outreach compliance
OUTREACH_RULES = ["2210", "2211", "2090", "2111"]


def _load_env() -> tuple[str, str]:
    """Load FINRA API credentials from env vars or .env file."""
    client_id = os.environ.get("FINRA_API_CLIENT_ID", "")
    client_secret = os.environ.get("FINRA_API_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key == "FINRA_API_CLIENT_ID":
                    client_id = val
                elif key == "FINRA_API_CLIENT_SECRET":
                    client_secret = val

    return client_id, client_secret


# ═══════════════════════════════════════════════════════════════════
# AUTH — OAuth2 Client Credentials via FINRA Identity Platform (FIP)
# ═══════════════════════════════════════════════════════════════════

_cached_token: Optional[str] = None


def get_access_token(force_refresh: bool = False) -> str:
    """Get OAuth2 bearer token from FINRA FIP.

    Flow: POST to FIP with Basic auth header (base64 of client_id:client_secret)
    → receive JSON with access_token (valid ~30 min).
    """
    global _cached_token
    if _cached_token and not force_refresh:
        return _cached_token

    client_id, client_secret = _load_env()
    if not client_id or not client_secret:
        raise ValueError(
            "FINRA API credentials not found. Set FINRA_API_CLIENT_ID and "
            "FINRA_API_CLIENT_SECRET in environment or .env file."
        )

    # Basic auth: base64(client_id:client_secret)
    credentials = f"{client_id}:{client_secret}"
    b64_creds = base64.b64encode(credentials.encode()).decode()

    req = Request(
        FINRA_TOKEN_URL,
        data=b"",  # POST with empty body; grant_type is in the URL
        headers={
            "Authorization": f"Basic {b64_creds}",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode())
            _cached_token = body["access_token"]
            expires_in = body.get("expires_in", "unknown")
            print(f"  Token acquired (expires in {expires_in}s)")
            return _cached_token
    except HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode()[:500]
        except Exception:
            pass
        raise RuntimeError(
            f"FINRA FIP auth failed: {e.code} {e.reason}\n  Body: {error_body}"
        ) from e
    except URLError as e:
        raise RuntimeError(f"FINRA FIP unreachable: {e.reason}") from e


# ═══════════════════════════════════════════════════════════════════
# QUERY API — fetch rulebook data from api.finra.org
# ═══════════════════════════════════════════════════════════════════

def _api_get(endpoint: str, params: Optional[Dict[str, str]] = None) -> Any:
    """Make authenticated GET request to FINRA data API."""
    token = get_access_token()
    url = f"{FINRA_API_BASE}{endpoint}"
    if params:
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{query}"

    req = Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    })

    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        if e.code == 401:
            # Token expired, retry
            get_access_token(force_refresh=True)
            req.remove_header("Authorization")
            req.add_header("Authorization", f"Bearer {_cached_token}")
            with urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        error_body = ""
        try:
            error_body = e.read().decode()[:500]
        except Exception:
            pass
        raise RuntimeError(f"FINRA API GET error: {e.code} {e.reason}\n  {error_body}") from e


def _api_post(endpoint: str, body: Dict[str, Any]) -> Any:
    """Make authenticated POST request to FINRA data API."""
    token = get_access_token()
    url = f"{FINRA_API_BASE}{endpoint}"

    req = Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        if e.code == 401:
            get_access_token(force_refresh=True)
            req.remove_header("Authorization")
            req.add_header("Authorization", f"Bearer {_cached_token}")
            with urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        error_body = ""
        try:
            error_body = e.read().decode()[:500]
        except Exception:
            pass
        raise RuntimeError(f"FINRA API POST error: {e.code} {e.reason}\n  {error_body}") from e


# ═══════════════════════════════════════════════════════════════════
# RULEBOOK FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def fetch_rulebook_metadata(use_mock: bool = False) -> Dict[str, Any]:
    """Fetch metadata for the FINRA Rulebook dataset."""
    dataset = FINRA_RULEBOOK_MOCK if use_mock else FINRA_RULEBOOK_DATASET
    endpoint = f"/data/group/finraContent/name/{dataset}"
    return _api_get(endpoint, params={"limit": "1"})


def fetch_rule(rule_number: str, use_mock: bool = False) -> Any:
    """Fetch a specific FINRA rule by number (e.g., '2210').

    Uses POST with compareFilters to query by rule number.
    """
    dataset = FINRA_RULEBOOK_MOCK if use_mock else FINRA_RULEBOOK_DATASET
    endpoint = f"/data/group/finraContent/name/{dataset}"

    body = {
        "fields": ["ruleNumber", "ruleTitle", "ruleText", "taxonomyTerms"],
        "compareFilters": [
            {
                "fieldName": "ruleNumber",
                "fieldValue": rule_number,
                "compareType": "EQUAL",
            }
        ],
        "limit": 10,
    }

    return _api_post(endpoint, body)


def fetch_outreach_rules(use_mock: bool = False) -> List[Dict[str, Any]]:
    """Fetch all rules relevant to outreach compliance (2210, 2211, 2090, 2111)."""
    results = []
    for rule_num in OUTREACH_RULES:
        try:
            data = fetch_rule(rule_num, use_mock=use_mock)
            results.append({"rule_number": rule_num, "data": data})
        except Exception as e:
            results.append({"rule_number": rule_num, "error": str(e)})
    return results


def get_rule_text_for_context(use_mock: bool = False) -> str:
    """Get concatenated rule text for LLM context window (Gemini).

    This text gets fed alongside the outreach message for
    AI-assisted compliance reasoning.
    """
    rules = fetch_outreach_rules(use_mock=use_mock)
    parts = []
    for r in rules:
        if "error" in r:
            parts.append(f"[Rule {r['rule_number']}: fetch error — {r['error']}]")
        else:
            data = r["data"]
            if isinstance(data, list):
                for item in data:
                    title = item.get("ruleTitle", f"Rule {r['rule_number']}")
                    text = item.get("ruleText", "")
                    parts.append(f"### {title}\n{text}\n")
            elif isinstance(data, dict):
                parts.append(json.dumps(data, indent=2)[:2000])
    return "\n---\n".join(parts)


# ═══════════════════════════════════════════════════════════════════
# STATUS CHECK
# ═══════════════════════════════════════════════════════════════════

def check_api_status() -> Dict[str, Any]:
    """Check if FINRA API is reachable and credentials work."""
    result = {
        "credentials_found": False,
        "auth_success": False,
        "rulebook_accessible": False,
        "error": None,
    }

    client_id, client_secret = _load_env()
    result["credentials_found"] = bool(client_id and client_secret)
    if client_id:
        result["client_id_preview"] = client_id[:8] + "..."

    if not result["credentials_found"]:
        result["error"] = "No credentials found. Set FINRA_API_CLIENT_ID and FINRA_API_CLIENT_SECRET."
        return result

    try:
        get_access_token(force_refresh=True)
        result["auth_success"] = True
    except Exception as e:
        result["error"] = f"Auth failed: {e}"
        return result

    try:
        data = fetch_rulebook_metadata(use_mock=False)
        result["rulebook_accessible"] = True
        if isinstance(data, list):
            result["records_returned"] = len(data)
        elif isinstance(data, dict):
            result["response_keys"] = list(data.keys())[:5]
    except Exception as e:
        # Try without mock
        result["rulebook_error"] = str(e)[:200]
        result["note"] = "Auth works but rulebook query failed. Public creds may not have rulebook access."

    return result


# ═══════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("FINRA API Status Check")
    print("=" * 60)

    status = check_api_status()
    for k, v in status.items():
        emoji = "✅" if v is True else "❌" if v is False else "ℹ️"
        print(f"  {emoji} {k}: {v}")

    if status["auth_success"]:
        print("\nAttempting to fetch Rule 2210...")
        try:
            data = fetch_rule("2210", use_mock=False)
            print(f"  Response type: {type(data).__name__}")
            preview = json.dumps(data, indent=2)[:800]
            print(f"  Preview:\n{preview}")
        except Exception as e:
            print(f"  Error: {e}")
            print("\n  Trying with mock dataset...")
            try:
                data = fetch_rule("2210", use_mock=True)
                print(f"  Mock response type: {type(data).__name__}")
                preview = json.dumps(data, indent=2)[:800]
                print(f"  Preview:\n{preview}")
            except Exception as e2:
                print(f"  Mock also failed: {e2}")
    print()
