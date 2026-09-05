"use strict";

import {
  getInspectionContextOptions,
  getProductSnapshots,
  getRunFileText,
  getSnapshot,
  updateInspectionContext,
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

export function followUpPresentation(status) {
  return {
    suggest_testing: { label: "建议重点关注/检测", tone: "orange" },
    needs_context_review: { label: "需补充商品信息", tone: "blue" },
    auxiliary_evidence_only: { label: "仅辅助线索", tone: "gray" },
    knowledge_integrity_gap: { label: "知识完整性待核对", tone: "red" },
    no_applicable_verified_method: { label: "当前知识库暂无适用的已核验方法", tone: "gray" },
  }[status] || { label: status || "待人工核对", tone: "gray" };
}

export function applicabilityPresentation(status) {
  return {
    applicable: { label: "Reference范围匹配", tone: "green" },
    conditional: { label: "条件适用", tone: "orange" },
    not_applicable: { label: "当前Reference范围未覆盖", tone: "gray" },
    insufficient_context: { label: "信息不足", tone: "blue" },
  }[status] || { label: status || "待核对", tone: "gray" };
}

export function visibleSuggestedMethods(finding, followUp) {
  return finding?.evidence_qualification === "seller_managed_primary"
    ? (followUp?.suggested_methods || [])
    : [];
}

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

function optionMarkup(values, current, unknownLabel) {
  const options = [...new Set([...(values || []), ...(current ? [current] : [])])];
  return `<option value="" ${current == null ? "selected" : ""}>${unknownLabel}</option>${options.map(value => `<option value="${escapeHtml(value)}" ${value === current ? "selected" : ""}>${escapeHtml(value)}</option>`).join("")}`;
}

function renderContextForm(context) {
  const options = appState.inspectionContextOptions || {
    product_categories: [],
    product_forms: [],
    ingredient_contexts: [],
  };
  const ingredients = context.confirmed_ingredient_contexts || [];
  const ingredientOptions = [...new Set([
    ...(options.ingredient_contexts || []),
    ...ingredients,
  ])];
  const optionError = appState.inspectionContextOptionsError
    ? `<p class="inspection-inline-error">Reference选项读取失败：${escapeHtml(appState.inspectionContextOptionsError)}</p>`
    : "";
  return `<section class="inspection-context-panel">
    <div class="inspection-section-title"><div><h3>Product Inspection Context</h3><p>仅保存人工明确确认的信息；未知项保持“未确认”。</p></div></div>
    <div class="inspection-context-fields">
      <label>食品类别<select id="inspectionCategoryInput">${optionMarkup(options.product_categories, context.product_category, "未确认")}</select></label>
      <label>剂型<select id="inspectionFormInput">${optionMarkup(options.product_forms, context.product_form, "未确认")}</select></label>
      <label>ingredient context <span class="field-note">可多选</span><select id="inspectionIngredientInput" multiple>${ingredientOptions.map(value => `<option value="${escapeHtml(value)}" ${ingredients.includes(value) ? "selected" : ""}>${escapeHtml(value)}</option>`).join("")}</select></label>
      <button class="button button-primary inspection-save-button" data-save-inspection-context>保存并重新评估</button>
    </div>${optionError}<p id="inspectionSaveMessage" class="review-message"></p>
  </section>`;
}

function renderTriggerEvidence(items) {
  if (!items?.length) return `<div class="inspection-muted">暂无可桥接页面证据。</div>`;
  return `<div class="inspection-trigger-list">${items.map(item => `<div><span class="source-tag ${item.content_origin === "user_generated" ? "user" : ""}">${item.content_origin === "user_generated" ? "UGC · 辅助" : "商家管理内容"}</span><p>${escapeHtml(item.text || "—")}</p></div>`).join("")}</div>`;
}

function renderMethod(method, secondary = false) {
  const applicability = applicabilityPresentation(method.applicability_status);
  const sourceUrl = safeExternalUrl(method.source_reference);
  return `<div class="inspection-method ${secondary ? "secondary" : ""}">
    <div><strong>${escapeHtml(method.method_no || "—")}</strong><span class="table-tag ${applicability.tone}">${escapeHtml(applicability.label)}</span></div>
    <p>${escapeHtml(method.method_name || "—")}</p>
    <small>${escapeHtml(method.source_name || "官方Reference")}${sourceUrl !== "#" ? ` · <a href="${escapeHtml(sourceUrl)}" target="_blank" rel="noopener">查看来源</a>` : ""}</small>
    ${method.applicability_reason ? `<small>${escapeHtml(method.applicability_reason)}</small>` : ""}
  </div>`;
}

function renderMethodSection(title, methods, className = "") {
  if (!methods?.length) return "";
  return `<div class="inspection-method-section ${className}"><h4>${title}</h4>${methods.map(item => renderMethod(item, className === "secondary")).join("")}</div>`;
}

function renderSubstance(followUp, finding) {
  const status = followUpPresentation(followUp.follow_up_status);
  const contextIds = (followUp.methods_needing_context || [])
    .flatMap(item => item.unresolved_applicability_ids || []);
  return `<article class="inspection-substance">
    <div class="inspection-substance-head"><div><h4>${escapeHtml(followUp.canonical_name || "待核对成分")}</h4><p>CAS：${escapeHtml(followUp.cas_no || "—")}</p></div><span class="table-tag ${status.tone}">${escapeHtml(status.label)}</span></div>
    <p class="inspection-reason">${escapeHtml(followUp.reason || "")}</p>
    ${contextIds.length ? `<div class="context-needed">还需确认与以下 Reference 范围有关的商品信息：${[...new Set(contextIds)].map(escapeHtml).join("、")}</div>` : ""}
    ${renderMethodSection("建议方法", visibleSuggestedMethods(finding, followUp))}
    ${renderMethodSection("待补充信息的方法", followUp.methods_needing_context, "needs-context")}
    ${(followUp.other_known_methods || []).length ? `<details class="other-methods"><summary>其他已知方法（${followUp.other_known_methods.length}）</summary>${followUp.other_known_methods.map(item => renderMethod(item, true)).join("")}</details>` : ""}
    ${(followUp.regulatory_contexts || []).length ? `<details class="regulatory-context"><summary>监管语境（需人工确认）</summary><p>${escapeHtml(followUp.regulatory_context_note || "")}</p>${followUp.regulatory_contexts.map(item => `<p>${escapeHtml(item.product_scope || item.note || "—")}</p>`).join("")}</details>` : ""}
  </article>`;
}

function renderGapSection(inspection) {
  const groups = (inspection.riskFindings || []).flatMap(item => item.group_targets || []);
  const composition = inspection.compositionGaps || [];
  const knowledge = inspection.knowledgeGaps || [];
  if (!groups.length && !composition.length && !knowledge.length) return "";
  return `<section class="inspection-gaps"><h3>Group partial / 知识缺口</h3>
    ${groups.map(item => `<div><strong>Group（partial）：${escapeHtml(item.target_group_label || "未命名Group")}</strong><p>仅保留Reference中的Group文字，不自动展开成员。</p></div>`).join("")}
    ${composition.map(item => `<div class="gap-warning"><strong>知识链组合缺口</strong><p>${escapeHtml(item.message || item.type || "需人工核对")}</p></div>`).join("")}
    ${knowledge.map(item => `<div><strong>知识缺口：${escapeHtml(item.type || "待核对")}</strong><p>${escapeHtml(item.message || "当前知识库信息不完整。")}</p></div>`).join("")}
  </section>`;
}

export function renderInspectionPanel(product, isHistory = false) {
  const target = $("#inspectionContent");
  if (!target) return;
  const badge = $("#inspectionStateBadge");
  const inspection = product?.inspection || {
    available: false,
    recommendationStatus: "unavailable",
    context: {
      product_category: null,
      product_form: null,
      confirmed_ingredient_contexts: [],
      context_evidence: [],
    },
  };
  const contextForm = renderContextForm(inspection.context || {});
  if (!inspection.available) {
    const failed = inspection.recommendationStatus === "error";
    badge.className = `table-tag ${failed ? "red" : "gray"}`;
    badge.textContent = failed ? "生成失败" : "尚未生成";
    const unavailableTitle = isHistory
      ? "该历史任务尚未生成抽检辅助建议"
      : "当前商品尚未生成抽检辅助建议";
    target.innerHTML = `${contextForm}<div class="inspection-unavailable ${failed ? "error" : ""}"><strong>${failed ? "抽检辅助建议暂不可用" : unavailableTitle}</strong><p>${escapeHtml(inspection.error?.message || "原有Phase3分析和风险证据仍可正常查看。")}</p></div>`;
    return;
  }
  badge.className = "table-tag green";
  badge.textContent = "已生成";
  const findings = inspection.riskFindings || [];
  target.innerHTML = `${contextForm}
    <section class="inspection-findings"><div class="inspection-section-title"><div><h3>可能风险与建议关注成分</h3><p>页面线索对应的监管关注方向，不是实验室结论。</p></div></div>
      ${findings.length ? findings.map(finding => `<article class="inspection-finding">
        <div class="inspection-finding-head"><div><h3>${escapeHtml((finding.risk_labels || []).join("、") || finding.risk_category || "待核对风险方向")}</h3><p>${escapeHtml(finding.possible_risk_summary || "")}</p></div><span class="table-tag ${finding.evidence_qualification === "seller_managed_primary" ? "orange" : "gray"}">${finding.evidence_qualification === "seller_managed_primary" ? "商家管理内容支持" : "仅UGC辅助线索"}</span></div>
        ${renderTriggerEvidence(finding.trigger_evidence || [])}
        <div class="inspection-substance-grid">${(finding.substance_follow_ups || []).map(item => renderSubstance(item, finding)).join("") || `<div class="inspection-muted">当前没有可列出的具体成分，Group与知识缺口见下方。</div>`}</div>
      </article>`).join("") : `<div class="inspection-muted">当前Phase3证据没有进入已核验的Evidence-to-Risk Bridge。</div>`}
    </section>
    ${renderGapSection(inspection)}
    <div class="inspection-disclaimer">${escapeHtml(inspection.disclaimer || "")}</div>`;
}

async function loadInspectionContextOptions() {
  if (appState.inspectionContextOptions || appState.inspectionContextOptionsError) return;
  try {
    appState.inspectionContextOptions = await getInspectionContextOptions();
  } catch (error) {
    appState.inspectionContextOptionsError = error.message;
  }
}

export async function saveInspectionContext() {
  const { product } = findRunProduct(appState.selectedRun, appState.selectedProduct);
  const message = $("#inspectionSaveMessage");
  if (!product || !message) return false;
  message.textContent = "正在保存并重新评估…";
  message.className = "review-message";
  const ingredientInput = $("#inspectionIngredientInput");
  const payload = {
    product_category: $("#inspectionCategoryInput").value || null,
    product_form: $("#inspectionFormInput").value || null,
    confirmed_ingredient_contexts: [...ingredientInput.selectedOptions].map(item => item.value),
  };
  try {
    const result = await updateInspectionContext(
      appState.selectedRun,
      appState.selectedProduct,
      payload,
    );
    product.inspection = result.inspection || {
      available: true,
      recommendationStatus: "available",
      context: result.context,
      riskFindings: result.recommendation.risk_findings || [],
      unmappedEvidence: result.recommendation.unmapped_evidence || [],
      compositionGaps: result.recommendation.composition_gaps || [],
      knowledgeGaps: result.recommendation.knowledge_gaps || [],
      disclaimer: result.recommendation.disclaimer || "",
    };
    renderInspectionPanel(product);
    showToast("商品信息已保存，抽检辅助建议已重新评估");
    return true;
  } catch (error) {
    message.textContent = error.message;
    message.className = "review-message error";
    return false;
  }
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
  $("#inspectionStateBadge").className = "table-tag gray";
  $("#inspectionStateBadge").textContent = "尚未生成";
  $("#inspectionContent").innerHTML = `<div class="empty-evidence">该历史任务尚未生成抽检辅助建议</div>`;
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
  renderInspectionPanel(product, isHistory);
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
    await loadInspectionContextOptions();
    const collection = await getProductSnapshots(productId);
    const match = (collection.snapshots || []).find(item => item.taskId === runId);
    if (!match) throw new Error("该商品尚未建立业务数据索引");
    const detail = await getSnapshot(match.snapshotId);
    if (token !== appState.reviewLoadToken || runId !== appState.selectedRun || productId !== appState.selectedProduct) return;
    appState.businessSnapshot = detail;
    renderReviewPanel();
    const { product } = findRunProduct(runId, productId);
    if (product) renderInspectionPanel(product, runId !== appState.current?.task?.id);
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
