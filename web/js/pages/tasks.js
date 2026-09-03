"use strict";

import {
  createTask,
  getMonitorTargets,
  getRun,
  getRunFileText,
  getTasks,
  resumeTaskRequest,
} from "../api.js";
import { appState, allRunSnapshots, clearProductSelection } from "../state.js";
import { $, escapeHtml, formatDate, monitorTargetPresentation, showToast, taskPresentation } from "../utils.js";

let hooks = {
  renderApp: () => {},
  refreshProducts: async () => {},
  activateView: () => {},
  targetsChanged: () => {},
};

export function configureTaskPage(overrides) {
  hooks = { ...hooks, ...overrides };
}

function flowData(stats, stage = appState.current?.task?.stage) {
  const selected = stats.selectedProducts;
  const stageOrder = {
    initializing: 0,
    searching: 0,
    manual_action_required: 0,
    collecting_details: 2,
    processing_ocr_analysis: 4,
    collection_completed: 6,
    completed: 6,
    completed_with_errors: 6,
    interrupted: -1,
    failed: -1,
  };
  const currentIndex = stageOrder[stage] ?? 0;
  const stateFor = index => {
    if (["failed", "interrupted"].includes(stage)) {
      if (index === Math.max(currentIndex, 0)) return "current";
      return index < currentIndex ? "done" : "pending";
    }
    if (index < currentIndex || currentIndex >= 6) return "done";
    return index === currentIndex || (currentIndex === 4 && index === 5) ? "current" : "pending";
  };
  return [
    { label: "搜索商品", count: `发现 ${stats.searchRaw}`, state: stateFor(0) },
    { label: "商品去重", count: `入选 ${selected}`, state: stateFor(1) },
    { label: "详情采集", count: `${stats.detailCollectedProducts}/${selected}`, state: stateFor(2) },
    { label: "原图保存", count: `${stats.originalImages} 张`, state: stateFor(3) },
    { label: "OCR识别", count: `完成 ${stats.analyzedProducts}/${selected}`, state: stateFor(4) },
    { label: "规则分析", count: `完成 ${stats.analyzedProducts}/${selected}`, state: stateFor(5) },
  ];
}

function renderFlow(target) {
  if (!target || !appState.current?.statistics) return;
  target.innerHTML = flowData(appState.current.statistics).map((step, index) => `
    <div class="process-step ${step.state}">
      <div class="process-dot">${step.state === "done" ? "✓" : index + 1}</div>
      <div class="process-label">${escapeHtml(step.label)}</div>
      <div class="process-count">${escapeHtml(step.count)}</div>
    </div>`).join("");
}

