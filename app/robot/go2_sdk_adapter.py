from __future__ import annotations

import json
import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.robot.base import RobotController


@dataclass(frozen=True)
class Go2AdapterConfig:
    dimos_cmd: tuple[str, ...]
    dimos_cwd: Path | None
    control_mode: str
    dry_run: bool
    timeout_seconds: float
    forward_meters: float
    return_meters: float
    left_degrees: float
    right_degrees: float
    velocity_x: float
    velocity_yaw: float
    forward_duration: float
    turn_duration: float
    return_duration: float
    tool_move_relative: str
    tool_move_velocity: str
    tool_sport: str
    stop_command: str
    param_forward: str
    param_left: str
    param_degrees: str
    param_velocity_x: str
    param_velocity_y: str
    param_velocity_yaw: str
    param_velocity_duration: str
    param_sport_command_name: str


class Go2SDKAdapter(RobotController):
    """Control a real Go2 through a running DimOS MCP-enabled Go2 blueprint.

    Expected macOS setup:
    1. Start DimOS first, for example:
       `uv run dimos run unitree-go2-agentic --robot-ip <GO2_IP>`
    2. Start this demo with `ROBOT_MODE=go2`.

    The default control mode uses DimOS `relative_move`, which is available in
    the Go2 UnitreeSkillContainer. A velocity mode is also available if the
    connected MCP server exposes a `move(x, y, yaw, duration)` tool.
    """

    def __init__(self, report_action) -> None:
        self._report_action = report_action
        self._config = self._load_config()

    def go_to_b(self) -> None:
        self._report_action("go2_forward", "Go2 前往取物区域 B 点")
        if self._config.control_mode == "velocity":
            self._call_mcp(
                self._config.tool_move_velocity,
                {
                    self._config.param_velocity_x: self._config.velocity_x,
                    self._config.param_velocity_y: 0.0,
                    self._config.param_velocity_yaw: 0.0,
                    self._config.param_velocity_duration: self._config.forward_duration,
                },
            )
            return
        self._call_mcp(
            self._config.tool_move_relative,
            {
                self._config.param_forward: self._config.forward_meters,
                self._config.param_left: 0.0,
                self._config.param_degrees: 0.0,
            },
        )

    def patrol(self) -> None:
        self._report_action("go2_turn_left", "Go2 向左巡视侧边盲区")
        self._turn(self._config.left_degrees)
        self._report_action("go2_turn_right", "Go2 向右巡视通道方向")
        self._turn(self._config.right_degrees)
        self._report_action("go2_turn_center", "Go2 回正视角")
        self._turn(self._config.left_degrees)

    def return_to_a(self) -> None:
        self._report_action("go2_backward", "Go2 返回 A 点")
        if self._config.control_mode == "velocity":
            self._call_mcp(
                self._config.tool_move_velocity,
                {
                    self._config.param_velocity_x: -abs(self._config.velocity_x),
                    self._config.param_velocity_y: 0.0,
                    self._config.param_velocity_yaw: 0.0,
                    self._config.param_velocity_duration: self._config.return_duration,
                },
            )
            return
        self._call_mcp(
            self._config.tool_move_relative,
            {
                self._config.param_forward: -abs(self._config.return_meters),
                self._config.param_left: 0.0,
                self._config.param_degrees: 0.0,
            },
        )

    def stop(self) -> None:
        self._report_action("go2_stop", "Go2 停止/保持平衡站立")
        if self._config.control_mode == "velocity":
            self._call_mcp(
                self._config.tool_move_velocity,
                {
                    self._config.param_velocity_x: 0.0,
                    self._config.param_velocity_y: 0.0,
                    self._config.param_velocity_yaw: 0.0,
                    self._config.param_velocity_duration: 0.2,
                },
            )
            return
        self._call_mcp(
            self._config.tool_sport,
            {self._config.param_sport_command_name: self._config.stop_command},
        )

    def _turn(self, degrees: float) -> None:
        if self._config.control_mode == "velocity":
            yaw = self._config.velocity_yaw if degrees > 0 else -abs(self._config.velocity_yaw)
            self._call_mcp(
                self._config.tool_move_velocity,
                {
                    self._config.param_velocity_x: 0.0,
                    self._config.param_velocity_y: 0.0,
                    self._config.param_velocity_yaw: yaw,
                    self._config.param_velocity_duration: self._config.turn_duration,
                },
            )
            return
        self._call_mcp(
            self._config.tool_move_relative,
            {
                self._config.param_forward: 0.0,
                self._config.param_left: 0.0,
                self._config.param_degrees: degrees,
            },
        )

    def _call_mcp(self, tool_name: str, args: dict[str, Any]) -> None:
        json_args = json.dumps(args, ensure_ascii=False)
        command = [*self._config.dimos_cmd, "mcp", "call", tool_name, "--json-args", json_args]
        display = " ".join(shlex.quote(part) for part in command)

        if self._config.dry_run:
            self._report_action("go2_dry_run", f"DRY RUN: {display}")
            return

        self._report_action("go2_mcp_call", f"调用 DimOS MCP：{tool_name}")
        try:
            completed = subprocess.run(
                command,
                cwd=str(self._config.dimos_cwd) if self._config.dimos_cwd else None,
                text=True,
                capture_output=True,
                timeout=self._config.timeout_seconds,
                check=True,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                "找不到 DimOS 命令。请设置 DIMOS_CMD，例如："
                "DIMOS_CMD='uv run dimos'，并确认 macOS 上已安装/同步 DimOS。"
            ) from exc
        except subprocess.CalledProcessError as exc:
            details = (exc.stderr or exc.stdout or str(exc)).strip()
            raise RuntimeError(f"DimOS MCP 调用失败：{details}") from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"DimOS MCP 调用超时：{display}") from exc

        output = (completed.stdout or completed.stderr).strip()
        if output:
            self._report_action("go2_mcp_result", output[-240:])

    @classmethod
    def _load_config(cls) -> Go2AdapterConfig:
        control_mode = os.getenv("GO2_CONTROL_MODE", "relative_move").strip().lower()
        if control_mode not in {"relative_move", "velocity"}:
            raise ValueError("GO2_CONTROL_MODE must be 'relative_move' or 'velocity'")

        dimos_cwd_raw = os.getenv("DIMOS_CWD", "").strip()
        return Go2AdapterConfig(
            dimos_cmd=tuple(shlex.split(os.getenv("DIMOS_CMD", "uv run dimos"))),
            dimos_cwd=Path(dimos_cwd_raw).expanduser() if dimos_cwd_raw else None,
            control_mode=control_mode,
            dry_run=os.getenv("GO2_DRY_RUN", "0").strip().lower() in {"1", "true", "yes"},
            timeout_seconds=cls._float_env("GO2_MCP_TIMEOUT", 120.0),
            forward_meters=cls._float_env("GO2_FORWARD_METERS", 0.8),
            return_meters=cls._float_env("GO2_RETURN_METERS", 0.8),
            left_degrees=cls._float_env("GO2_LEFT_DEGREES", 45.0),
            right_degrees=cls._float_env("GO2_RIGHT_DEGREES", -90.0),
            velocity_x=cls._float_env("GO2_VELOCITY_X", 0.25),
            velocity_yaw=cls._float_env("GO2_VELOCITY_YAW", 0.6),
            forward_duration=cls._float_env("GO2_FORWARD_DURATION", 2.0),
            turn_duration=cls._float_env("GO2_TURN_DURATION", 1.0),
            return_duration=cls._float_env("GO2_RETURN_DURATION", 2.0),
            tool_move_relative=os.getenv("GO2_TOOL_MOVE_RELATIVE", "relative_move").strip(),
            tool_move_velocity=os.getenv("GO2_TOOL_MOVE_VELOCITY", "move").strip(),
            tool_sport=os.getenv("GO2_TOOL_SPORT", "execute_sport_command").strip(),
            stop_command=os.getenv("GO2_STOP_COMMAND", "BalanceStand").strip(),
            param_forward=os.getenv("GO2_PARAM_FORWARD", "forward").strip(),
            param_left=os.getenv("GO2_PARAM_LEFT", "left").strip(),
            param_degrees=os.getenv("GO2_PARAM_DEGREES", "degrees").strip(),
            param_velocity_x=os.getenv("GO2_PARAM_VELOCITY_X", "x").strip(),
            param_velocity_y=os.getenv("GO2_PARAM_VELOCITY_Y", "y").strip(),
            param_velocity_yaw=os.getenv("GO2_PARAM_VELOCITY_YAW", "yaw").strip(),
            param_velocity_duration=os.getenv("GO2_PARAM_VELOCITY_DURATION", "duration").strip(),
            param_sport_command_name=os.getenv("GO2_PARAM_SPORT_COMMAND", "command_name").strip(),
        )

    @staticmethod
    def _float_env(name: str, default: float) -> float:
        raw = os.getenv(name)
        if raw is None or raw.strip() == "":
            return default
        try:
            return float(raw)
        except ValueError as exc:
            raise ValueError(f"{name} must be a number") from exc
