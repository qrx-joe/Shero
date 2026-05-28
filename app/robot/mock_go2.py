from __future__ import annotations

import time

from app.robot.base import RobotController


class MockGo2Controller(RobotController):
    def __init__(self, report_action) -> None:
        self._report_action = report_action

    def go_to_b(self) -> None:
        self._move("forward", "前进到取物区域 B 点", 1.2)
        self.stop()

    def patrol(self) -> None:
        self._move("turn_left", "向左巡视侧边盲区", 0.8)
        self._move("turn_right", "向右巡视通道方向", 1.2)
        self._move("turn_center", "回正视角", 0.8)
        self.stop()

    def return_to_a(self) -> None:
        self._move("backward", "返回 A 点", 1.2)
        self.stop()

    def stop(self) -> None:
        self._report_action("stop", "停止移动")
        time.sleep(0.25)

    def _move(self, action: str, label: str, seconds: float) -> None:
        self._report_action(action, label)
        time.sleep(seconds)
