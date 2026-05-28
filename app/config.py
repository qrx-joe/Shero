from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    host: str = "127.0.0.1"
    port: int = 8000
    robot_mode: str = "mock"


def load_config() -> AppConfig:
    return AppConfig(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        robot_mode=os.getenv("ROBOT_MODE", "mock").lower(),
    )
