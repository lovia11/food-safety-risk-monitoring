"use strict";

import {
  getProductSnapshots,
  getRunFileText,
  getSnapshot,
  updateReview,
} from "../api.js";
import { appState, allRunSnapshots, findRunProduct } from "../state.js";
import {
  $,
  $$,
  analysisState,
  assetUrl,
  escapeHtml,
  formatDate,
  productThumb,
  reviewPresentation,
  safeExternalUrl,
  showToast,
} from "../utils.js";

export function defaultJudgmentSelection() {
  const existing = findRunProduct(appState.selectedRun, appState.selectedProduct);
  if (existing.snapshot && existing.product) return;
  const snapshots = allRunSnapshots();
  const snapshot = snapshots.find(item => item.products.some(product => product.risk?.reviewRequired === true))
    || snapshots.find(item => item.products.length);
  const product = snapshot?.products.find(item => item.risk?.reviewRequired === true)
    || snapshot?.products[0];
  if (!snapshot || !product) {
    appState.selectedRun = null;
    appState.selectedProduct = null;
    return;
  }
  appState.selectedRun = snapshot.task.id;
  appState.selectedProduct = product.id;
  appState.selectedImagePath = null;
}

export function selectJudgmentProduct(runId, productId, runSnapshot = null) {
  appState.selectedRun = runId;
  appState.selectedProduct = productId;
  appState.selectedImagePath = null;
  appState.businessSnapshot = null;
  if (runSnapshot) appState.selectedRunSnapshot = runSnapshot;
}

function evidenceKeywords(product) {
  const configured = Object.values(product.risk?.matchedKeywords || {}).flat();
  const evidence = (product.risk?.evidenceDetails || [])
    .flatMap(item => item.matched_keywords || item.matchedKeywords || []);
  return [...new Set([...configured, ...evidence])];
}

function renderEmptyJudgment() {
  $("#judgmentHero").innerHTML = `<div class="empty-evidence">当前任务尚无可查看的商品结果。</div>`;
  $("#analysisCard").innerHTML = `<div class="empty-evidence">任务产生商品分析结果后将在这里展示。</div>`;
  $("#evidenceList").innerHTML = `<div class="empty-evidence">尚未生成风险证据。</div>`;
  $("#galleryThumbs").innerHTML = "";
  $("#mainEvidenceImage").removeAttribute("src");
  $("#mainEvidenceImage").removeAttribute("alt");
  $("#mainEvidenceImageButton").hidden = true;
  delete $("#mainEvidenceImageButton").dataset.fullImage;
  delete $("#mainEvidenceImageButton").dataset.caption;
  $("#ocrFileName").textContent = "—";
  $("#ocrText").textContent = "暂无OCR结果。";
  $("#openProductLinkTop").href = "#";
  appState.businessSnapshot = null;
  renderReviewPanel();
}

