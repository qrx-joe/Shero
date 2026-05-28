const startBtn = document.querySelector("#startBtn");
const resetBtn = document.querySelector("#resetBtn");
const cameraBtn = document.querySelector("#cameraBtn");
const timeline = document.querySelector("#timeline");
const currentState = document.querySelector("#currentState strong");
const fixedViewBadge = document.querySelector("#fixedViewBadge");
const robotBadge = document.querySelector("#robotBadge");
const modeBadge = document.querySelector("#modeBadge");
const fixedViewText = document.querySelector("#fixedViewText");
const robotText = document.querySelector("#robotText");
const robotActionText = document.querySelector("#robotActionText");
const sceneCopy = document.querySelector("#sceneCopy");
const notificationToast = document.querySelector("#notificationToast");
const cameraPreview = document.querySelector("#cameraPreview");
const mobileViewFrame = document.querySelector("#mobileViewFrame");
const cameraHint = document.querySelector("#cameraHint");
const recordBadge = document.querySelector("#recordBadge");
const recordSource = document.querySelector("#recordSource");
const recordStart = document.querySelector("#recordStart");
const recordResult = document.querySelector("#recordResult");
const recordText = document.querySelector("#recordText");
const recordDownload = document.querySelector("#recordDownload");
const metadataDownload = document.querySelector("#metadataDownload");

let lastEventCount = -1;
let cameraStream = null;
let mediaRecorder = null;
let recordingChunks = [];
let missionStarted = false;
let recordSaved = false;
let recordSaving = false;

async function postJson(url, options = {}) {
  const response = await fetch(url, { method: "POST", ...options });
  return response.json();
}

async function getState() {
  const response = await fetch("/api/state");
  return response.json();
}

function renderState(state) {
  startBtn.disabled = state.running;
  modeBadge.textContent = state.robot_mode;
  currentState.textContent = state.current_message;
  robotBadge.textContent = state.current_robot_action_label;
  robotText.textContent = `动作：${state.current_robot_action_label}`;
  robotActionText.textContent = cameraStream ? "笔记本摄像头移动视角" : state.current_robot_action_label;

  updateSceneCopy(state.current_state);
  updateFixedView(state.current_state);
  updateRecordPanel(state);

  if (state.events.length !== lastEventCount) {
    lastEventCount = state.events.length;
    timeline.replaceChildren(...state.events.map(renderEvent));
    timeline.scrollTop = timeline.scrollHeight;
  }

  if (missionStarted && !recordSaved && !recordSaving && ["done", "error"].includes(state.current_state)) {
    completeMissionRecord(state);
  }
}

function renderEvent(event) {
  const item = document.createElement("li");
  item.className = event.level;

  const time = document.createElement("time");
  time.textContent = event.time;

  const text = document.createElement("p");
  text.textContent = event.message;

  item.append(time, text);
  return item;
}

function updateFixedView(current) {
  fixedViewBadge.textContent = "不可用";

  if (current === "fixed_view_checking") {
    fixedViewText.textContent = "正在检测实验场地是否存在可用固定视角。";
    return;
  }

  fixedViewText.textContent = "固定视角不可用：实验场地无门铃/猫眼接入。";
}

function updateRecordPanel(state) {
  if (!missionStarted) {
    recordBadge.textContent = "待开始";
    recordResult.textContent = "等待确认";
    return;
  }

  if (recordSaving) {
    recordBadge.textContent = "保存中";
  } else if (recordSaved) {
    recordBadge.textContent = "已保存";
  } else if (mediaRecorder?.state === "recording") {
    recordBadge.textContent = "记录中";
  } else {
    recordBadge.textContent = "记录任务日志";
  }

  recordSource.textContent = cameraStream ? "笔记本摄像头 + 任务日志" : "任务日志";

  if (state.current_state === "clear" || state.current_state === "suggestion" || state.current_state === "done") {
    recordResult.textContent = "当前视野内未发现人员停留";
  } else if (state.current_state === "person_found") {
    recordResult.textContent = "疑似有人停留";
  } else if (state.current_state === "error") {
    recordResult.textContent = "任务异常";
  }
}

function updateSceneCopy(current) {
  const copy = {
    waiting: "固定视角不可用时，系统调度机器狗作为移动感知节点，完成取物区域二次确认。",
    starting: "正在接管取物区域二次确认任务。",
    received: "用户发起取物区域确认任务，系统开始接管流程。",
    fixed_view_checking: "系统先检测现场是否存在可用固定视角。",
    fixed_view_unavailable: "实验场地无门铃/猫眼接入，固定视角标记为不可用。",
    switching_to_mobile: "系统不会假装有传感器，而是切换到移动确认视角。",
    dispatching: "系统正在调度机器狗作为移动感知节点。",
    moving_to_b: "机器狗从 A 点前往取物区域 B 点。",
    patrolling: "机器狗转向巡视取物区域、侧边盲区与通道方向。",
    person_found: "机器狗检测到取物区域附近疑似有人停留，建议暂不取物。",
    clear: "机器狗完成二次确认，当前视野内未发现人员停留。",
    suggestion: "用户可以取回物品，建议立即返回并关闭入口。",
    returning: "机器狗返回 A 点，任务进入收尾。",
    done: "取物区域二次确认结束，巡航记录已归档。",
    error: "任务异常，请切换 mock 模式或检查 Go2 适配器。",
  };
  sceneCopy.textContent = copy[current] ?? copy.waiting;
}

