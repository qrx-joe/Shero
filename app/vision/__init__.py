"""Vision and detection helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class DetectionResult:
    has_person: bool
    summary: str


class PersonDetector(Protocol):
    def check_person(self) -> DetectionResult: ...
