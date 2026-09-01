"use strict";

const API_ROOT = "/api";
const PREFERRED_CURRENT_RUN = "20260828_cdp_smoke2";
const PREFERRED_HISTORY_RUN = "20260817T181659_batch";
const PREFERRED_RISK_PRODUCT = "600949052422";

const appState = {
  current: null,
  history: null,
  runs: [],
  selectedRun: null,
  selectedProduct: null,
  selectedImagePath: null,
  filters: { query: "", status: "all", region: "all", effect: "all", review: "all" },
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function safeExternalUrl(value) {
  try {
    const url = new URL(String(value || ""));
    return ["http:", "https:"].includes(url.protocol) ? url.href : "#";
  } catch (_) {
    return "#";
  }
}

function encodedPath(path) {
  return String(path || "").split("/").filter(Boolean).map(encodeURIComponent).join("/");
}

function assetUrl(runId, path) {
  if (!runId || !path) return "";
  return `${API_ROOT}/runs/${encodeURIComponent(runId)}/files/${encodedPath(path)}`;
}

async function fetchJson(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) throw new Error(`请求失败：${response.status}`);
  return response.json();
}

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.remove("show"), 2200);
}

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit",
    hour12: false,
  }).format(date).replaceAll("/", "-");
}

function productThumb(product, runId) {
  const images = product.assets?.originalImages || [];
  const path = images[0]?.path || product.assets?.overview;
  return path ? assetUrl(runId, path) : "";
}

function analysisState(product) {
  const review = product.risk?.reviewRequired;
  if (review === true) return { label: "建议人工复核", tone: "orange", statusClass: "status-warning" };
  if (review === false) return { label: "未发现明显线索", tone: "blue", statusClass: "status-info" };
  return { label: "待OCR分析", tone: "gray", statusClass: "status-neutral" };
}

function renderStatCards() {
  const stats = appState.current.statistics;
  const selected = stats.selectedProducts;
  const pending = Math.max(selected - stats.analyzedProducts, 0);
  const cards = [
    ["⌕", "搜索发现商品", stats.searchRaw, `本批入选 ${selected} 件`, "blue"],
    ["▣", "完成详情采集", stats.detailCollectedProducts, `保存原始详情图 ${stats.originalImages} 张`, "green"],
    ["OCR", "完成OCR与分析", `${stats.analyzedProducts} / ${selected}`, "已生成结构化分析结果", "purple"],
    ["!", "待继续分析", pending, "等待OCR与规则处理", "orange"],
  ];
  $("#overviewStats").innerHTML = cards.map(([icon, label, value, foot, tone]) => `
    <article class="card overview-stat-card">
      <div class="overview-stat-icon ${tone}">${escapeHtml(icon)}</div>
      <div><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong><small>${escapeHtml(foot)}</small></div>
    </article>`).join("");
}

const CHART_COLORS = ["#2f7df4", "#35ae79", "#fa9a2e", "#ef5b62", "#7a67dc", "#7aa7d9"];

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
  return `<div class="donut" style="background:${background}"><div class="donut-center"><strong>${total}</strong><span>${escapeHtml(centerLabel)}</span></div></div>
    <div class="chart-legend">${items.map((item, index) => `<div><i class="legend-dot" style="background:${CHART_COLORS[index % CHART_COLORS.length]}"></i><span>${escapeHtml(item[0])}</span><b>${item[1]}</b></div>`).join("")}</div>`;
}

function classifyFood(product) {
  const name = String(product.name || "");
  if (/茶包|百合茶|泡水|茶/.test(name)) return "茶/冲泡类";
  if (/粉/.test(name)) return "粉类";
  if (/膏/.test(name)) return "膏滋类";
  return "原料类";
}

