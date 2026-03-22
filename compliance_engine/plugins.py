"""
Plugin Regulations — import this module to register all available regulations.

Core regulations (FINRA, SEC) are auto-imported by checker.py.
Plugin regulations are opt-in: import this module to make them available.

Usage:
    from compliance_engine import plugins  # registers MiFID II, NY State, etc.

After import, all plugin regulations appear in default_registry
and can be filtered by regulation_id in check_compliance().
"""

# Plugin regulations — each auto-registers on import
from . import rules_mifid2      # noqa: F401  — MiFID II (EU)
from . import rules_ny_state    # noqa: F401  — NY State (Martin Act + DFS)
from . import rules_nasaa       # noqa: F401  — NASAA (state securities)
from . import rules_canspam_tcpa  # noqa: F401  — CAN-SPAM / TCPA
from . import rules_sox         # noqa: F401  — SOX recordkeeping

PLUGIN_REGULATION_IDS = [
    "MiFID_II",
    "NY_State",
    "NASAA",
    "CAN_SPAM_TCPA",
    "SOX",
]

CORE_REGULATION_IDS = [
    "FINRA",
    "SEC",
]

ALL_REGULATION_IDS = CORE_REGULATION_IDS + PLUGIN_REGULATION_IDS
