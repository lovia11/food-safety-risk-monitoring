"use strict";

import { getRun } from "./js/api.js";
import { appState, findRunProduct } from "./js/state.js";
import { $, $$, escapeHtml, showToast } from "./js/utils.js";
import { renderOverviewPage } from "./js/pages/overview.js";
import {
  bindProductEvents,
  loadProductsPage,
  populateProductTargetOptions,
  renderProductsPage,
  searchProductsFromOverview,
} from "./js/pages/products.js";
import {
  defaultJudgmentSelection,
  loadSelectedBusinessSnapshot,
  renderJudgmentPage,
  saveInspectionContext,
  saveSelectedReview,
  selectGalleryImage,
  selectedGalleryProduct,
  selectJudgmentProduct,
} from "./js/pages/judgment.js";
import {
  bindTaskEvents,
  configureTaskPage,
  loadMonitorTargets,
  loadRunLog,
  openRun,
  pollTask,
  refreshRunData,
  renderTasksPage,
  resumeTask,
  syncTaskMode,
} from "./js/pages/tasks.js";

function renderApplication() {
  renderOverviewPage();
  renderProductsPage();
  defaultJudgmentSelection();
  renderJudgmentPage();
  renderTasksPage();
  loadRunLog();
}

function activateView(viewName) {
  appState.currentView = viewName;
  $$(".view").forEach(view => {
    view.classList.toggle("active", view.dataset.viewPanel === viewName);
  });
  $$(".nav-item").forEach(item => {
    item.classList.toggle("active", item.dataset.view === viewName);
  });
  if (viewName === "judgment") {
    defaultJudgmentSelection();
    renderJudgmentPage();
    loadSelectedBusinessSnapshot();
  }
  window.scrollTo({ top: 0, behavior: "instant" });
}

async function openProductDetail(runId, productId) {
  try {
    let runSnapshot = findRunProduct(runId, productId).snapshot;
    if (!runSnapshot) runSnapshot = await getRun(runId);
    selectJudgmentProduct(runId, productId, runSnapshot);
    activateView("judgment");
  } catch (error) {
    showToast(`商品详情读取失败：${error.message}`);
  }
}

function bindGlobalEvents() {
  $$(".nav-item").forEach(button => button.addEventListener("click", () => {
    activateView(button.dataset.view);
  }));
  $$('[data-nav-target]').forEach(button => button.addEventListener("click", () => {
    activateView(button.dataset.navTarget);
  }));
  document.addEventListener("click", async event => {
    const runButton = event.target.closest("[data-open-run]");
    if (runButton) {
      await openRun(runButton.dataset.openRun);
      return;
    }
    const resumeButton = event.target.closest("[data-resume-task]");
    if (resumeButton) {
      await resumeTask(resumeButton.dataset.resumeTask);
      return;
    }
    const detailButton = event.target.closest("[data-view-product]");
    if (detailButton) {
      await openProductDetail(detailButton.dataset.runId, detailButton.dataset.viewProduct);
      return;
    }
    const reviewButton = event.target.closest("[data-save-review]");
    if (reviewButton) {
      if (await saveSelectedReview(reviewButton.dataset.saveReview)) await loadProductsPage();
      return;
    }
    const inspectionButton = event.target.closest("[data-save-inspection-context]");
    if (inspectionButton) {
      await saveInspectionContext();
      return;
    }
    const thumb = event.target.closest("[data-image-path]");
    if (thumb) {
      const { snapshot, product } = selectedGalleryProduct();
      if (snapshot && product) selectGalleryImage(snapshot, product, thumb.dataset.imagePath);
    }
  });
  $("#overviewSearch").addEventListener("keydown", async event => {
    if (event.key !== "Enter") return;
    activateView("products");
    await searchProductsFromOverview(event.currentTarget.value);
  });
  $("#mainEvidenceImageButton").addEventListener("click", event => {
    const button = event.currentTarget;
    if (!button.dataset.fullImage) return;
    $("#modalImage").src = button.dataset.fullImage;
    $("#modalCaption").textContent = button.dataset.caption || "真实详情图";
    $("#imageModal").hidden = false;
  });
  const closeModal = () => {
    $("#imageModal").hidden = true;
    $("#modalImage").removeAttribute("src");
  };
  $("#closeImageModal").addEventListener("click", closeModal);
  $("#imageModal").addEventListener("click", event => {
    if (event.target === event.currentTarget) closeModal();
  });
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && !$("#imageModal").hidden) closeModal();
  });
  $("#exportCsv").addEventListener("click", () => showToast("正在下载当前真实批次 CSV"));
}

async function init() {
  configureTaskPage({
    renderApp: renderApplication,
    refreshProducts: loadProductsPage,
    activateView,
    targetsChanged: populateProductTargetOptions,
  });
  bindGlobalEvents();
  bindProductEvents();
  bindTaskEvents();
  try {
    await loadMonitorTargets();
  } catch (error) {
    appState.monitorTargets = [];
    populateProductTargetOptions();
    $("#monitorQueryPreview").textContent = `监测对象读取失败：${error.message}`;
  }
  try {
    await refreshRunData();
  } catch (error) {
    showToast(`任务数据读取失败：${error.message}`);
  }
  defaultJudgmentSelection();
  renderApplication();
  syncTaskMode();
  $("#loadingState").hidden = true;
  $("#appContent").hidden = false;
  await loadProductsPage();
  if (appState.current?.runtime?.active) pollTask(appState.current.task.id);
}

init().catch(error => {
  $("#loadingState").innerHTML = `<div class="load-error"><strong>页面初始化失败</strong><p>${escapeHtml(error.message)}</p><p>请确认本地结果服务可用后刷新页面。</p></div>`;
});
