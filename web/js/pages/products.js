"use strict";

import { getProducts } from "../api.js";
import { appState, defaultProductQueryState } from "../state.js";
import {
  $,
  escapeHtml,
  formatDate,
  monitorTargetPresentation,
  reviewPresentation,
  safeExternalUrl,
} from "../utils.js";

export function applyProductPage(payload, state = appState.productQuery) {
  state.items = Array.isArray(payload.products) ? payload.products : [];
  state.page = Number(payload.page) || state.page || 1;
  state.pageSize = Number(payload.pageSize) || state.pageSize || 20;
  state.total = Number(payload.total) || 0;
  state.totalPages = Number(payload.totalPages) || 0;
  state.loading = false;
  state.error = "";
  state.loaded = true;
  return state;
}

export function updateProductFilters(patch, state = appState.productQuery) {
  state.filters = { ...state.filters, ...patch };
  state.page = 1;
  return state;
}

export function productTargetLabel(product) {
  return product.targetName || (product.targetId ? "未命名监测对象" : "快速任务");
}

export function productEffectPresentation(product) {
  const analyzed = product.reviewRequired !== null && product.reviewRequired !== undefined;
  const effects = Array.isArray(product.detectedEffects) ? product.detectedEffects : [];
  if (effects.length) return { effects, label: "", tone: "orange" };
  if (analyzed) return { effects: [], label: "未发现明显线索", tone: "blue" };
  return { effects: [], label: "待分析", tone: "gray" };
}

function targetOptions() {
  return appState.monitorTargets.map(target => {
    const name = target.targetName || target.standardName || target.standard_name || "未命名对象";
    const id = target.targetId || target.target_id || "";
    const kind = monitorTargetPresentation(target);
    return `<option value="${escapeHtml(id)}">${escapeHtml(name)} · ${kind.label}</option>`;
  }).join("");
}

export function populateProductTargetOptions() {
  const select = $("#productTargetFilter");
  if (!select) return;
  const selected = appState.productQuery.filters.targetId;
  select.innerHTML = `<option value="">全部</option>${targetOptions()}`;
  if ([...select.options].some(option => option.value === selected)) select.value = selected;
}

function renderProductRow(product) {
  const effect = productEffectPresentation(product);
  const effects = effect.effects.length
    ? effect.effects.map(item => `<span class="table-tag orange">${escapeHtml(item)}</span>`).join(" ")
    : `<span class="table-tag ${effect.tone}">${escapeHtml(effect.label)}</span>`;
  const review = reviewPresentation(product.review?.status);
  const targetLabel = productTargetLabel(product);
  const target = appState.monitorTargets.find(item => (item.target_id || item.targetId) === product.targetId);
  const targetKind = product.targetId ? monitorTargetPresentation(target) : null;
  const targetMarkup = product.targetId
    ? `<span class="table-tag blue">${escapeHtml(targetLabel)}</span>${targetKind ? `<small class="target-kind">${targetKind.label}</small>` : ""}`
    : `<span class="table-tag gray">${escapeHtml(targetLabel)}</span>`;
  return `<tr>
    <td><div class="product-cell"><div class="product-thumb product-thumb-placeholder" aria-hidden="true"><svg viewBox="0 0 24 24"><rect x="4" y="5" width="16" height="14" rx="2"/><path d="m7 16 3.5-3.5 2.5 2 2-2 2 2"/><circle cx="15.5" cy="9" r="1"/></svg></div><div><strong title="${escapeHtml(product.productName || "—")}">${escapeHtml(product.productName || "—")}</strong><span>商品ID ${escapeHtml(product.productId)}</span></div></div></td>
    <td><div class="target-cell">${targetMarkup}</div></td>
    <td>${escapeHtml(product.shopName || "—")}</td>
    <td>${escapeHtml(product.region || "—")}</td>
    <td><div class="effect-tags">${effects}</div></td>
    <td><span class="table-tag ${review.tone}">${escapeHtml(review.label)}</span></td>
    <td>${escapeHtml(formatDate(product.collectedAt))}</td>
    <td><div class="table-actions"><button data-view-product="${escapeHtml(product.productId)}" data-run-id="${escapeHtml(product.taskId)}">查看详情</button><i></i><a href="${escapeHtml(safeExternalUrl(product.productUrl))}" target="_blank" rel="noopener">打开原链接</a></div></td>
  </tr>`;
}

function loadingRows() {
  return Array.from({ length: 6 }, () => `<tr class="loading-row" aria-hidden="true"><td><div class="product-skeleton"></div></td><td><div class="product-skeleton short"></div></td><td><div class="product-skeleton short"></div></td><td><div class="product-skeleton short"></div></td><td><div class="product-skeleton short"></div></td><td><div class="product-skeleton short"></div></td><td><div class="product-skeleton short"></div></td><td><div class="product-skeleton short"></div></td></tr>`).join("");
}

function hasProductFilters(state) {
  return Object.values(state.filters || {}).some(Boolean);
}

function syncProductControls() {
  const state = appState.productQuery;
  $("#productSearch").value = state.filters.query;
  $("#productTargetFilter").value = state.filters.targetId;
  $("#productReviewFilter").value = state.filters.reviewStatus;
  $("#productEffectFilter").value = state.filters.effect;
  $("#productPageSize").value = String(state.pageSize);
}

