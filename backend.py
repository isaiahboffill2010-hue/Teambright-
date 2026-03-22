"""
FastAPI Backend — serves pre-computed compliance data for the dashboard.

Endpoints:
    GET  /api/prospects          — paginated list with summary scores
    GET  /api/prospects/{index}  — full detail for one prospect
    GET  /api/stats              — aggregate stats for dashboard header
    GET  /api/regulations        — available regulations + combo definitions
    POST /api/check              — live single-prospect compliance check (demo)

Data source: pre-computed batch JSON from batch_process.py
    - Phase 1: sample_output/batch_template.json (regex only)
    - Phase 2: sample_output/batch_gemini.json (Gemini + regex)

Run locally:
    uvicorn backend:app --reload --port 8000

Deploy to Cloud Run:
    See Dockerfile
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# APP SETUP
# ═══════════════════════════════════════════════════════════════════

app = FastAPI(
    title="The Compliant Prospector API",
    description="Compliance algebra-powered prospecting engine for financial advisors",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Vercel frontend, localhost dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═══════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════

PROJECT_ROOT = Path(__file__).parent
OUTPUT_DIR = PROJECT_ROOT / "sample_output"

# In-memory data store — loaded once at startup
_template_data: List[Dict] = []
_gemini_data: List[Dict] = []
_active_data: List[Dict] = []  # whichever is best available
_data_source: str = "none"


def _load_data():
    """Load best available batch data at startup."""
    global _template_data, _gemini_data, _active_data, _data_source

    gemini_path = OUTPUT_DIR / "batch_gemini.json"
    template_path = OUTPUT_DIR / "batch_template.json"

    # Also check for test files (hackathon dev)
    gemini_test_files = sorted(OUTPUT_DIR.glob("batch_gemini_test_*.json"), reverse=True)
    template_test_files = sorted(OUTPUT_DIR.glob("batch_template_test_*.json"), reverse=True)

    # Priority: production gemini > test gemini > production template > test template
    if gemini_path.exists():
        _gemini_data = json.loads(gemini_path.read_text(encoding="utf-8"))
        _active_data = _gemini_data
        _data_source = f"gemini ({len(_gemini_data)} prospects)"
        logger.info("Loaded production Gemini data: %d prospects", len(_gemini_data))
    elif gemini_test_files:
        path = gemini_test_files[0]
        _gemini_data = json.loads(path.read_text(encoding="utf-8"))
        _active_data = _gemini_data
        _data_source = f"gemini_test ({path.name}, {len(_gemini_data)} prospects)"
        logger.info("Loaded test Gemini data from %s: %d prospects", path.name, len(_gemini_data))
    elif template_path.exists():
        _template_data = json.loads(template_path.read_text(encoding="utf-8"))
        _active_data = _template_data
        _data_source = f"template ({len(_template_data)} prospects)"
        logger.info("Loaded production template data: %d prospects", len(_template_data))
    elif template_test_files:
        path = template_test_files[0]
        _template_data = json.loads(path.read_text(encoding="utf-8"))
        _active_data = _template_data
        _data_source = f"template_test ({path.name}, {len(_template_data)} prospects)"
        logger.info("Loaded test template data from %s: %d prospects", path.name, len(_template_data))
    else:
        logger.warning("No batch data found in %s", OUTPUT_DIR)
        _data_source = "none"


@app.on_event("startup")
async def startup():
    _load_data()


# ═══════════════════════════════════════════════════════════════════
# RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════════

class ProspectSummary(BaseModel):
    index: int
    name: str
    current_role: str
    location: str
    icp_match_score: float
    urgency_score: float
    composite_score: float
    matched_icp: str
    compliance_level: str
    corrected_compliance_level: Optional[str] = None
    binary_level: str
    needs_review: bool
    method: str


class StatsResponse(BaseModel):
    total_prospects: int
    data_source: str
    compliance_distribution: Dict[str, int]
    corrected_distribution: Optional[Dict[str, int]] = None
    avg_composite_score: float
    needs_review_count: int
    method_counts: Dict[str, int]
    regulations_available: List[str]
    combos_available: List[str]


class RegulationInfo(BaseModel):
    regulation_ids: List[str]
    combos: Dict[str, List[str]]
    primary_combo: str
    gemini_regulations: List[str]


# ═══════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "data_source": _data_source,
        "prospects_loaded": len(_active_data),
        "timestamp": time.time(),
    }


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    if not _active_data:
        raise HTTPException(status_code=503, detail="No batch data loaded")

    compliance_dist: Dict[str, int] = {}
    corrected_dist: Dict[str, int] = {}
    method_counts: Dict[str, int] = {}
    total_composite = 0.0
    review_count = 0

    for r in _active_data:
        # Compliance distribution
        cl = r.get("compliance_level", "UNKNOWN")
        compliance_dist[cl] = compliance_dist.get(cl, 0) + 1

        # Corrected distribution
        ccl = r.get("corrected_compliance_level")
        if ccl:
            corrected_dist[ccl] = corrected_dist.get(ccl, 0) + 1

        # Method
        m = r.get("method", "unknown")
        method_counts[m] = method_counts.get(m, 0) + 1

        # Scores
        p = r.get("prospect", {})
        total_composite += p.get("composite_score", 0)

        if r.get("needs_review", False):
            review_count += 1

    # Get regulation info from first prospect's combos
    combos_available = []
    regs_available = []
    if _active_data:
        combos = _active_data[0].get("regulation_combos", {})
        combos_available = list(combos.keys())
        reg_set = set()
        for combo_data in combos.values():
            for rid in combo_data.get("regulation_ids", []):
                reg_set.add(rid)
        regs_available = sorted(reg_set)

    return StatsResponse(
        total_prospects=len(_active_data),
        data_source=_data_source,
        compliance_distribution=compliance_dist,
        corrected_distribution=corrected_dist if corrected_dist else None,
        avg_composite_score=round(total_composite / len(_active_data), 2) if _active_data else 0,
        needs_review_count=review_count,
        method_counts=method_counts,
        regulations_available=regs_available,
        combos_available=combos_available,
    )


@app.get("/api/prospects", response_model=List[ProspectSummary])
async def list_prospects(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    sort_by: str = Query("composite_score", enum=["composite_score", "icp_match_score", "urgency_score", "name", "compliance_level"]),
    sort_order: str = Query("desc", enum=["asc", "desc"]),
    compliance_filter: Optional[str] = Query(None, description="Filter by compliance level"),
    icp_filter: Optional[str] = Query(None, description="Filter by matched ICP"),
    search: Optional[str] = Query(None, description="Search by name or role"),
):
    if not _active_data:
        raise HTTPException(status_code=503, detail="No batch data loaded")

    # Build indexed results
    results = []
    for i, r in enumerate(_active_data):
        p = r.get("prospect", {})

        # Apply filters
        if compliance_filter and r.get("compliance_level") != compliance_filter:
            continue
        if icp_filter and p.get("matched_icp") != icp_filter:
            continue
        if search:
            search_lower = search.lower()
            if search_lower not in p.get("name", "").lower() and search_lower not in p.get("current_role", "").lower():
                continue

        results.append(ProspectSummary(
            index=i,
            name=p.get("name", ""),
            current_role=p.get("current_role", ""),
            location=p.get("location", ""),
            icp_match_score=p.get("icp_match_score", 0),
            urgency_score=p.get("urgency_score", 0),
            composite_score=p.get("composite_score", 0),
            matched_icp=p.get("matched_icp", ""),
            compliance_level=r.get("compliance_level", "UNKNOWN"),
            corrected_compliance_level=r.get("corrected_compliance_level"),
            binary_level=r.get("binary_level", "UNKNOWN"),
            needs_review=r.get("needs_review", False),
            method=r.get("method", "unknown"),
        ))

    # Sort
    reverse = sort_order == "desc"
    if sort_by == "name":
        results.sort(key=lambda x: x.name.lower(), reverse=reverse)
    elif sort_by == "compliance_level":
        level_order = {"HIGH_CONFIDENCE_COMPLIANT": 0, "LIKELY_COMPLIANT": 1, "NEEDS_REVIEW": 2, "INSUFFICIENT_EVIDENCE": 3, "NON_COMPLIANT": 4}
        results.sort(key=lambda x: level_order.get(x.compliance_level, 5), reverse=reverse)
    else:
        results.sort(key=lambda x: getattr(x, sort_by, 0), reverse=reverse)

    # Paginate
    start = (page - 1) * per_page
    end = start + per_page
    return results[start:end]


@app.get("/api/prospects/{index}")
async def get_prospect_detail(
    index: int,
    combo: Optional[str] = Query(None, description="Specific regulation combo to return"),
    corrected: bool = Query(False, description="Return corrected version data"),
):
    if not _active_data:
        raise HTTPException(status_code=503, detail="No batch data loaded")
    if index < 0 or index >= len(_active_data):
        raise HTTPException(status_code=404, detail=f"Prospect index {index} not found (0-{len(_active_data)-1})")

    result = _active_data[index]

    # If requesting a specific combo, return just that combo's data
    if combo:
        combos_key = "corrected_regulation_combos" if corrected else "regulation_combos"
        combos = result.get(combos_key, result.get("regulation_combos", {}))
        if combo not in combos:
            available = list(combos.keys()) if combos else []
            raise HTTPException(status_code=404, detail=f"Combo '{combo}' not found. Available: {available}")
        return {
            "prospect": result.get("prospect"),
            "combo_name": combo,
            "corrected": corrected,
            "data": combos[combo],
        }

    # Return full prospect data
    return result


@app.get("/api/regulations", response_model=RegulationInfo)
async def get_regulations():
    from batch_process import REGULATION_COMBOS, ALL_REGULATION_IDS, PRIMARY_COMBO, GEMINI_REGULATIONS
    return RegulationInfo(
        regulation_ids=ALL_REGULATION_IDS,
        combos=REGULATION_COMBOS,
        primary_combo=PRIMARY_COMBO,
        gemini_regulations=sorted(GEMINI_REGULATIONS),
    )


@app.post("/api/check")
async def live_check(
    message: str,
    prospect_name: str = "",
    prospect_role: str = "",
    regulation_ids: Optional[List[str]] = None,
    use_gemini: bool = False,
    use_algebra: bool = True,
):
    """Live compliance check — for demo purposes. Costs API calls if use_gemini=True."""
    try:
        from compliance_engine import plugins  # noqa: F401
        from compliance_engine import check_compliance, default_registry
        from compliance_engine.correction import self_correct

        company = ""
        if " at " in prospect_role:
            company = prospect_role.split(" at ", 1)[1].strip()

        audit = check_compliance(
            message=message,
            prospect_name=prospect_name,
            prospect_role=prospect_role,
            prospect_company=company,
            use_gemini=use_gemini,
            use_algebra=use_algebra,
            regulation_ids=regulation_ids,
        )

        # Self-correct
        correction = self_correct(
            message=message,
            check_fn=lambda **kw: check_compliance(**kw, regulation_ids=regulation_ids),
            prospect_name=prospect_name,
            prospect_role=prospect_role,
            use_gemini=False,
        )

        return {
            "audit": audit.to_dict(),
            "correction": correction.to_dict(),
            "compliance_level": audit.overall.compliance_level if audit.overall else "UNKNOWN",
            "corrected_compliance_level": (
                correction.corrected_audit.overall.compliance_level
                if correction.corrected_audit and correction.corrected_audit.overall
                else "UNKNOWN"
            ),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reload")
async def reload_data():
    """Reload batch data from disk (after a new batch run)."""
    _load_data()
    return {"status": "reloaded", "data_source": _data_source, "prospects": len(_active_data)}
