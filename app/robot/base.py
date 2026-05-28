from __future__ import annotations

from abc import ABC, abstractmethod


class RobotController(ABC):
    """Stable boundary between mission logic and robot-specific SDK code."""

    @abstractmethod
    def go_to_b(self) -> None:
        """Move from point A to pickup/checking point B."""

    @abstractmethod
    def patrol(self) -> None:
        """Scan the pickup area from point B."""

    @abstractmethod
    def return_to_a(self) -> None:
        """Return from point B to point A."""

    @abstractmethod
    def stop(self) -> None:
        """Stop all robot motion."""
