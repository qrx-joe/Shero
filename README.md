# Go2 取物区域二次确认 Demo

> 固定视角不可用时，系统调度机器狗或移动视角完成取物区域二次确认，并保存巡航记录。

本项目用于演示一个面向“取物前安全确认”的家庭操作系统场景：实验场地没有真实门铃/猫眼接入时，系统不会伪造固定摄像头，而是将固定视角标记为不可用，并切换到移动确认流程。移动视角可以来自 Unitree Go2，也可以在无机器狗时使用笔记本摄像头完成流程验证。

---

## 项目背景

原始场景是“用户收到外卖通知后，不直接去取物，而是先让系统确认取物区域附近是否有人停留”。由于当前演示环境可能是室外或室内实验场地，没有真实门铃/猫眼，因此本项目采用更诚实的降级策略：

```text
固定视角：不可用
处理策略：切换为移动视角确认
移动来源：Go2 / 笔记本摄像头
输出结果：当前视野内未发现人员停留
记录归档：保存任务日志，可选保存移动视角视频
```

给评委的说明话术：

> 当前实验场地没有真实门铃/猫眼接入，所以我们在系统中把固定视角标记为不可用。系统不会假装有传感器，而是自动切换到机器狗移动确认流程，由 Go2 前往取物区域完成二次巡检，并保存本次巡航记录用于事后复核。

---

## 技术栈

| 层级 | 技术 | 版本/说明 |
|---|---|---|
| 语言 | Python | `>=3.11` |
| 包管理 | uv | 项目规范要求，仅使用 `uv` |
| 后端服务 | Python 标准库 `http.server` | 无额外 Python 依赖 |
| 前端 | HTML / CSS / JavaScript | 原生实现，无构建步骤 |
| 摄像头 | `getUserMedia` | 浏览器本地摄像头预览 |
| 视频记录 | `MediaRecorder` | 保存 `.webm` 移动视角视频 |
| 任务日志 | JSON | 保存 `.json` 巡航记录 |
| Go2 控制 | DimOS MCP CLI | 通过 `relative_move` 等 MCP 工具控制 |

---

## 核心功能

- 固定视角不可用检测：明确展示“实验场地无门铃/猫眼接入”，避免伪造传感器。
- 移动确认流程：系统触发 `door_check` 任务，依次执行前往 B 点、巡视、返回 A 点。
- 无机器狗兜底演示：使用 `MockGo2Controller` 模拟 Go2 动作，完整跑通产品闭环。
- 笔记本摄像头移动视角：没有 Go2 时，可启用笔记本摄像头作为移动视角进行演示。
- 巡航记录保存：任务结束后保存 JSON 日志；启用摄像头时同时保存 `.webm` 视频。
- 真机适配边界：任务流程依赖 `RobotController` 抽象，真实 Go2 控制集中在 `go2_sdk_adapter.py`。

---

## 演示流程

1. 用户收到通知：“外卖已到取物区域。”
2. 用户发起指令：“帮我看看门外有没有人。”
3. 系统检测固定视角状态。
4. 系统显示：`固定视角不可用：实验场地无门铃/猫眼接入`。
5. 系统切换为移动确认流程。
6. 机器狗或 mock 控制器前往取物区域 B 点。
7. 移动视角巡视侧边盲区和通道方向。
8. 系统输出：`当前视野内未发现人员停留`。
9. 系统建议：`可以取回物品，建议立即返回并关闭入口`。
10. 系统保存本次巡航任务记录。

---

## 本地运行

进入项目目录：

```powershell
cd D:\LINUX\go2-door-check-demo
```

创建项目内虚拟环境：

```powershell
uv venv
```

启动服务：

```powershell
uv run python -m app.main
```

打开页面：

```text
http://127.0.0.1:8000
```

如果 Windows 上 `uv` 访问用户缓存目录失败，可以使用项目内启动脚本：

```powershell
powershell -ExecutionPolicy Bypass -File D:\LINUX\go2-door-check-demo\scripts\start_windows.ps1
```

---

## 无 Go2 测试方式

没有机器狗也可以完整跑通 demo。

```powershell
$env:ROBOT_MODE="mock"
uv run python -m app.main
```

测试步骤：

1. 打开 `http://127.0.0.1:8000`。
2. 点击中间面板的 `启用摄像头`。
3. 在浏览器权限弹窗中允许摄像头。
4. 点击 `启动移动确认`。
5. 等待任务跑到完成。
6. 在左侧 `任务巡航记录` 中下载视频记录或任务日志。

说明：

- 启用摄像头后，系统会保存 `.webm` 视频和 `.json` 任务日志。
- 未启用摄像头时，系统仍会保存 `.json` 任务日志。
- 摄像头权限在 `localhost` / `127.0.0.1` 下可用；如果没有画面，检查浏览器摄像头权限和摄像头是否被其他软件占用。

