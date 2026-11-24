"""Ports (interfaces) the application layer depends on. Implemented in `infrastructure`."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class Clock(Protocol):
    """Source of time — injected so use cases are deterministic in tests."""

    def now(self) -> datetime: ...
