from __future__ import annotations

import os

from app.vision import DetectionResult


class MockPersonDetector:
    def check_person(self) -> DetectionResult:
        force_person = os.getenv("FORCE_PERSON_FOUND", "0").strip().lower() in {"1", "true", "yes"}
        if force_person:
            return DetectionResult(
                has_person=True,
                summary="发现取物区域附近疑似有人停留",
            )
        return DetectionResult(
            has_person=False,
            summary="当前视野内未发现人员停留",
        )
