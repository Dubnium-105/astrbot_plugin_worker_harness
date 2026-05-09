"""Small audit log abstraction for Harness decisions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class AuditEntry:
    event: str
    detail: dict[str, Any]
    created_at: str


class AuditLog:
    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    def record(self, event: str, **detail: Any) -> AuditEntry:
        entry = AuditEntry(
            event=event,
            detail=detail,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._entries.append(entry)
        return entry

    def entries(self) -> list[AuditEntry]:
        return list(self._entries)