保存目录：

```text
D:\LINUX\go2-door-check-demo\recordings
```

---

## macOS 连接 Go2

在连接 Go2 的 Mac 上，先确认 mock 模式能跑：

```bash
cd go2-door-check-demo
uv venv
uv sync
export ROBOT_MODE=mock
uv run python -m app.main
```

确认页面正常后，启动 DimOS Go2 agentic blueprint：

```bash
cd ~/dimos
uv run dimos run unitree-go2-agentic --robot-ip <GO2_IP>
```

另开一个终端启动本 demo：

```bash
cd go2-door-check-demo
export ROBOT_MODE=go2
export DIMOS_CWD="$HOME/dimos"
export DIMOS_CMD="uv run dimos"
export GO2_CONTROL_MODE=relative_move
uv run python -m app.main
```

打开：

```text
http://127.0.0.1:8000
```

也可以使用脚本：

```bash
chmod +x scripts/start_macos_go2.sh
ACK_GO2_LIVE=1 ./scripts/start_macos_go2.sh
```

---

## 真机安全检查

正式让 Go2 动之前，必须先做小步测试：

```bash
cd ~/dimos
uv run dimos mcp list-tools
uv run dimos mcp call relative_move --json-args '{"forward": 0.2, "left": 0, "degrees": 0}'
```

确认 Go2 只前进约 20 cm 后，再运行完整 demo。

如果要先检查命令构造，不让机器狗移动：

```bash
export ROBOT_MODE=go2
export GO2_DRY_RUN=1
uv run python -m app.main
```

常用环境变量：

```bash
ROBOT_MODE=go2
DIMOS_CWD=$HOME/dimos
DIMOS_CMD="uv run dimos"
GO2_CONTROL_MODE=relative_move
GO2_FORWARD_METERS=0.8
GO2_RETURN_METERS=0.8
GO2_LEFT_DEGREES=45
GO2_RIGHT_DEGREES=-90
GO2_MCP_TIMEOUT=120
MISSION_PACE_MULTIPLIER=1.0
```

如果借来的 Mac 上 DimOS 工具名不同，可以覆盖工具名：

```bash
GO2_TOOL_MOVE_RELATIVE=relative_move
GO2_TOOL_MOVE_VELOCITY=move
GO2_TOOL_SPORT=execute_sport_command
GO2_STOP_COMMAND=BalanceStand
```

---

## 项目结构

```text
go2-door-check-demo/
  app/
    main.py                    # HTTP 服务和静态资源
    config.py                  # 环境变量配置
    api/
      routes.py                # 任务状态、记录保存 API
    mission/
      door_check.py            # 取物区域二次确认任务流
    robot/
      base.py                  # 机器人控制接口
      mock_go2.py              # 本机 mock 控制器
      go2_sdk_adapter.py       # DimOS MCP 真机适配器
    vision/
      mock_detector.py         # 模拟人员检测结果
    web/
      index.html               # Demo 页面
      style.css                # 页面样式
      app.js                   # 前端状态轮询、摄像头、录制逻辑
  recordings/                  # 巡航视频和任务日志输出目录
  scripts/
    start_windows.ps1          # Windows 启动脚本
    start_macos_go2.sh         # macOS Go2 启动脚本
  pyproject.toml
```

---

## 关键设计决策

- 不伪造门铃/猫眼：实验场地没有固定视角时，直接标记不可用，避免演示逻辑被评委质疑。
- 任务流和硬件控制解耦：`DoorCheckMission` 只依赖 `RobotController`，避免 Go2 SDK 变化牵连业务流程。
- mock 优先：没有真机时也能验证系统闭环，降低硬件不可用带来的演示风险。
- 记录优先于口头说明：巡航日志和移动视角视频能证明系统确实完成过一次确认任务。
- 安全文案不绝对化：统一使用“当前视野内未发现人员停留”，不承诺“绝对安全”。

---

## 演示话术

推荐说法：

```text
当前实验场地没有真实门铃/猫眼接入，所以系统不会假装存在固定摄像头。
它会把固定视角标记为不可用，并自动切换到移动确认流程。
移动视角可以来自 Go2，也可以在无真机时用笔记本摄像头模拟。
任务结束后，系统会保存巡航日志和可选的视频记录，便于事后复核。
```

避免说法：

```text
系统已经确认绝对安全。
```

更稳妥的结果文案：

```text
当前视野内未发现人员停留，可以取回物品，建议立即返回并关闭入口。
```

---

## 当前限制

- 人员检测目前是模拟结果，尚未接入真实视觉模型。
- Go2 真机控制依赖 Mac 上的 DimOS MCP 服务。
- 浏览器录制视频使用 `MediaRecorder`，输出格式通常为 `.webm`。
- 巡航记录保存到本地项目目录，不包含用户系统级权限管理。

