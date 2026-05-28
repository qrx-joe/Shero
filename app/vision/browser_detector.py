from __future__ import annotations

from typing import Callable

from app.vision import DetectionResult


class BrowserPersonDetector:
    """Person detector backed by browser-side MediaPipe events.

    The browser runs MediaPipe Object Detection on the laptop camera stream
    and POSTs `/api/vision/event` when it sees a person with enough confidence
    over a short window. This detector reads the resulting flag at mission
    decision time.
    """

    def __init__(self, snapshot: Callable[[], bool]) -> None:
        self._snapshot = snapshot

    def check_person(self) -> DetectionResult:
        if self._snapshot():
            return DetectionResult(
                has_person=True,
                summary="移动视角在取物区域附近检测到人员停留",
            )
        return DetectionResult(
            has_person=False,
            summary="当前视野内未发现人员停留",
        )