export function renderProductsPage() {
  const state = appState.productQuery;
  const body = $("#productTableBody");
  const table = $("#productTableWrap");
  const empty = $("#productEmpty");
  const status = $("#productWorkspaceStatus");
  if (!body || !table || !empty || !status) return;

  syncProductControls();
  body.innerHTML = state.loading ? loadingRows() : state.items.map(renderProductRow).join("");
  table.hidden = Boolean(state.error) || (!state.loading && !state.items.length);
  table.setAttribute("aria-busy", state.loading ? "true" : "false");
  empty.hidden = state.loading || Boolean(state.error) || Boolean(state.items.length);

  if (state.loading) {
    status.hidden = true;
    status.className = "workspace-state";
    status.textContent = "";
  } else if (state.error) {
    status.hidden = false;
    status.className = "workspace-state error";
    status.innerHTML = `<strong>商品数据加载失败</strong><p>${escapeHtml(state.error)}</p><button class="button button-secondary" id="retryProductQuery">重新加载</button>`;
  } else {
    status.hidden = true;
    status.textContent = "";
  }

  const filtered = hasProductFilters(state);
  $("#productEmptyTitle").textContent = filtered ? "没有符合当前筛选条件的商品" : "暂无监测商品";
  $("#productEmptyHint").textContent = filtered ? "请调整或清空筛选条件后重试。" : "请先创建采集任务，完成后可在这里跨任务查询。";
  $("#clearProductFilters").hidden = !filtered;
  $("#productResultCount").textContent = filtered ? `共 ${state.total} 件符合当前条件` : `共 ${state.total} 件商品`;

  const displayPage = state.totalPages ? state.page : 0;
  const rangeStart = state.items.length ? (state.page - 1) * state.pageSize + 1 : 0;
  const rangeEnd = state.items.length ? rangeStart + state.items.length - 1 : 0;
  $("#productPageSummary").textContent = `第 ${displayPage} / ${state.totalPages}页`;
  $("#productTotalSummary").textContent = `${rangeStart}–${rangeEnd} / 共 ${state.total} 件`;
  $("#productFirstPage").disabled = !state.totalPages || state.page <= 1;
  $("#productPreviousPage").disabled = !state.totalPages || state.page <= 1;
  $("#productNextPage").disabled = !state.totalPages || state.page >= state.totalPages;
  $("#productLastPage").disabled = !state.totalPages || state.page === state.totalPages;
}

export async function loadProductsPage() {
  const state = appState.productQuery;
  const token = ++state.requestToken;
  state.loading = true;
  state.error = "";
  renderProductsPage();
  try {
    const payload = await getProducts(state);
    if (token !== state.requestToken) return;
    applyProductPage(payload, state);
  } catch (error) {
    if (token !== state.requestToken) return;
    state.loading = false;
    state.loaded = true;
    state.error = error.message || "商品数据读取失败";
  }
  renderProductsPage();
}

function filtersFromControls() {
  return {
    targetId: $("#productTargetFilter").value,
    query: $("#productSearch").value.trim(),
    reviewStatus: $("#productReviewFilter").value,
    effect: $("#productEffectFilter").value,
    taskId: "",
  };
}

async function runProductQuery() {
  updateProductFilters(filtersFromControls());
  await loadProductsPage();
}

async function goToPage(page) {
  if (!Number.isInteger(page) || page < 1) return;
  appState.productQuery.page = page;
  await loadProductsPage();
}

export async function searchProductsFromOverview(query) {
  updateProductFilters({ query: String(query || "").trim(), taskId: "" });
  syncProductControls();
  await loadProductsPage();
}

export function resetProductQueryState() {
  appState.productQuery = defaultProductQueryState();
  populateProductTargetOptions();
  renderProductsPage();
}

export function bindProductEvents() {
  $("#runProductQuery").addEventListener("click", runProductQuery);
  $("#productSearch").addEventListener("keydown", event => {
    if (event.key === "Enter") runProductQuery();
  });
  ["#productTargetFilter", "#productReviewFilter", "#productEffectFilter"].forEach(selector => {
    $(selector).addEventListener("change", runProductQuery);
  });
  $("#productPageSize").addEventListener("change", async event => {
    appState.productQuery.pageSize = Number.parseInt(event.target.value, 10) || 20;
    updateProductFilters(filtersFromControls());
    await loadProductsPage();
  });
  const resetFilters = async () => {
    appState.productQuery = defaultProductQueryState();
    populateProductTargetOptions();
    renderProductsPage();
    await loadProductsPage();
  };
  $("#resetFilters").addEventListener("click", resetFilters);
  $("#clearProductFilters").addEventListener("click", resetFilters);
  $("#productFirstPage").addEventListener("click", () => goToPage(1));
  $("#productPreviousPage").addEventListener("click", () => goToPage(appState.productQuery.page - 1));
  $("#productNextPage").addEventListener("click", () => goToPage(appState.productQuery.page + 1));
  $("#productLastPage").addEventListener("click", () => goToPage(appState.productQuery.totalPages));
  $("#productWorkspaceStatus").addEventListener("click", event => {
    if (event.target.closest("#retryProductQuery")) loadProductsPage();
  });
}
