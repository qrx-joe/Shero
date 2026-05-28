from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Callable

from app.robot.base import RobotController
from app.vision import PersonDetector


@dataclass(frozen=True)
class MissionEvent:
    state: str
    message: str
    level: str = "info"


Reporter = Callable[[MissionEvent], None]


def _load_pace_multiplier() -> float:
    raw = os.getenv("MISSION_PACE_MULTIPLIER", "1.0").strip()
    if not raw:
        return 1.0
    try:
        value = float(raw)
    except ValueError:
        return 1.0
    return max(0.0, value)


class DoorCheckMission:
    PACE: dict[str, float] = {
        "fixed_view_unavailable": 2.0,
        "switching_to_mobile": 2.0,
        "clear": 1.8,
        "suggestion": 1.8,
        "person_found": 1.8,
    }
    DEFAULT_PACE = 0.9

    def __init__(
        self,
        robot: RobotController,
        detector: PersonDetector,
        report: Reporter,
    ) -> None:
        self.robot = robot
        self.detector = detector
        self.report = report
        self._pace_multiplier = _load_pace_multiplier()

    def run(self) -> None:
        self._step("received", "已接收指令：帮我看看门外有没有人")
        self._step("fixed_view_checking", "正在检测固定视角状态")
        self._step("fixed_view_unavailable", "固定视角不可用：实验场地无门铃/猫眼接入")
        self._step("switching_to_mobile", "系统切换为机器狗移动确认流程")

        self._step("dispatching", "正在调度机器狗执行取物区域二次确认")
        self._step("moving_to_b", "机器狗前往取物区域 B 点")
        self.robot.go_to_b()

        self._step("patrolling", "机器狗正在巡视取物区域周围")
        self.robot.patrol()

        result = self.detector.check_person()
        if result.has_person:
            self._step("person_found", "发现取物区域附近疑似有人停留，建议暂不取物", "warning")
            self._step("returning", "机器狗返回 A 点")
            self.robot.return_to_a()
            self._step("done", "任务完成：请继续观察取物区域情况", "warning")
            return

        self._step("clear", f"机器狗已完成取物区域二次确认，{result.summary}")
        self._step("suggestion", "可以取回物品，建议立即返回并关闭入口")
        self._step("returning", "机器狗返回 A 点")
        self.robot.return_to_a()
        self._step("done", "任务完成：取物区域二次确认结束")

    def _step(self, state: str, message: str, level: str = "info") -> None:
        self.report(MissionEvent(state=state, message=message, level=level))
        time.sleep(self.PACE.get(state, self.DEFAULT_PACE) * self._pace_multiplier)
