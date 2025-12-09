from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DSLAction:
    verb: str
    target_calendar: Optional[str] = None
    path: Optional[str] = None
    filters: List[str] = field(default_factory=list)
    assignments: Dict[str, str] = field(default_factory=dict)


@dataclass
class DSLBlock:
    calendar_name: str
    actions: List[DSLAction] = field(default_factory=list)


@dataclass
class ExecutionContext:
    calendar_id: Optional[str]
    calendar_name: str
    filtered_events: List[Dict[str, Any]] = field(default_factory=list)
    dry_run: bool = False
