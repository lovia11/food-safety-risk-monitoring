"use strict";

import { appState, allRunSnapshots } from "../state.js";
import {
  $,
  assetUrl,
  escapeHtml,
  formatDate,
  productThumb,
  taskPresentation,
} from "../utils.js";

const CHART_COLORS = ["#2f7df4", "#35ae79", "#fa9a2e", "#ef5b62", "#7a67dc", "#7aa7d9"];

const STAT_ICONS = {
  search: `<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6"/><path d="m16 16 4 4"/></svg>`,
  detail: `<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="4" width="14" height="16" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/></svg>`,
  analysis: `<span aria-hidden="true">OCR</span>`,
  pending: `<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v6M12 17h.01"/></svg>`,
};

function counted(values) {
  return Object.entries(values.reduce((result, value) => {
    const key = value || "其他";
    result[key] = (result[key] || 0) + 1;
    return result;
  }, {})).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], "zh-CN"));
}

function donutMarkup(items, centerLabel) {
  const total = items.reduce((sum, item) => sum + item[1], 0);
  let cursor = 0;
  const stops = items.map((item, index) => {
    const start = cursor;
    cursor += total ? item[1] / total * 100 : 0;
    return `${CHART_COLORS[index % CHART_COLORS.length]} ${start}% ${cursor}%`;
  });
  const background = stops.length ? `conic-gradient(${stops.join(",")})` : "#e8edf3";
  const legend = items.map((item, index) => `<div><i class="legend-dot" style="background:${CHART_COLORS[index % CHART_COLORS.length]}"></i><span>${escapeHtml(item[0])}</span><b>${item[1]}</b></div>`).join("");
  return `<div class="donut" style="background:${background}"><div class="donut-center"><strong>${total}</strong><span>${escapeHtml(centerLabel)}</span></div></div><div class="chart-legend">${legend}</div>`;
}

function classifyFood(product) {
  const name = String(product.name || "");
  if (/茶包|百合茶|泡水|茶/.test(name)) return "茶/冲泡类";
  if (/粉/.test(name)) return "粉类";
  if (/膏/.test(name)) return "膏滋类";
  return "原料类";
}

function renderStatCards() {
  const stats = appState.current?.statistics;
  if (!stats) {
    $("#overviewStats").innerHTML = "";
    return;
  }
  const selected = stats.selectedProducts;
  const pending = Math.max(selected - stats.analyzedProducts, 0);
  const cards = [
    ["search", "搜索发现商品", stats.searchRaw, `本批入选 ${selected} 件`, "blue"],
    ["detail", "完成详情采集", stats.detailCollectedProducts, `保存原始详情图 ${stats.originalImages} 张`, "green"],
    ["analysis", "完成OCR与分析", `${stats.analyzedProducts} / ${selected}`, "已生成结构化分析结果", "purple"],
    ["pending", "待继续分析", pending, "等待OCR与规则处理", "orange"],
  ];
  $("#overviewStats").innerHTML = cards.map(([icon, label, value, foot, tone]) => `
    <article class="card overview-stat-card">
      <div class="overview-stat-icon ${tone}">${STAT_ICONS[icon]}</div>
      <div><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong><small>${escapeHtml(foot)}</small></div>
    </article>`).join("");
}

function normalizeProvinceName(value) {
  return String(value || "")
    .replace(/壮族自治区|回族自治区|维吾尔自治区|特别行政区|自治区|省|市/g, "")
    .trim();
}

