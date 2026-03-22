"""
Regulation Registry — pluggable regulation framework.

Any regulation (FINRA, SEC, state-level, EU MiFID II, etc.) is defined
as a Regulation object containing RuleDefinitions. New regulations are
registered at startup and automatically included in the compliance check.

Architecture:
    Regulation
      └── RuleDefinition (multiple)
            └── check(message, context) → RuleResult

    Registry
      └── register(regulation)
      └── get_all_rules() → flat list for the checker
      └── get_regulations() → grouped by regulation

This makes the engine regulation-agnostic. The compliance algebra
(jurisdictional meet) handles the combination regardless of how many
or which regulations are registered.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol

from .opinion import ComplianceOpinion
from .operators import RuleResult


# ═══════════════════════════════════════════════════════════════════
# CORE ABSTRACTIONS
# ═══════════════════════════════════════════════════════════════════


@dataclass
class ProspectContext:
    """Context about the prospect and advisor, passed to rule checks.

    Extensible dict-style: add any field needed for future rules.
    """
    prospect_name: str = ""
    prospect_role: str = ""
    prospect_company: str = ""
    prospect_location: str = ""
    advisor_name: str = ""
    advisor_firm: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


class RuleChecker(Protocol):
    """Protocol for a rule check function.

    Any callable matching this signature can be a rule checker.
    """
    def __call__(self, message: str, context: ProspectContext) -> RuleResult: ...


@dataclass
class RuleDefinition:
    """A single compliance rule within a regulation.

    Attributes:
        rule_id:      Unique ID like 'FINRA-2210-d1-A'
        rule_name:    Human-readable name
        description:  What the rule checks for
        checker:      Function(message, context) → RuleResult
        severity:     'critical' | 'major' | 'minor' | 'advisory'
        enabled:      Can be toggled off without removing
    """
    rule_id: str
    rule_name: str
    description: str
    checker: Callable[[str, ProspectContext], RuleResult]
    severity: str = "major"
    enabled: bool = True


@dataclass
class Regulation:
    """A regulatory body and its collection of rules.

    Attributes:
        regulation_id:   Short key like 'FINRA' or 'SEC'
        regulation_name: Full name like 'Financial Industry Regulatory Authority'
        base_rate:       Default base rate for opinions under this regulation
        rules:           List of RuleDefinitions
        metadata:        Anything else (API endpoints, version, etc.)
    """
    regulation_id: str
    regulation_name: str
    base_rate: float = 0.3
    rules: List[RuleDefinition] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_rule(self, rule: RuleDefinition) -> None:
        """Add a rule to this regulation."""
        self.rules.append(rule)

    @property
    def enabled_rules(self) -> List[RuleDefinition]:
        """Only rules that are currently enabled."""
        return [r for r in self.rules if r.enabled]


# ═══════════════════════════════════════════════════════════════════
# REGULATION REGISTRY — singleton pattern
# ═══════════════════════════════════════════════════════════════════


class RegulationRegistry:
    """Central registry for all regulations.

    Usage:
        registry = RegulationRegistry()
        registry.register(finra_regulation)
        registry.register(sec_regulation)
        registry.register(my_state_regulation)  # plug in anything

        # Checker uses this to get all rules
        for reg_id, rules in registry.get_rules_by_regulation().items():
            ...
    """

    def __init__(self) -> None:
        self._regulations: Dict[str, Regulation] = {}

    def register(self, regulation: Regulation) -> None:
        """Register a new regulation. Overwrites if same ID exists."""
        self._regulations[regulation.regulation_id] = regulation

    def unregister(self, regulation_id: str) -> None:
        """Remove a regulation by ID."""
        self._regulations.pop(regulation_id, None)

    def get(self, regulation_id: str) -> Optional[Regulation]:
        """Get a specific regulation by ID."""
        return self._regulations.get(regulation_id)

    def get_all_regulations(self) -> List[Regulation]:
        """All registered regulations."""
        return list(self._regulations.values())

    def get_rules_by_regulation(self) -> Dict[str, List[RuleDefinition]]:
        """All enabled rules grouped by regulation ID."""
        return {
            reg_id: reg.enabled_rules
            for reg_id, reg in self._regulations.items()
        }

    def get_all_enabled_rules(self) -> List[tuple[str, RuleDefinition]]:
        """Flat list of (regulation_id, rule_definition) pairs."""
        result = []
        for reg_id, reg in self._regulations.items():
            for rule in reg.enabled_rules:
                result.append((reg_id, rule))
        return result

    @property
    def regulation_ids(self) -> List[str]:
        return list(self._regulations.keys())

    def __len__(self) -> int:
        return len(self._regulations)

    def summary(self) -> str:
        """Human-readable summary of registered regulations."""
        lines = [f"RegulationRegistry: {len(self._regulations)} regulation(s)"]
        for reg_id, reg in self._regulations.items():
            enabled = len(reg.enabled_rules)
            total = len(reg.rules)
            lines.append(f"  {reg_id}: {reg.regulation_name} ({enabled}/{total} rules enabled)")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# DEFAULT GLOBAL REGISTRY
# ═══════════════════════════════════════════════════════════════════

# The default registry. Regulations auto-register here on import.
default_registry = RegulationRegistry()