function taskPresentation(snapshot) {
  const stage = snapshot.task?.stage;
  if (stage === "completed") return { label: "已完成", tone: "green" };
  if (stage === "failed" || stage === "completed_with_errors") return { label: "失败", tone: "red" };
  if (["searching", "collecting_details", "processing_ocr_analysis"].includes(stage)) return { label: "进行中", tone: "green" };
  return { label: "待继续", tone: "orange" };
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
    const width = 520, height = 300, minLon = 73, maxLon = 135, minLat = 18, maxLat = 54;
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
      const fill = value >= 3 ? "#1677ff" : value === 2 ? "#69aaf8" : value === 1 ? "#b7d6fb" : "#edf5ff";
      const path = geometryPath(feature.geometry);
      return path ? `<path class="china-province" d="${path}" fill="${fill}" fill-rule="evenodd"><title>${escapeHtml(shortName)}：${value} 件</title></path>` : "";
    }).join("");
    target.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="中国省级商品地区热图">${paths}</svg><div class="heatmap-legend"><span>低</span><i class="heatmap-gradient"></i><span>高</span></div>`;
  } catch (error) {
    target.innerHTML = `<div class="map-loading">地区地图暂时无法加载</div>`;
  }
}

function renderOverviewDistributions() {
  const analyzed = allSnapshots().flatMap(snapshot => snapshot.products).filter(product => product.risk?.reviewRequired !== null && product.risk?.reviewRequired !== undefined);
  const effectItems = counted(analyzed.map(product => product.risk?.detectedEffects?.[0] || "无明显线索"));
  const foodItems = counted(appState.current.products.map(classifyFood));
  const regionItems = counted(appState.current.products.map(product => product.region || "未知地区"));
  $("#effectDistribution").innerHTML = donutMarkup(effectItems, "已分析商品");
  $("#foodDistribution").innerHTML = donutMarkup(foodItems, "本批商品");
  $("#regionDistribution").innerHTML = regionItems.slice(0, 5).map(([name, count]) => `<div><b>${escapeHtml(name)}</b><span>${count} 件</span></div>`).join("");
  renderChinaHeatmap(regionItems);
}

function renderOverviewTasks() {
  const snapshots = allSnapshots();
  $("#overviewTaskBody").innerHTML = snapshots.map((snapshot, index) => {
    const status = taskPresentation(snapshot);
    const stats = snapshot.statistics;
    return `<tr><td>${index === 0 ? "酸枣仁专项采集" : "酸枣仁历史验证"}<small>${escapeHtml(snapshot.task.id)}</small></td><td><span class="table-tag ${status.tone}">${status.label}</span></td><td>${stats.analyzedProducts}/${stats.selectedProducts}</td></tr>`;
  }).join("");
}

function flowData(stats) {
  const selected = stats.selectedProducts;
  return [
    { label: "搜索商品", count: `发现 ${stats.searchRaw}`, state: "done" },
    { label: "商品去重", count: `入选 ${selected}`, state: "done" },
    { label: "详情采集", count: `${stats.detailCollectedProducts}/${selected}`, state: "done" },
    { label: "原图保存", count: `${stats.originalImages} 张`, state: "done" },
    { label: "OCR识别", count: `完成 ${stats.analyzedProducts}/${selected}`, state: "current" },
    { label: "规则分析", count: `完成 ${stats.analyzedProducts}/${selected}`, state: "current" },
  ];
}

function renderFlow(target, vertical = false) {
  const data = flowData(appState.current.statistics);
  target.innerHTML = data.map((step, index) => `
    <div class="process-step ${step.state}">
      <div class="process-dot">${step.state === "done" ? "✓" : index + 1}</div>
      <div class="process-label">${escapeHtml(step.label)}</div>
      <div class="process-count">${escapeHtml(step.count)}</div>
    </div>`).join("");
  if (vertical) target.classList.add("vertical");
}

function productRow(product, runId, compact = false) {
  const state = analysisState(product);
  const thumb = productThumb(product, runId);
  const thumbHtml = thumb
    ? `<img class="product-thumb" src="${escapeHtml(thumb)}" alt="${escapeHtml(product.name)}真实详情缩略图" loading="lazy">`
    : `<div class="product-thumb"></div>`;
  if (compact) {
    return `<tr>
      <td><div class="product-cell">${thumbHtml}<div><strong>${escapeHtml(product.name || "—")}</strong><span>商品ID ${escapeHtml(product.id)}</span></div></div></td>
      <td>${escapeHtml(product.shopName || "—")}</td><td>${escapeHtml(product.region || "—")}</td>
      <td>${product.counts?.originalImages || 0} 张</td>
      <td><span class="table-tag ${state.tone}">${state.label}</span></td>
      <td><div class="table-actions"><button data-view-product="${escapeHtml(product.id)}" data-run-id="${escapeHtml(runId)}">查看详情</button></div></td>
    </tr>`;
  }
  const analyzed = product.risk?.reviewRequired !== null && product.risk?.reviewRequired !== undefined;
  const effects = product.risk?.detectedEffects || [];
  const effectHtml = effects.length
    ? effects.map(item => `<span class="table-tag orange">${escapeHtml(item)}</span>`).join(" ")
    : analyzed ? `<span class="table-tag blue">无明显线索</span>` : "—";
  const ocrLabel = analyzed ? `已完成（${product.counts?.ocrImages || 0}张）` : "待OCR分析";
  return `<tr>
    <td><div class="product-cell">${thumbHtml}<div><strong>${escapeHtml(product.name || "—")}</strong><span>商品ID ${escapeHtml(product.id)}</span></div></div></td>
    <td>${escapeHtml(product.shopName || "—")}</td><td>${escapeHtml(product.region || "—")}</td>
    <td>${product.counts?.originalImages || 0} 张</td>
    <td><span class="table-tag ${analyzed ? "green" : "gray"}">${ocrLabel}</span></td>
    <td>${effectHtml}</td><td><span class="table-tag ${state.tone}">${state.label}</span></td>
    <td><div class="table-actions"><button data-view-product="${escapeHtml(product.id)}" data-run-id="${escapeHtml(runId)}">查看详情</button><i></i><a href="${escapeHtml(safeExternalUrl(product.productUrl))}" target="_blank" rel="noopener">打开原链接</a></div></td>
  </tr>`;
}

function renderRecentProducts() {
  const products = allSnapshots().flatMap(snapshot => snapshot.products.filter(product => product.risk?.reviewRequired === true).map(product => ({ snapshot, product }))).slice(0, 5);
  $("#recentProductsBody").innerHTML = products.length ? products.map(({ snapshot, product }) => {
    const thumb = productThumb(product, snapshot.task.id);
    const thumbHtml = thumb ? `<img class="product-thumb" src="${escapeHtml(thumb)}" alt="${escapeHtml(product.name)}缩略图">` : `<div class="product-thumb"></div>`;
    const effects = (product.risk?.detectedEffects || []).join("、") || "—";
    return `<tr><td><div class="product-cell">${thumbHtml}<div><strong>${escapeHtml(product.name || "—")}</strong><span>商品ID ${escapeHtml(product.id)}</span></div></div></td><td>${escapeHtml(classifyFood(product))}</td><td><span class="table-tag blue">${escapeHtml(effects)}</span></td><td><span class="table-tag orange">待人工复核</span></td><td>${escapeHtml(formatDate(product.collectedAt))}</td><td><button class="text-button" data-view-product="${escapeHtml(product.id)}" data-run-id="${escapeHtml(snapshot.task.id)}">查看详情</button></td></tr>`;
  }).join("") : `<tr><td colspan="6" class="overview-review-empty">暂无待人工复核商品</td></tr>`;
}

function monitorProductEntries() {
  const currentProducts = (appState.current?.products || []).map(product => ({
    snapshot: appState.current,
    product,
    historical: false,
  }));
  const currentIds = new Set(currentProducts.map(item => item.product.id));
  const historicalAnalyzed = (appState.history?.products || [])
    .filter(product => product.risk?.reviewRequired !== null && product.risk?.reviewRequired !== undefined)
    .filter(product => !currentIds.has(product.id))
    .map(product => ({ snapshot: appState.history, product, historical: true }));
  return [...currentProducts, ...historicalAnalyzed];
}

function populateFilters() {
  const monitoredProducts = monitorProductEntries().map(item => item.product);
  const regions = [...new Set(monitoredProducts.map(item => item.region).filter(Boolean))].sort();
  $("#regionFilter").innerHTML = `<option value="all">全部</option>${regions.map(value => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join("")}`;
  const effects = [...new Set(monitoredProducts.flatMap(item => item.risk?.detectedEffects || []))].sort();
  $("#effectFilter").innerHTML = `<option value="all">全部</option>${effects.map(value => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join("")}<option value="none">无明显线索</option><option value="pending">待分析</option>`;
}

function filteredProducts() {
  const { query, status, region, effect, review } = appState.filters;
  const needle = query.trim().toLowerCase();
  return monitorProductEntries().filter(({ product }) => {
    const analyzed = product.risk?.reviewRequired !== null && product.risk?.reviewRequired !== undefined;
    const haystack = `${product.name} ${product.shopName} ${product.id}`.toLowerCase();
    if (needle && !haystack.includes(needle)) return false;
    if (status === "analyzed" && !analyzed) return false;
    if (status === "pending" && analyzed) return false;
    if (region !== "all" && product.region !== region) return false;
    if (effect === "pending" && analyzed) return false;
    if (effect === "none" && (!analyzed || (product.risk?.detectedEffects || []).length)) return false;
    if (!["all", "pending", "none"].includes(effect) && !(product.risk?.detectedEffects || []).includes(effect)) return false;
    if (review === "yes" && product.risk?.reviewRequired !== true) return false;
    if (review === "no" && product.risk?.reviewRequired !== false) return false;
    if (review === "pending" && analyzed) return false;
    return true;
  });
}

function renderProductTable() {
  const entries = filteredProducts();
  const historicalCount = monitorProductEntries().filter(item => item.historical).length;
  $("#productTableBody").innerHTML = entries.map(({ snapshot, product }) => productRow(product, snapshot.task.id)).join("");
  $("#productResultCount").textContent = `共 ${entries.length} 件；当前批次 ${appState.current.statistics.detailCollectedProducts} 件，历史已分析 ${historicalCount} 件`;
  $("#productEmpty").hidden = entries.length > 0;
}

function updateExportLinks() {
  const runId = appState.current.task.id;
  $("#exportCsv").href = assetUrl(runId, "products.csv");
  $("#viewJson").href = assetUrl(runId, "products.json");
  $("#viewReport").href = assetUrl(runId, "summary.md");
}

function allSnapshots() { return [appState.current, appState.history].filter(Boolean); }

function findProduct(runId, productId) {
  const snapshot = allSnapshots().find(item => item.task.id === runId);
  const product = snapshot?.products.find(item => item.id === productId);
  return { snapshot, product };
}

function defaultRiskSelection() {
  const product = appState.history.products.find(item => item.id === PREFERRED_RISK_PRODUCT)
    || appState.history.products.find(item => item.risk?.reviewRequired === true)
    || appState.current.products[0];
  const snapshot = appState.history.products.includes(product) ? appState.history : appState.current;
  appState.selectedRun = snapshot.task.id;
  appState.selectedProduct = product.id;
  appState.selectedImagePath = null;
}

function evidenceKeywords(product) {
  const configured = Object.values(product.risk?.matchedKeywords || {}).flat();
  const evidence = (product.risk?.evidenceDetails || []).flatMap(item => item.matched_keywords || item.matchedKeywords || []);
  return [...new Set([...configured, ...evidence])];
}

function renderJudgment() {
  const { snapshot, product } = findProduct(appState.selectedRun, appState.selectedProduct);
  if (!snapshot || !product) return;
  const runId = snapshot.task.id;
  const isHistory = runId !== appState.current.task.id;
  const thumb = productThumb(product, runId);
  const effects = product.risk?.detectedEffects || [];
  const analyzed = product.risk?.reviewRequired !== null && product.risk?.reviewRequired !== undefined;
  const state = analysisState(product);
  const tags = [
    `<span class="table-tag blue">${escapeHtml(product.keyword || "酸枣仁")}</span>`,
    ...effects.map(item => `<span class="table-tag orange">${escapeHtml(item)}</span>`),
    `<span class="table-tag ${state.tone}">${escapeHtml(state.label)}</span>`,
  ].join("");
  $("#judgmentHero").innerHTML = `<div class="hero-layout">
    ${thumb ? `<img class="hero-image" src="${escapeHtml(thumb)}" alt="真实商品详情缩略图">` : `<div class="hero-image"></div>`}
    <div><div>${isHistory ? `<span class="sample-badge">历史真实验证样本</span>` : ""}</div><h2 class="hero-title">${escapeHtml(product.name || "—")}</h2><div class="hero-tags">${tags}</div>
      <div class="hero-meta"><div><span>商品ID</span><strong>${escapeHtml(product.id)}</strong></div><div><span>店铺</span><strong>${escapeHtml(product.shopName || "—")}</strong></div><div><span>地区</span><strong>${escapeHtml(product.region || "—")}</strong></div><div><span>搜索排名</span><strong>${product.rank ?? "—"}</strong></div><div><span>采集时间</span><strong>${escapeHtml(formatDate(product.collectedAt))}</strong></div></div>
    </div><div class="hero-side"><span>所属批次</span><strong>${escapeHtml(runId)}</strong><span style="margin-top:11px">原始详情图</span><strong>${product.counts?.originalImages || 0} 张</strong></div>
  </div>`;
  $("#openProductLinkTop").href = safeExternalUrl(product.productUrl);

  const keywords = evidenceKeywords(product);
  const evidence = product.risk?.evidenceDetails || [];
  let alertClass = "neutral", alertIcon = "…", title = "待OCR分析", description = "当前商品已完成详情采集，尚未生成完整OCR与规则分析结果。";
  if (product.risk?.reviewRequired === true) {
    alertClass = ""; alertIcon = "!"; title = `检测到${effects.join("、") || "功效"}相关宣传`;
    description = product.risk.reason || "当前商品页面中检测到相关功效表达，建议人工进一步复核商家宣传内容。";
  } else if (product.risk?.reviewRequired === false) {
    alertClass = "info"; alertIcon = "i"; title = "未发现配置词库中的明显功效表达";
    description = product.risk.reason || "当前规则未命中明确功效表达，仍需结合页面语境人工判断。";
  }
  $("#analysisCard").innerHTML = `<div class="card-heading"><div><h2>系统分析结果</h2><p>基于页面文本和真实详情图OCR的规则筛查</p></div></div>
    <div class="analysis-alert ${alertClass}"><div class="alert-icon">${alertIcon}</div><div><h2>${escapeHtml(title)}</h2><p>${escapeHtml(description)}</p></div></div>
    <div class="metric-mini-grid"><div class="metric-mini"><span>命中功效</span><strong>${effects.length}</strong></div><div class="metric-mini"><span>命中关键词</span><strong>${keywords.length}</strong></div><div class="metric-mini"><span>证据数量</span><strong>${evidence.length}</strong></div><div class="metric-mini"><span>OCR图片</span><strong>${product.counts?.ocrImages || 0}</strong></div></div>`;

  $("#evidenceList").innerHTML = evidence.length ? evidence.map(item => {
    const isUser = item.content_origin === "user_generated";
    const matched = item.matched_keywords || item.matchedKeywords || [];
    return `<div class="evidence-item"><div class="evidence-top"><span class="source-tag ${isUser ? "user" : ""}">${escapeHtml(item.source_label || item.sourceLabel || item.source_type || "页面内容")}</span><span class="origin-label">${isUser ? "user_generated · 辅助" : "seller_managed · 主要"}</span></div><p>${escapeHtml(item.text || "—")}</p>${matched.length ? `<div class="evidence-keywords">命中：${matched.map(escapeHtml).join("、")}</div>` : ""}</div>`;
  }).join("") : `<div class="empty-evidence">${analyzed ? "未发现配置词库中的明确功效证据" : "尚未生成风险证据"}</div>`;
  $("#ugcNotice").hidden = !evidence.some(item => item.content_origin === "user_generated");
  renderGallery(snapshot, product);
}

function renderGallery(snapshot, product) {
  const images = product.assets?.originalImages || [];
  const ocrItems = product.assets?.ocrItems || [];
  $("#galleryCount").textContent = `${images.length} 张真实原图`;
  if (!images.length) {
    $("#galleryThumbs").innerHTML = "";
    $("#mainEvidenceImage").removeAttribute("src");
    $("#ocrText").textContent = "暂无真实详情图片。";
    return;
  }
  if (!appState.selectedImagePath || !images.some(item => item.path === appState.selectedImagePath)) {
    const ocrEvidence = (product.risk?.evidenceDetails || []).find(item => item.source_type === "ocr" || item.sourceType === "ocr");
    const evidenceFile = String(ocrEvidence?.source_path || ocrEvidence?.sourcePath || "").split("/").pop()?.replace(".txt", "");
    const matchedOcr = evidenceFile ? ocrItems.find(item => String(item.image || "").startsWith(evidenceFile)) : null;
    appState.selectedImagePath = matchedOcr?.imagePath || ocrItems[0]?.imagePath || images[0].path;
  }
  $("#galleryThumbs").innerHTML = images.map((item, index) => `<button class="thumb-button ${item.path === appState.selectedImagePath ? "active" : ""}" data-image-path="${escapeHtml(item.path)}" aria-label="查看第${index + 1}张详情图"><img src="${escapeHtml(assetUrl(snapshot.task.id, item.path))}" alt="第${index + 1}张真实详情图" loading="lazy"></button>`).join("");
  selectGalleryImage(snapshot, product, appState.selectedImagePath, false);
}

async function selectGalleryImage(snapshot, product, path, refreshThumbs = true) {
  const image = (product.assets?.originalImages || []).find(item => item.path === path) || product.assets?.originalImages?.[0];
  if (!image) return;
  appState.selectedImagePath = image.path;
  const url = assetUrl(snapshot.task.id, image.path);
  $("#mainEvidenceImage").src = url;
  $("#mainEvidenceImage").alt = `商品${product.id}真实详情图${image.index || ""}`;
  $("#mainEvidenceImageButton").dataset.fullImage = url;
  $("#mainEvidenceImageButton").dataset.caption = `商品 ${product.id} · 原始详情图 ${image.index || ""}`;
  if (refreshThumbs) $$(".thumb-button").forEach(button => button.classList.toggle("active", button.dataset.imagePath === image.path));
  const ocrItem = (product.assets?.ocrItems || []).find(item => item.imagePath === image.path);
  $("#ocrFileName").textContent = ocrItem?.image || `原图 ${image.index || ""}`;
  if (!ocrItem?.textPath || ocrItem.status !== "success") {
    $("#ocrText").textContent = "该图片没有已完成的OCR结果。";
    return;
  }
  $("#ocrText").textContent = "正在读取真实OCR文字…";
  try {
    const response = await fetch(assetUrl(snapshot.task.id, ocrItem.textPath), { cache: "no-store" });
    if (!response.ok) throw new Error();
    $("#ocrText").textContent = (await response.text()).trim() || "OCR结果为空。";
  } catch (_) {
    $("#ocrText").textContent = "OCR文本读取失败。";
  }
}

function renderTaskPage() {
  const snapshots = allSnapshots();
  const stateCounts = { running: 0, waiting: 0, completed: 0, failed: 0 };
  snapshots.forEach(snapshot => {
    const stage = snapshot.task?.stage;
    if (stage === "completed") stateCounts.completed += 1;
    else if (stage === "failed" || stage === "completed_with_errors") stateCounts.failed += 1;
    else if (["searching", "collecting_details", "processing_ocr_analysis"].includes(stage)) stateCounts.running += 1;
    else stateCounts.waiting += 1;
  });
  const stateCards = [
    ["▶", "进行中", stateCounts.running, "green"],
    ["◷", "待继续", stateCounts.waiting, "orange"],
    ["✓", "已完成", stateCounts.completed, "blue"],
    ["!", "失败", stateCounts.failed, "red"],
  ];
  $("#taskStateOverview").innerHTML = stateCards.map(([icon, label, count, tone]) => `<div class="task-state-item"><span class="task-state-icon ${tone}">${icon}</span><div><span>${label}</span><strong>${count}</strong></div></div>`).join("");
  $("#taskRecordBody").innerHTML = snapshots.map((snapshot, index) => {
    const stats = snapshot.statistics;
    const status = taskPresentation(snapshot);
    const total = Math.max(stats.selectedProducts || 0, 1);
    const value = stats.analyzedProducts || 0;
    const percent = Math.min(100, Math.round(value / total * 100));
    const collectedTimes = snapshot.products.map(product => product.collectedAt).filter(Boolean).sort();
    const createdAt = collectedTimes[0] || snapshot.generatedAt;
    return `<tr><td>${index === 0 ? "酸枣仁专项采集" : "酸枣仁历史验证"}</td><td>${escapeHtml(snapshot.task.keyword || "酸枣仁")}</td><td><span class="table-tag ${status.tone}">${status.label}</span></td><td class="progress-cell"><span>${value} / ${stats.selectedProducts}</span><div class="progress-track"><i style="width:${percent}%"></i></div></td><td>${escapeHtml(formatDate(createdAt))}</td><td><a class="text-button" href="${API_ROOT}/runs/${encodeURIComponent(snapshot.task.id)}" target="_blank">查看</a></td></tr>`;
  }).join("");
  renderFlow($("#taskFlow"));
}

async function loadRunLog() {
  try {
    const response = await fetch(assetUrl(appState.current.task.id, "run.log"), { cache: "no-store" });
    if (!response.ok) throw new Error();
    const lines = (await response.text()).trim().split(/\r?\n/);
    $("#logContent").textContent = lines.slice(-90).join("\n") || "日志为空。";
  } catch (_) {
    $("#logContent").textContent = "当前运行日志暂时无法读取。";
  }
}

function activateView(viewName) {
  $$(".view").forEach(view => view.classList.toggle("active", view.dataset.viewPanel === viewName));
  $$(".nav-item").forEach(item => item.classList.toggle("active", item.dataset.view === viewName));
  if (viewName === "judgment") renderJudgment();
  window.scrollTo({ top: 0, behavior: "instant" });
}

function bindEvents() {
  $$(".nav-item").forEach(button => button.addEventListener("click", () => {
    if (button.dataset.view === "judgment") defaultRiskSelection();
    activateView(button.dataset.view);
  }));
  $$('[data-nav-target]').forEach(button => button.addEventListener("click", () => activateView(button.dataset.navTarget)));
  document.addEventListener("click", event => {
    const detailButton = event.target.closest("[data-view-product]");
    if (detailButton) {
      appState.selectedRun = detailButton.dataset.runId;
      appState.selectedProduct = detailButton.dataset.viewProduct;
      appState.selectedImagePath = null;
      activateView("judgment");
      return;
    }
    const thumb = event.target.closest("[data-image-path]");
    if (thumb) {
      const { snapshot, product } = findProduct(appState.selectedRun, appState.selectedProduct);
      if (snapshot && product) selectGalleryImage(snapshot, product, thumb.dataset.imagePath);
    }
  });
  $("#productSearch").addEventListener("input", event => { appState.filters.query = event.target.value; renderProductTable(); });
  [["#statusFilter", "status"], ["#regionFilter", "region"], ["#effectFilter", "effect"], ["#reviewFilter", "review"]].forEach(([selector, key]) => {
    $(selector).addEventListener("change", event => { appState.filters[key] = event.target.value; renderProductTable(); });
  });
  $("#resetFilters").addEventListener("click", () => {
    appState.filters = { query: "", status: "all", region: "all", effect: "all", review: "all" };
    $("#productSearch").value = "";
    ["#statusFilter", "#regionFilter", "#effectFilter", "#reviewFilter"].forEach(selector => $(selector).value = "all");
    renderProductTable();
  });
  $("#overviewSearch").addEventListener("keydown", event => {
    if (event.key !== "Enter") return;
    appState.filters.query = event.currentTarget.value;
    $("#productSearch").value = event.currentTarget.value;
    renderProductTable();
    activateView("products");
  });
  $("#scrollToLogs").addEventListener("click", () => {
    $("#runLogs details").open = true;
    $("#runLogs").scrollIntoView({ behavior: "smooth", block: "start" });
  });
  $("#focusNewTask").addEventListener("click", () => $("#newTaskForm").scrollIntoView({ behavior: "smooth", block: "start" }));
  $("#saveTaskDraft").addEventListener("click", () => {
    localStorage.setItem("risk-monitor-task-draft", JSON.stringify({ name: $("#taskNameInput").value, savedAt: new Date().toISOString() }));
    showToast("任务草稿已保存");
  });
  $("#mainEvidenceImageButton").addEventListener("click", event => {
    const button = event.currentTarget;
    if (!button.dataset.fullImage) return;
    $("#modalImage").src = button.dataset.fullImage;
    $("#modalCaption").textContent = button.dataset.caption || "真实详情图";
    $("#imageModal").hidden = false;
  });
  const closeModal = () => { $("#imageModal").hidden = true; $("#modalImage").removeAttribute("src"); };
  $("#closeImageModal").addEventListener("click", closeModal);
  $("#imageModal").addEventListener("click", event => { if (event.target === event.currentTarget) closeModal(); });
  document.addEventListener("keydown", event => { if (event.key === "Escape" && !$("#imageModal").hidden) closeModal(); });
  $("#exportCsv").addEventListener("click", () => showToast("正在下载当前真实批次 CSV"));
}

function renderAll() {
  renderStatCards();
  renderOverviewDistributions();
  renderOverviewTasks();
  renderRecentProducts();
  populateFilters();
  renderProductTable();
  updateExportLinks();
  defaultRiskSelection();
  renderJudgment();
  renderTaskPage();
  loadRunLog();
}

async function init() {
  try {
    const runList = await fetchJson(`${API_ROOT}/runs`);
    const runs = runList.runs || [];
    appState.runs = runs;
    const currentMeta = runs.find(item => item.id === PREFERRED_CURRENT_RUN)
      || runs.find(item => item.statistics?.selectedProducts === 10 && item.statistics?.detailCollectedProducts === 10)
      || runs[0];
    const historyMeta = runs.find(item => item.id === PREFERRED_HISTORY_RUN)
      || runs.find(item => item.statistics?.clueProducts > 0 && item.id !== currentMeta?.id);
    if (!currentMeta || !historyMeta) throw new Error("缺少已生成的真实网页快照");
    [appState.current, appState.history] = await Promise.all([
      fetchJson(currentMeta.url), fetchJson(historyMeta.url),
    ]);
    renderAll();
    bindEvents();
    $("#loadingState").hidden = true;
    $("#appContent").hidden = false;
  } catch (error) {
    $("#loadingState").innerHTML = `<div class="load-error"><strong>数据读取失败</strong><p>${escapeHtml(error.message)}</p><p>请确认结果服务可用后刷新页面。</p></div>`;
  }
}

init();