async function renderChinaHeatmap(regionItems) {
  const target = $("#chinaHeatmap");
  const counts = Object.fromEntries(regionItems.map(([name, count]) => [normalizeProvinceName(name), count]));
  try {
    const response = await fetch("data/china-provinces.geojson", { cache: "force-cache" });
    if (!response.ok) throw new Error(`地图数据请求失败：${response.status}`);
    const geojson = await response.json();
    const width = 520;
    const height = 300;
    const minLon = 73;
    const maxLon = 135;
    const minLat = 18;
    const maxLat = 54;
    const longitudeFactor = Math.cos(35 * Math.PI / 180);
    const scale = Math.min((width - 22) / ((maxLon - minLon) * longitudeFactor), (height - 18) / (maxLat - minLat));
    const mapWidth = (maxLon - minLon) * longitudeFactor * scale;
    const mapHeight = (maxLat - minLat) * scale;
    const offsetX = (width - mapWidth) / 2;
    const offsetY = (height - mapHeight) / 2;
    const project = coordinate => [
      offsetX + (coordinate[0] - minLon) * longitudeFactor * scale,
      offsetY + (maxLat - coordinate[1]) * scale,
    ];
    const ringPath = ring => {
      const points = ring.filter(point => point[0] >= 72 && point[0] <= 136 && point[1] >= 17 && point[1] <= 55);
      if (points.length < 3) return "";
      return `${points.map((point, index) => {
        const [x, y] = project(point);
        return `${index ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`;
      }).join(" ")} Z`;
    };
    const geometryPath = geometry => {
      const polygons = geometry?.type === "Polygon" ? [geometry.coordinates] : geometry?.type === "MultiPolygon" ? geometry.coordinates : [];
      return polygons.flatMap(polygon => polygon.map(ringPath)).filter(Boolean).join(" ");
    };
    const paths = (geojson.features || []).map(feature => {
      const name = feature.properties?.name || "";
      if (!name) return "";
      const shortName = normalizeProvinceName(name);
      const value = counts[shortName] || 0;
      const fill = value >= 3 ? "#2563eb" : value === 2 ? "#69aaf8" : value === 1 ? "#b7d6fb" : "#edf5ff";
      const path = geometryPath(feature.geometry);
      return path ? `<path class="china-province" d="${path}" fill="${fill}" fill-rule="evenodd"><title>${escapeHtml(shortName)}：${value} 件</title></path>` : "";
    }).join("");
    target.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="中国省级商品地区热图">${paths}</svg><div class="heatmap-legend"><span>低</span><i class="heatmap-gradient"></i><span>高</span></div>`;
  } catch (_) {
    target.innerHTML = `<div class="map-loading">地区地图暂时无法加载</div>`;
  }
}

function renderOverviewDistributions() {
  const currentProducts = appState.current?.products || [];
  const analyzed = allRunSnapshots()
    .flatMap(snapshot => snapshot.products)
    .filter(product => product.risk?.reviewRequired !== null && product.risk?.reviewRequired !== undefined);
  const effectItems = counted(analyzed.map(product => product.risk?.detectedEffects?.[0] || "无明显线索"));
  const foodItems = counted(currentProducts.map(classifyFood));
  const regionItems = counted(currentProducts.map(product => product.region || "未知地区"));
  $("#effectDistribution").innerHTML = donutMarkup(effectItems, "已分析商品");
  $("#foodDistribution").innerHTML = donutMarkup(foodItems, "本批商品");
  $("#regionDistribution").innerHTML = regionItems.slice(0, 5).map(([name, count]) => `<div><b>${escapeHtml(name)}</b><span>${count} 件</span></div>`).join("");
  renderChinaHeatmap(regionItems);
}

function renderOverviewTasks() {
  $("#overviewTaskBody").innerHTML = allRunSnapshots().map(snapshot => {
    const status = taskPresentation(snapshot);
    const stats = snapshot.statistics;
    return `<tr><td>${escapeHtml(snapshot.task.keyword || "未命名")}采集任务<small>${escapeHtml(snapshot.task.id)}</small></td><td><span class="table-tag ${status.tone}">${status.label}</span></td><td>${stats.analyzedProducts}/${stats.selectedProducts}</td></tr>`;
  }).join("");
}

function renderRecentProducts() {
  const products = allRunSnapshots().flatMap(snapshot => snapshot.products
    .filter(product => product.risk?.reviewRequired === true)
    .map(product => ({ snapshot, product }))).slice(0, 5);
  $("#recentProductsBody").innerHTML = products.length ? products.map(({ snapshot, product }) => {
    const thumb = productThumb(product, snapshot.task.id);
    const thumbHtml = thumb ? `<img class="product-thumb" src="${escapeHtml(thumb)}" alt="${escapeHtml(product.name)}缩略图">` : `<div class="product-thumb"></div>`;
    const effects = (product.risk?.detectedEffects || []).join("、") || "—";
    return `<tr><td><div class="product-cell">${thumbHtml}<div><strong>${escapeHtml(product.name || "—")}</strong><span>商品ID ${escapeHtml(product.id)}</span></div></div></td><td>${escapeHtml(classifyFood(product))}</td><td><span class="table-tag blue">${escapeHtml(effects)}</span></td><td><span class="table-tag orange">待人工复核</span></td><td>${escapeHtml(formatDate(product.collectedAt))}</td><td><button class="text-button" data-view-product="${escapeHtml(product.id)}" data-run-id="${escapeHtml(snapshot.task.id)}">查看详情</button></td></tr>`;
  }).join("") : `<tr><td colspan="6" class="overview-review-empty">暂无待人工复核商品</td></tr>`;
}

export function updateExportLinks() {
  const runId = appState.current?.task?.id;
  if (!runId) return;
  $("#exportCsv").href = assetUrl(runId, "products.csv");
  $("#viewJson").href = assetUrl(runId, "products.json");
  $("#viewReport").href = assetUrl(runId, "summary.md");
}

export function renderOverviewPage() {
  renderStatCards();
  renderOverviewDistributions();
  renderOverviewTasks();
  renderRecentProducts();
  updateExportLinks();
}