async function startCamera() {
  if (!navigator.mediaDevices?.getUserMedia) {
    setCameraError("当前浏览器不支持摄像头访问");
    return;
  }

  try {
    cameraStream = await openCameraStream();
    cameraPreview.srcObject = cameraStream;
    await cameraPreview.play();
    mobileViewFrame.classList.add("camera-active");
    mobileViewFrame.classList.remove("camera-error");
    cameraBtn.textContent = "关闭摄像头";
    cameraHint.textContent = "笔记本摄像头已作为移动视角";
    robotActionText.textContent = "笔记本摄像头移动视角";
  } catch (error) {
    setCameraError(`摄像头启用失败：${error.name || error.message}`);
  }
}

async function openCameraStream() {
  try {
    return await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 1280 }, height: { ideal: 720 } },
      audio: false,
    });
  } catch (error) {
    return navigator.mediaDevices.getUserMedia({ video: true, audio: false });
  }
}

function stopCamera() {
  if (cameraStream) {
    for (const track of cameraStream.getTracks()) {
      track.stop();
    }
  }
  cameraStream = null;
  cameraPreview.srcObject = null;
  mobileViewFrame.classList.remove("camera-active", "camera-error");
  cameraBtn.textContent = "启用摄像头";
  cameraHint.textContent = "可启用笔记本摄像头作为移动视角";
}

function setCameraError(message) {
  mobileViewFrame.classList.add("camera-error");
  cameraHint.textContent = message;
}

function startMissionRecord() {
  stopActiveRecorder();
  missionStarted = true;
  recordSaved = false;
  recordSaving = false;
  recordingChunks = [];
  recordDownload.classList.add("hidden");
  metadataDownload.classList.add("hidden");
  recordStart.textContent = new Date().toLocaleTimeString("zh-CN", { hour12: false });
  recordText.textContent = cameraStream
    ? "正在记录任务日志，并录制移动视角视频。"
    : "正在记录任务日志。启用摄像头后可同时保存移动视角视频。";

  if (!cameraStream || !window.MediaRecorder) {
    return;
  }

  const mimeType = MediaRecorder.isTypeSupported("video/webm;codecs=vp9")
    ? "video/webm;codecs=vp9"
    : "video/webm";
  const chunks = recordingChunks;
  mediaRecorder = new MediaRecorder(cameraStream, { mimeType });
  mediaRecorder.addEventListener("dataavailable", (event) => {
    if (event.data.size > 0) {
      chunks.push(event.data);
    }
  });
  mediaRecorder.start(500);
}

function stopActiveRecorder() {
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    try {
      mediaRecorder.stop();
    } catch (error) {
      // ignore — recorder may have already ended
    }
  }
  mediaRecorder = null;
}

async function completeMissionRecord() {
  recordSaving = true;
  recordBadge.textContent = "保存中";

  if (mediaRecorder?.state === "recording") {
    await new Promise((resolve) => {
      mediaRecorder.addEventListener("stop", resolve, { once: true });
      mediaRecorder.stop();
    });
  }

  const blob = recordingChunks.length
    ? new Blob(recordingChunks, { type: mediaRecorder?.mimeType || "video/webm" })
    : null;

  try {
    const result = await postJson("/api/recording", {
      headers: blob ? { "Content-Type": blob.type } : undefined,
      body: blob || undefined,
    });
    recordSaved = true;
    recordText.textContent = result.has_video
      ? "本次巡航视频和任务日志已保存。"
      : "本次任务日志已保存；未检测到摄像头视频。";

    if (result.video_url) {
      recordDownload.href = result.video_url;
      recordDownload.classList.remove("hidden");
    }
    if (result.metadata_url) {
      metadataDownload.href = result.metadata_url;
      metadataDownload.classList.remove("hidden");
    }
  } catch (error) {
    recordText.textContent = `巡航记录保存失败：${error}`;
  } finally {
    recordSaving = false;
    mediaRecorder = null;
    recordingChunks = [];
  }
}

async function refresh() {
  try {
    renderState(await getState());
  } catch (error) {
    currentState.textContent = `无法连接后端：${error}`;
  }
}

startBtn.addEventListener("click", async () => {
  startMissionRecord();
  await postJson("/api/start");
  await refresh();
});

resetBtn.addEventListener("click", async () => {
  stopActiveRecorder();
  recordingChunks = [];
  await postJson("/api/reset");
  lastEventCount = -1;
  missionStarted = false;
  recordSaving = false;
  recordSaved = false;
  recordBadge.textContent = "待开始";
  recordSource.textContent = "任务日志";
  recordStart.textContent = "未开始";
  recordResult.textContent = "等待确认";
  recordText.textContent = "启动任务后，系统会保存本次巡航任务日志；启用摄像头后会同时保存移动视角视频。";
  recordDownload.classList.add("hidden");
  metadataDownload.classList.add("hidden");
  showNotification();
  await refresh();
});

cameraBtn.addEventListener("click", async () => {
  if (cameraStream) {
    stopCamera();
    return;
  }
  await startCamera();
});

function showNotification() {
  notificationToast.classList.remove("hidden");
  setTimeout(() => notificationToast.classList.add("hidden"), 6000);
}

setTimeout(showNotification, 1500);

refresh();
setInterval(refresh, 500);