function renderDiscoveryDiagnostics() {
  const card = $("#discoveryDiagnostics");
  const discovery = appState.current?.discovery;
  card.hidden = !discovery;
  if (!discovery) return;
  const summaries = [
    ["搜索词命中", discovery.rawHits || 0],
    ["去重后候选", discovery.uniqueCandidates || 0],
    ["进入详情采集", discovery.selectedForDetail || 0],
  ];
  $("#discoverySummary").innerHTML = summaries.map(([label, value]) => `<div><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join("");
  $("#discoveryQueryBody").innerHTML = (discovery.queryResults || []).map((item, index) => `<tr><td>${escapeHtml(item.order || index + 1)}</td><td>${escapeHtml(item.query_text || "—")}</td><td>${escapeHtml(item.candidate_count || 0)}</td><td>${escapeHtml(item.raw_card_count || 0)}</td><td>${escapeHtml(item.stop_reason || "—")}</td></tr>`).join("");
}

function selectedMonitorTarget() {
  const targetId = $("#monitorTargetInput")?.value;
  return appState.monitorTargets.find(item => item.target_id === targetId) || null;
}

export function renderMonitorTargetOptions(preferredTargetId = "") {
  const select = $("#monitorTargetInput");
  if (!select) return;
  select.innerHTML = appState.monitorTargets.map(item => {
    const kind = monitorTargetPresentation(item);
    return `<option value="${escapeHtml(item.target_id)}">${escapeHtml(item.standard_name)} · ${kind.label}</option>`;
  }).join("");
  if (preferredTargetId && appState.monitorTargets.some(item => item.target_id === preferredTargetId)) {
    select.value = preferredTargetId;
  }
  const target = selectedMonitorTarget();
  $("#monitorQueryPreview").innerHTML = target
    ? (target.queries || []).filter(item => item.enabled).map(item => `<span>${escapeHtml(item.query_text)}</span>`).join("")
    : "暂无可用监测对象";
}

export function syncTaskMode() {
  const monitor = $("#taskModeInput").value === "monitor";
  $("#quickTaskFields").hidden = monitor;
  $("#monitorTaskFields").hidden = !monitor;
  if (monitor) renderMonitorTargetOptions($("#monitorTargetInput").value);
}

export async function loadMonitorTargets() {
  const payload = await getMonitorTargets();
  appState.monitorTargets = payload.targets || [];
  renderMonitorTargetOptions();
  hooks.targetsChanged();
}

function setTaskFormMessage(message, tone = "", source = "user") {
  const target = $("#taskFormMessage");
  target.textContent = message || "";
  target.className = `task-form-message ${tone}`.trim();
  target.dataset.source = source;
}

function syncTaskFormState() {
  const activeMeta = appState.runs.find(item => item.runtime?.active);
  const active = Boolean(activeMeta || appState.current?.runtime?.active);
  $("#startTaskButton").disabled = active;
  ["#taskModeInput", "#taskKeywordInput", "#candidateLimitInput", "#monitorTargetInput", "#perQueryCandidateLimitInput", "#detailLimitInput"].forEach(selector => {
    $(selector).disabled = active;
  });
  if (active) {
    const task = appState.current?.runtime?.active ? appState.current.task : activeMeta?.task;
    setTaskFormMessage(task?.message || "采集任务正在后台运行", "", "runtime");
  } else if ($("#taskFormMessage").dataset.source === "runtime") {
    setTaskFormMessage("", "", "user");
  }
}

export function renderTasksPage() {
  const snapshots = appState.runs.length ? appState.runs : allRunSnapshots();
  const stateCounts = { running: 0, waiting: 0, completed: 0, failed: 0 };
  snapshots.forEach(snapshot => {
    const stage = snapshot.task?.stage;
    if (stage === "completed") stateCounts.completed += 1;
    else if (stage === "failed" || stage === "completed_with_errors") stateCounts.failed += 1;
    else if (["searching", "collecting_details", "processing_ocr_analysis", "manual_action_required", "initializing"].includes(stage) && snapshot.runtime?.active) stateCounts.running += 1;
    else stateCounts.waiting += 1;
  });
  const stateCards = [
    ["▶", "进行中", stateCounts.running, "green"],
    ["◷", "待继续", stateCounts.waiting, "orange"],
    ["✓", "已完成", stateCounts.completed, "blue"],
    ["!", "失败", stateCounts.failed, "red"],
  ];
  $("#taskStateOverview").innerHTML = stateCards.map(([icon, label, count, tone]) => `<div class="task-state-item"><span class="task-state-icon ${tone}">${icon}</span><div><span>${label}</span><strong>${count}</strong></div></div>`).join("");
  $("#taskRecordBody").innerHTML = snapshots.slice(0, 8).map(snapshot => {
    const stats = snapshot.statistics;
    const status = taskPresentation(snapshot);
    const total = Math.max(stats.selectedProducts || 0, 1);
    const value = stats.analyzedProducts || 0;
    const percent = Math.min(100, Math.round(value / total * 100));
    const createdAt = snapshot.runtime?.createdAt || snapshot.generatedAt;
    const resume = snapshot.runtime?.resumable ? `<button class="text-button" data-resume-task="${escapeHtml(snapshot.task.id)}">恢复</button>` : "";
    const request = snapshot.runtime?.request || {};
    const queryLabel = request.taskType === "monitor"
      ? (request.searchQueries || []).map(item => item.query_text).join("、")
      : snapshot.task.keyword;
    const taskLabel = request.taskType === "monitor"
      ? `${request.targetName || snapshot.task.keyword}监测任务`
      : `${snapshot.task.keyword || "未命名"}采集任务`;
    return `<tr><td>${escapeHtml(taskLabel)}<small>${escapeHtml(snapshot.task.id)}</small></td><td>${escapeHtml(queryLabel || "—")}</td><td><span class="table-tag ${status.tone}">${status.label}</span></td><td class="progress-cell"><span>${value} / ${stats.selectedProducts}</span><div class="progress-track"><i style="width:${percent}%"></i></div></td><td>${escapeHtml(formatDate(createdAt))}</td><td><button class="text-button" data-open-run="${escapeHtml(snapshot.task.id)}">查看</button>${resume}</td></tr>`;
  }).join("");
  renderCurrentTaskSummary();
  renderFlow($("#taskFlow"));
  renderDiscoveryDiagnostics();
  syncTaskFormState();
}

export async function loadRunLog() {
  if (!appState.current?.task?.id) {
    $("#logContent").textContent = "暂无运行日志。";
    return;
  }
  try {
    const text = await getRunFileText(appState.current.task.id, "run.log");
    const lines = text.trim().split(/\r?\n/);
    $("#logContent").textContent = lines.slice(-90).join("\n") || "日志为空。";
  } catch (_) {
    $("#logContent").textContent = "当前运行日志暂时无法读取。";
  }
}

function upsertRunMeta(snapshot) {
  const meta = {
    id: snapshot.task.id,
    generatedAt: snapshot.generatedAt,
    task: snapshot.task,
    statistics: snapshot.statistics,
    runtime: snapshot.runtime || {},
  };
  appState.runs = [meta, ...appState.runs.filter(item => item.id !== meta.id)]
    .sort((a, b) => String(b.generatedAt || "").localeCompare(String(a.generatedAt || "")));
}

function renderCurrentTaskSummary() {
  const target = $("#currentTaskSummary");
  const snapshot = appState.current;
  if (!target) return;
  if (!snapshot?.task || !snapshot?.statistics) {
    target.innerHTML = `<div class="empty-evidence">当前没有可展示的任务。</div>`;
    return;
  }
  const status = taskPresentation(snapshot);
  const request = snapshot.runtime?.request || {};
  const monitor = request.taskType === "monitor";
  const name = monitor ? `${request.targetName || snapshot.task.keyword || "未命名"}监测任务` : `${snapshot.task.keyword || "未命名"}采集任务`;
  const query = monitor ? (request.searchQueries || []).map(item => item.query_text).join("、") : snapshot.task.keyword;
  const stats = snapshot.statistics;
  target.innerHTML = `<div class="current-task-header"><div><h3>${escapeHtml(name)}</h3><p>${escapeHtml(snapshot.task.id)}</p></div><span class="table-tag ${status.tone}">${escapeHtml(status.label)}</span></div>
    <div class="current-task-meta"><div><span>任务类型</span><strong>${monitor ? "监测任务" : "快速任务"}</strong></div><div><span>监测对象 / 关键词</span><strong title="${escapeHtml(query || "—")}">${escapeHtml(query || "—")}</strong></div><div><span>更新时间</span><strong>${escapeHtml(formatDate(snapshot.generatedAt))}</strong></div></div>
    <div class="current-task-metrics"><div><span>搜索发现</span><strong>${stats.searchRaw || 0}</strong></div><div><span>入选商品</span><strong>${stats.selectedProducts || 0}</strong></div><div><span>详情完成</span><strong>${stats.detailCollectedProducts || 0}</strong></div><div><span>OCR / 分析</span><strong>${stats.analyzedProducts || 0}</strong></div></div>
    <div class="current-task-actions"><button class="button button-secondary" data-open-run="${escapeHtml(snapshot.task.id)}">查看任务详情</button></div>`;
}

export async function refreshRunData(preferredRunId = null) {
  const taskList = await getTasks();
  appState.runs = taskList.tasks || [];
  const currentMeta = appState.runs.find(item => item.id === preferredRunId)
    || appState.runs.find(item => item.runtime?.active)
    || appState.runs[0];
  if (!currentMeta) throw new Error("当前没有可展示的任务数据");
  const historyMeta = appState.runs.find(item => item.id !== currentMeta.id && item.statistics?.clueProducts > 0);
  appState.current = await getRun(currentMeta.id);
  appState.history = historyMeta ? await getRun(historyMeta.id) : null;
}

function stopTaskPolling() {
  if (appState.pollTimer) clearTimeout(appState.pollTimer);
  appState.pollTimer = null;
}

export async function pollTask(taskId) {
  stopTaskPolling();
  try {
    const snapshot = await getRun(taskId);
    appState.current = snapshot;
    upsertRunMeta(snapshot);
    hooks.renderApp();
    if (snapshot.task.terminal) {
      await refreshRunData(taskId);
      await hooks.refreshProducts();
      hooks.renderApp();
      const failed = ["failed", "completed_with_errors"].includes(snapshot.task.stage);
      setTaskFormMessage(snapshot.task.message || snapshot.task.stageLabel, failed ? "error" : "success", "user");
      if (!failed) showToast("采集任务已完成，结果已自动更新");
      return;
    }
    appState.pollTimer = setTimeout(() => pollTask(taskId), 2000);
  } catch (error) {
    setTaskFormMessage(`状态更新失败：${error.message}`, "error", "user");
    appState.pollTimer = setTimeout(() => pollTask(taskId), 4000);
  }
}

export function buildTaskPayload(values) {
  const detailLimit = Number.parseInt(values.detailLimit, 10);
  if (values.taskType === "monitor") {
    return {
      task_type: "monitor",
      target_id: values.targetId,
      per_query_candidate_limit: Number.parseInt(values.perQueryCandidateLimit, 10),
      detail_limit: detailLimit,
    };
  }
  return {
    task_type: "quick",
    keyword: String(values.keyword || "").trim(),
    candidate_limit: Number.parseInt(values.candidateLimit, 10),
    detail_limit: detailLimit,
  };
}

function taskFormValues() {
  return {
    taskType: $("#taskModeInput").value,
    keyword: $("#taskKeywordInput").value,
    candidateLimit: $("#candidateLimitInput").value,
    targetId: $("#monitorTargetInput").value,
    perQueryCandidateLimit: $("#perQueryCandidateLimitInput").value,
    detailLimit: $("#detailLimitInput").value,
  };
}

export async function startTask() {
  setTaskFormMessage("正在创建任务…", "", "runtime");
  $("#startTaskButton").disabled = true;
  try {
    const snapshot = await createTask(buildTaskPayload(taskFormValues()));
    appState.current = snapshot;
    clearProductSelection();
    upsertRunMeta(snapshot);
    hooks.renderApp();
    showToast("任务已创建，采集流程正在后台运行");
    pollTask(snapshot.task.id);
  } catch (error) {
    setTaskFormMessage(error.message, "error", "user");
    $("#startTaskButton").disabled = false;
    if (error.activeTaskId) pollTask(error.activeTaskId);
  }
}

export async function openRun(taskId) {
  try {
    const snapshot = await getRun(taskId);
    appState.current = snapshot;
    clearProductSelection();
    upsertRunMeta(snapshot);
    hooks.renderApp();
    if (snapshot.runtime?.active) pollTask(taskId);
    hooks.activateView(snapshot.task.terminal ? "products" : "tasks");
  } catch (error) {
    showToast(`任务读取失败：${error.message}`);
  }
}

export async function resumeTask(taskId) {
  setTaskFormMessage("正在恢复任务…", "", "runtime");
  try {
    const snapshot = await resumeTaskRequest(taskId);
    appState.current = snapshot;
    upsertRunMeta(snapshot);
    hooks.renderApp();
    pollTask(taskId);
  } catch (error) {
    setTaskFormMessage(error.message, "error", "user");
  }
}

export function bindTaskEvents() {
  $("#scrollToLogs").addEventListener("click", () => {
    $("#runLogs details").open = true;
    $("#runLogs").scrollIntoView({ behavior: "smooth", block: "start" });
  });
  $("#focusNewTask").addEventListener("click", () => $("#newTaskForm").scrollIntoView({ behavior: "smooth", block: "start" }));
  $("#taskModeInput").addEventListener("change", syncTaskMode);
  $("#monitorTargetInput").addEventListener("change", () => renderMonitorTargetOptions($("#monitorTargetInput").value));
  $("#saveTaskDraft").addEventListener("click", () => {
    localStorage.setItem("risk-monitor-task-draft", JSON.stringify({
      name: $("#taskNameInput").value,
      ...taskFormValues(),
      savedAt: new Date().toISOString(),
    }));
    showToast("任务草稿已保存");
  });
  $("#startTaskButton").addEventListener("click", startTask);
}
