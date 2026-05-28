#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Default to real Go2 because the script name says so, but require explicit
# acknowledgement before we actually move a robot. To run mock mode just call
#   uv run python -m app.main
# directly — this script is for the live-Go2 path.
export ROBOT_MODE="${ROBOT_MODE:-go2}"
export GO2_CONTROL_MODE="${GO2_CONTROL_MODE:-relative_move}"
export DIMOS_CMD="${DIMOS_CMD:-uv run dimos}"
export DIMOS_CWD="${DIMOS_CWD:-$HOME/dimos}"
export PORT="${PORT:-8000}"

# Optional overrides for a borrowed Mac whose DimOS exposes different tool names
# or parameter keys. Defaults match Go2-Door-Check-Demo-Plan.md.
#
#   export GO2_TOOL_MOVE_RELATIVE=relative_move
#   export GO2_TOOL_MOVE_VELOCITY=move
#   export GO2_TOOL_SPORT=execute_sport_command
#   export GO2_STOP_COMMAND=BalanceStand
#   export GO2_PARAM_FORWARD=forward
#   export GO2_PARAM_LEFT=left
#   export GO2_PARAM_DEGREES=degrees
#   export GO2_PARAM_VELOCITY_X=x
#   export GO2_PARAM_VELOCITY_Y=y
#   export GO2_PARAM_VELOCITY_YAW=yaw
#   export GO2_PARAM_VELOCITY_DURATION=duration
#   export GO2_PARAM_SPORT_COMMAND=command_name
#
# Slow the mission so the audience can read every transition:
#   export MISSION_PACE_MULTIPLIER=1.4
#
# Force the "person found" branch for rehearsal:
#   export FORCE_PERSON_FOUND=1

if [ "${ROBOT_MODE}" = "go2" ] \
   && [ "${GO2_DRY_RUN:-0}" != "1" ] \
   && [ "${ACK_GO2_LIVE:-0}" != "1" ]; then
  cat <<'WARN' >&2

================================================================
  你正准备直接控制真实 Go2 (ROBOT_MODE=go2, GO2_DRY_RUN=0)
================================================================
  第一次在这台 macOS 上跑, 请先做这两件事:

    1) 在另一个终端确认 DimOS MCP 工具名:
         cd "$DIMOS_CWD" && uv run dimos mcp list-tools

    2) 用 dry-run 模式启动 demo, 看命令构造是否正确:
         GO2_DRY_RUN=1 ./scripts/start_macos_go2.sh

  确认无误后, 显式承认并重新启动:
         ACK_GO2_LIVE=1 ./scripts/start_macos_go2.sh
================================================================
WARN
  exit 1
fi

uv run python -m app.main
