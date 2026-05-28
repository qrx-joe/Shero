from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.mission.door_check import DoorCheckMission, MissionEvent
from app.robot.go2_sdk_adapter import Go2SDKAdapter
from app.robot.mock_go2 import MockGo2Controller
from app.vision.browser_detector import BrowserPersonDetector

EVENT_CAP = 200


@dataclass
class DemoState:
    running: bool = False
    robot_mode: str = "mock"
    current_state: str = "waiting"
    current_message: str = "等待指令"
    current_level: str = "info"
    current_robot_action: str = "idle"
    current_robot_action_label: str = "待命"
    person_seen: bool = False
    last_person_seen_at: str = ""
    events: list[dict] = field(default_factory=list)


class DemoRuntime:
    def __init__(self, robot_mode: str) -> None:
        self._lock = threading.Lock()
        self._state = DemoState(robot_mode=robot_mode)
        self._robot_mode = robot_mode

    def snapshot(self) -> dict:
        with self._lock:
            return asdict(self._state)

    def reset(self) -> None:
        with self._lock:
            self._state.running = False
            self._state.current_state = "waiting"
            self._state.current_message = "等待指令"
            self._state.current_level = "info"
            self._state.current_robot_action = "idle"
            self._state.current_robot_action_label = "待命"
            self._state.person_seen = False
            self._state.last_person_seen_at = ""
            self._state.events.clear()

    def start(self) -> tuple[bool, str]:
        with self._lock:
            if self._state.running:
                return False, "任务正在执行中"
            self._state.running = True
            self._state.current_state = "starting"
            self._state.current_message = "正在启动门外二次确认任务"
            self._state.current_level = "info"
            self._state.person_seen = False
            self._state.last_person_seen_at = ""
            self._state.events.clear()

        worker = threading.Thread(target=self._run_mission, daemon=True)
        worker.start()
        return True, "任务已启动"

    def _run_mission(self) -> None:
        try:
            robot = self._build_robot()
            mission = DoorCheckMission(
                robot=robot,
                detector=BrowserPersonDetector(self._person_seen_snapshot),
                report=self._report_event,
            )
            mission.run()
        except Exception as exc:
            self._report_event(
                MissionEvent(
                    state="error",
                    message=f"任务执行失败：{exc}",
                    level="error",
                )
            )
        finally:
            with self._lock:
                self._state.running = False

    def _build_robot(self):
        if self._robot_mode == "go2":
            return Go2SDKAdapter(self._report_robot_action)
        return MockGo2Controller(self._report_robot_action)

    def _person_seen_snapshot(self) -> bool:
        with self._lock:
            return self._state.person_seen

    def record_vision_event(self, payload: dict) -> dict:
        has_person = bool(payload.get("has_person"))
        try:
            confidence = float(payload.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        bbox = payload.get("bbox")

        if not has_person:
            return {"ok": True, "person_seen": False}

        timestamp = time.strftime("%H:%M:%S")
        record = {
            "state": "person_detected",
            "message": f"移动视角检测到人员停留（置信度 {confidence:.0%}）",
            "level": "warning",
            "time": timestamp,
        }
        with self._lock:
            if not self._state.running:
                return {"ok": True, "person_seen": self._state.person_seen, "ignored": True}
            already_seen = self._state.person_seen
            self._state.person_seen = True
            self._state.last_person_seen_at = timestamp
            if not already_seen:
                self._state.events.append(record)
                if len(self._state.events) > EVENT_CAP:
                    self._state.events = self._state.events[-EVENT_CAP:]
        return {
            "ok": True,
            "person_seen": True,
            "first_trigger": not already_seen,
            "confidence": confidence,
            "bbox": bbox,
        }

    def _report_event(self, event: MissionEvent) -> None:
        record = {
            "state": event.state,
            "message": event.message,
            "level": event.level,
            "time": time.strftime("%H:%M:%S"),
        }
        with self._lock:
            self._state.current_state = event.state
            self._state.current_message = event.message
            self._state.current_level = event.level
            self._state.events.append(record)
            if len(self._state.events) > EVENT_CAP:
                self._state.events = self._state.events[-EVENT_CAP:]

    def _report_robot_action(self, action: str, label: str) -> None:
        record = {
            "state": f"robot_{action}",
            "message": f"机器狗动作：{label}",
            "level": "robot",
            "time": time.strftime("%H:%M:%S"),
        }
        with self._lock:
            self._state.current_robot_action = action
            self._state.current_robot_action_label = label
            self._state.events.append(record)
            if len(self._state.events) > EVENT_CAP:
                self._state.events = self._state.events[-EVENT_CAP:]


def json_response(handler, status: int, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def save_recording_response(handler, runtime: DemoRuntime, recordings_dir: Path) -> None:
    recordings_dir.mkdir(parents=True, exist_ok=True)

    content_length = int(handler.headers.get("Content-Length", "0") or "0")
    content_type = handler.headers.get("Content-Type", "application/octet-stream")
    payload = handler.rfile.read(content_length) if content_length > 0 else b""

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    record_id = f"door-check-{stamp}-{uuid4().hex[:8]}"
    metadata = {
        "record_id": record_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "content_type": content_type,
        "has_video": bool(payload),
        "mission": runtime.snapshot(),
    }

    video_url = None
    if payload:
        video_name = f"{record_id}.webm"
        (recordings_dir / video_name).write_bytes(payload)
        video_url = f"/recordings/{video_name}"
        metadata["video_file"] = video_name
        metadata["video_url"] = video_url

    metadata_name = f"{record_id}.json"
    (recordings_dir / metadata_name).write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    json_response(
        handler,
        201,
        {
            "ok": True,
            "record_id": record_id,
            "has_video": bool(payload),
            "video_url": video_url,
            "metadata_url": f"/recordings/{metadata_name}",
        },
    )