export function renderJudgmentPage() {
  const { snapshot, product } = findRunProduct(appState.selectedRun, appState.selectedProduct);
  if (!snapshot || !product) {
    renderEmptyJudgment();
    return;
  }
  const runId = snapshot.task.id;
  const isHistory = runId !== appState.current?.task?.id;
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
      <div class="hero-meta"><div><span>商品ID</span><strong>${escapeHtml(product.id)}</strong></div><div><span>店铺</span><strong>${escapeHtml(product.shopName || "—")}</strong></div><div><span>搜索页地区</span><strong>${escapeHtml(product.region || "—")}</strong></div><div><span>搜索排名</span><strong>${product.rank ?? "—"}</strong></div><div><span>采集时间</span><strong>${escapeHtml(formatDate(product.collectedAt))}</strong></div></div>
    </div><div class="hero-side"><span>所属批次</span><strong>${escapeHtml(runId)}</strong><span style="margin-top:11px">原始详情图</span><strong>${product.counts?.originalImages || 0} 张</strong></div>
  </div>`;
  $("#openProductLinkTop").href = safeExternalUrl(product.productUrl);

  const keywords = evidenceKeywords(product);
  const evidence = product.risk?.evidenceDetails || [];
  let alertClass = "neutral";
  let alertIcon = "…";
  let title = "待OCR分析";
  let description = "当前商品已完成详情采集，尚未生成完整OCR与规则分析结果。";
  if (product.risk?.reviewRequired === true) {
    alertClass = "";
    alertIcon = "!";
    title = `检测到${effects.join("、") || "功效"}相关表达`;
    description = product.risk.reason || "当前商品页面中检测到相关功效表达，建议人工进一步复核页面内容。";
  } else if (product.risk?.reviewRequired === false) {
    alertClass = "info";
    alertIcon = "i";
    title = "未发现配置词库中的明显功效表达";
    description = product.risk.reason || "当前规则未命中明确功效表达，仍需结合页面语境人工判断。";
  }
  $("#analysisCard").innerHTML = `<div class="card-heading"><div><h2>系统分析结果</h2><p>基于页面文本和真实详情图OCR的规则筛查</p></div></div>
    <div class="analysis-alert ${alertClass}"><div class="alert-icon">${alertIcon}</div><div><h2>${escapeHtml(title)}</h2><p>${escapeHtml(description)}</p></div></div>
    <div class="metric-mini-grid"><div class="metric-mini"><span>命中功效</span><strong>${effects.length}</strong></div><div class="metric-mini"><span>命中关键词</span><strong>${keywords.length}</strong></div><div class="metric-mini"><span>证据数量</span><strong>${evidence.length}</strong></div><div class="metric-mini"><span>OCR图片</span><strong>${product.counts?.ocrImages || 0}</strong></div></div>`;

  $("#evidenceList").innerHTML = evidence.length ? evidence.map(item => {
    const isUser = item.content_origin === "user_generated";
    const matched = item.matched_keywords || item.matchedKeywords || [];
    const label = item.source_label || item.sourceLabel || item.source_type || "页面内容";
    return `<div class="evidence-item"><div class="evidence-top"><span class="source-tag ${isUser ? "user" : ""}">${escapeHtml(label)}</span><span class="origin-label">${isUser ? "user_generated · 辅助" : "seller_managed · 主要"}</span></div><p>${escapeHtml(item.text || "—")}</p>${matched.length ? `<div class="evidence-keywords">命中：${matched.map(escapeHtml).join("、")}</div>` : ""}</div>`;
  }).join("") : `<div class="empty-evidence">${analyzed ? "未发现配置词库中的明确功效证据" : "尚未生成风险证据"}</div>`;
  $("#ugcNotice").hidden = !evidence.some(item => item.content_origin === "user_generated");
  renderGallery(snapshot, product);
  renderReviewPanel();
}

export function renderReviewPanel() {
  const target = $("#reviewPanelContent");
  if (!target) return;
  const selected = appState.businessSnapshot;
  const matches = selected
    && selected.taskId === appState.selectedRun
    && selected.productId === appState.selectedProduct;
  if (!appState.selectedRun || !appState.selectedProduct) {
    $("#reviewStateBadge").className = "table-tag gray";
    $("#reviewStateBadge").textContent = "待复核";
    target.innerHTML = `<div class="empty-evidence">请选择商品后进行人工复核。</div>`;
    return;
  }
  if (!matches) {
    $("#reviewStateBadge").className = "table-tag gray";
    $("#reviewStateBadge").textContent = "读取中";
    target.innerHTML = `<div class="empty-evidence">正在读取复核记录…</div>`;
    return;
  }
  const review = selected.review || { status: "pending", note: "", reviewedAt: null };
  const presentation = reviewPresentation(review.status);
  $("#reviewStateBadge").className = `table-tag ${presentation.tone}`;
  $("#reviewStateBadge").textContent = presentation.label;
  target.innerHTML = `
    <label>复核结论
      <select id="reviewStatusInput">
        <option value="pending" ${review.status === "pending" ? "selected" : ""}>待复核</option>
        <option value="recommend_follow_up" ${review.status === "recommend_follow_up" ? "selected" : ""}>建议进一步关注</option>
        <option value="no_further_action" ${review.status === "no_further_action" ? "selected" : ""}>暂不进一步关注</option>
      </select>
    </label>
    <label>复核备注
      <textarea id="reviewNoteInput" maxlength="2000" placeholder="记录页面语境、资质核对或后续处理建议">${escapeHtml(review.note || "")}</textarea>
    </label>
    <p id="reviewMessage" class="review-message"></p>
    <div class="review-actions">
      <span class="review-saved-at">${review.reviewedAt ? `上次保存：${escapeHtml(formatDate(review.reviewedAt))}` : "尚未提交人工复核结论"}</span>
      <button class="button button-primary" data-save-review="${escapeHtml(selected.snapshotId)}">保存复核结果</button>
    </div>`;
}

export async function loadSelectedBusinessSnapshot() {
  const runId = appState.selectedRun;
  const productId = appState.selectedProduct;
  const token = ++appState.reviewLoadToken;
  appState.businessSnapshot = null;
  renderReviewPanel();
  if (!runId || !productId) return;
  try {
    const collection = await getProductSnapshots(productId);
    const match = (collection.snapshots || []).find(item => item.taskId === runId);
    if (!match) throw new Error("该商品尚未建立业务数据索引");
    const detail = await getSnapshot(match.snapshotId);
    if (token !== appState.reviewLoadToken || runId !== appState.selectedRun || productId !== appState.selectedProduct) return;
    appState.businessSnapshot = detail;
    renderReviewPanel();
  } catch (error) {
    if (token !== appState.reviewLoadToken) return;
    $("#reviewStateBadge").className = "table-tag gray";
    $("#reviewStateBadge").textContent = "读取失败";
    $("#reviewPanelContent").innerHTML = `<div class="empty-evidence">${escapeHtml(error.message)}</div>`;
  }
}

export async function saveSelectedReview(snapshotId) {
  const statusInput = $("#reviewStatusInput");
  const noteInput = $("#reviewNoteInput");
  const message = $("#reviewMessage");
  if (!statusInput || !noteInput || !message) return false;
  message.textContent = "正在保存…";
  message.className = "review-message";
  try {
    const result = await updateReview(snapshotId, {
      status: statusInput.value,
      note: noteInput.value,
    });
    if (appState.businessSnapshot?.snapshotId === snapshotId) {
      appState.businessSnapshot.review = result.review;
    }
    const workspaceItem = appState.productQuery.items.find(item => item.snapshotId === snapshotId);
    if (workspaceItem) workspaceItem.review = result.review;
    renderReviewPanel();
    $("#reviewMessage").textContent = "复核结果已保存";
    $("#reviewMessage").className = "review-message success";
    showToast("人工复核结果已保存");
    return true;
  } catch (error) {
    message.textContent = error.message;
    message.className = "review-message error";
    return false;
  }
}

function renderGallery(snapshot, product) {
  const images = product.assets?.originalImages || [];
  const ocrItems = product.assets?.ocrItems || [];
  $("#galleryCount").textContent = `${images.length} 张真实原图`;
  if (!images.length) {
    $("#galleryThumbs").innerHTML = "";
    $("#mainEvidenceImage").removeAttribute("src");
    $("#mainEvidenceImage").removeAttribute("alt");
    $("#mainEvidenceImageButton").hidden = true;
    delete $("#mainEvidenceImageButton").dataset.fullImage;
    delete $("#mainEvidenceImageButton").dataset.caption;
    $("#ocrFileName").textContent = "—";
    $("#ocrText").textContent = "暂无真实详情图片。";
    return;
  }
  if (!appState.selectedImagePath || !images.some(item => item.path === appState.selectedImagePath)) {
    const ocrEvidence = (product.risk?.evidenceDetails || [])
      .find(item => item.source_type === "ocr" || item.sourceType === "ocr");
    const evidenceFile = String(ocrEvidence?.source_path || ocrEvidence?.sourcePath || "")
      .split("/").pop()?.replace(".txt", "");
    const matchedOcr = evidenceFile
      ? ocrItems.find(item => String(item.image || "").startsWith(evidenceFile))
      : null;
    appState.selectedImagePath = matchedOcr?.imagePath || ocrItems[0]?.imagePath || images[0].path;
  }
  $("#galleryThumbs").innerHTML = images.map((item, index) => `<button class="thumb-button ${item.path === appState.selectedImagePath ? "active" : ""}" data-image-path="${escapeHtml(item.path)}" aria-label="查看第${index + 1}张详情图"><img src="${escapeHtml(assetUrl(snapshot.task.id, item.path))}" alt="第${index + 1}张真实详情图" loading="lazy"></button>`).join("");
  selectGalleryImage(snapshot, product, appState.selectedImagePath, false);
}

export async function selectGalleryImage(snapshot, product, path, refreshThumbs = true) {
  const images = product.assets?.originalImages || [];
  const image = images.find(item => item.path === path) || images[0];
  if (!image) return;
  $("#mainEvidenceImageButton").hidden = false;
  appState.selectedImagePath = image.path;
  const url = assetUrl(snapshot.task.id, image.path);
  $("#mainEvidenceImage").src = url;
  $("#mainEvidenceImage").alt = `商品${product.id}真实详情图${image.index || ""}`;
  $("#mainEvidenceImageButton").dataset.fullImage = url;
  $("#mainEvidenceImageButton").dataset.caption = `商品 ${product.id} · 原始详情图 ${image.index || ""}`;
  if (refreshThumbs) {
    $$(".thumb-button").forEach(button => {
      button.classList.toggle("active", button.dataset.imagePath === image.path);
    });
  }
  const ocrItem = (product.assets?.ocrItems || []).find(item => item.imagePath === image.path);
  $("#ocrFileName").textContent = ocrItem?.image || `原图 ${image.index || ""}`;
  if (!ocrItem?.textPath || ocrItem.status !== "success") {
    $("#ocrText").textContent = "该图片没有已完成的OCR结果。";
    return;
  }
  $("#ocrText").textContent = "正在读取真实OCR文字…";
  try {
    const text = await getRunFileText(snapshot.task.id, ocrItem.textPath);
    $("#ocrText").textContent = text.trim() || "OCR结果为空。";
  } catch (_) {
    $("#ocrText").textContent = "OCR文本读取失败。";
  }
}

export function selectedGalleryProduct() {
  return findRunProduct(appState.selectedRun, appState.selectedProduct);
}
