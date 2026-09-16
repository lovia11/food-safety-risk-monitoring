import {
  ClipboardCheck,
  ExternalLink,
  FileSearch,
  FlaskConical,
  ScanSearch,
} from "lucide-react";

import type { SnapshotWorkspace } from "../api/contracts";
import type { AnalysisStatePresentation } from "../domain/analysis";
import {
  claimPresentation,
  claimSignalLabels,
  claimSourceLabel,
} from "../domain/claims";
import type { EvidencePartitions } from "../domain/evidence";
import { healthFoodIdentityPresentation } from "../domain/healthFoodIdentity";
import { reviewPresentation } from "../domain/presentation";
import { formatDateTime, safeHttpUrl } from "../domain/product";
import { pageRegionClueValues } from "../domain/productFacts";
import { ProductThumbnail } from "./ProductThumbnail";
import { StatusBadge } from "./StatusBadge";

type ProductSnapshotSummaryProps = {
  workspace: SnapshotWorkspace;
  analysis: AnalysisStatePresentation;
  partitions: EvidencePartitions;
};

function shortText(value: string, limit = 78) {
  const clean = value.replace(/\s+/g, " ").trim();
  if (clean.length <= limit) return clean;
  return `${clean.slice(0, limit)}…`;
}

function distinct(values: string[]) {
  return [...new Set(values.filter(Boolean))];
}

export function ProductSnapshotSummary({
  workspace,
  analysis,
  partitions: _partitions,
}: ProductSnapshotSummaryProps) {
  const review = workspace.snapshot.readiness.reviewEligible
    ? reviewPresentation[workspace.review.status]
    : { label: "尚不可复核", tone: "neutral" as const };
  const healthFood = healthFoodIdentityPresentation[workspace.healthFoodIdentity.state];
  const claims = claimPresentation(
    workspace.claimAnalysisStatus,
    workspace.claimSignals,
  );
  const claimLabels = claimSignalLabels(workspace.claimSignals, 3);
  const productUrl = safeHttpUrl(workspace.snapshot.productUrl);
  const showHealthFoodStatus = workspace.healthFoodIdentity.state !== "no_indicator";
  const pageRegionClues = pageRegionClueValues(
    workspace.productFacts,
    workspace.snapshot.productName,
    workspace.snapshot.targetName || "",
  );

  const originSummary = workspace.declaredOrigin.state === "single"
    ? `标称产地：${workspace.declaredOrigin.values.join("、")}`
    : workspace.declaredOrigin.state === "conflict"
      ? "标称产地信息存在冲突"
      : pageRegionClues.length > 0
        ? `页面地区线索：${pageRegionClues.join("、")}`
        : "标称产地未明确";

  const claimSummary = claims.code === "with_claims"
    ? `${claimLabels.labels.join("、")}${claimLabels.remaining ? ` 等 ${workspace.claimSignals.length} 类` : ""} · 共 ${claims.mentionCount} 处表达`
    : claims.code === "zero"
      ? "当前未发现重点宣传线索"
      : claims.code === "not_generated"
        ? "页面宣传线索尚未完成"
        : "页面宣传线索分析失败";

  const firstMention = workspace.claimMentions[0] ?? null;
  const keyEvidence = firstMention
    ? `${claimSourceLabel(firstMention.sourceAssetType)}：“${shortText(firstMention.rawText)}”`
    : claims.code === "zero"
      ? "当前没有形成重点宣传线索证据"
      : claims.code === "with_claims"
        ? "已发现宣传线索，可在下方查看原始页面证据"
        : "尚无可展示的关键宣传证据";

  const suggestedSubstances = workspace.inspection.riskFindings.flatMap((finding) =>
    finding.substance_follow_ups.filter(
      (substance) => substance.follow_up_status === "suggest_testing",
    ),
  );
  const substanceNames = distinct(
    suggestedSubstances.map((substance) => substance.canonical_name),
  );
  const methodLabels = distinct(
    suggestedSubstances.flatMap((substance) =>
      substance.suggested_methods.map((method) =>
        method.method_no
          ? `${method.method_no} ${method.method_name}`
          : method.method_name,
      ),
    ),
  );

  let recommendationSummary: string;
  if (substanceNames.length > 0) {
    const shownSubstances = substanceNames.slice(0, 3).join("、");
    const remainingSubstances = substanceNames.length > 3
      ? ` 等 ${substanceNames.length} 项`
      : "";
    const methodSummary = methodLabels.length > 0
      ? `；检验方法：${shortText(methodLabels[0], 54)}${methodLabels.length > 1 ? ` 等 ${methodLabels.length} 项` : ""}`
      : "；当前暂无可直接引用的已核验方法";
    recommendationSummary = `建议重点关注：${shownSubstances}${remainingSubstances}${methodSummary}`;
  } else if (workspace.inspection.riskFindings.length > 0) {
    recommendationSummary = "已形成需要关注的方向，暂未关联到可直接建议的检测成分";
  } else if (claims.code === "with_claims") {
    recommendationSummary = "已发现页面宣传线索，当前知识库暂无可靠的针对性检测建议";
  } else if (claims.code === "zero") {
    recommendationSummary = "当前无针对性检测建议，可继续人工查看原始页面证据";
  } else if (analysis.code === "RECOMMENDATION_ERROR") {
    recommendationSummary = "检测建议暂不可用，页面证据和人工复核仍可继续使用";
  } else {
    recommendationSummary = "当前尚未形成针对性检测建议";
  }

  const reviewSummary = workspace.sampling.inCurrentList
    ? `${review.label} · 已纳入当前抽检清单`
    : review.label;

  return (
    <section className="snapshot-summary">
      <div className="snapshot-summary-heading">
        <ProductThumbnail
          src={workspace.snapshot.thumbnailUrl}
          alt={workspace.snapshot.productName || "商品图片"}
          variant="summary"
        />
        <div className="snapshot-summary-identity">
          <h3>{workspace.snapshot.productName || "未命名商品"}</h3>
          <p>{workspace.snapshot.shopName || "店铺未记录"} · {originSummary}</p>
          <small>
            采集于 {formatDateTime(workspace.snapshot.collectedAt)}
            {productUrl ? (
              <>
                {" · "}
                <a className="text-link" href={productUrl} target="_blank" rel="noreferrer">
                  查看原商品 <ExternalLink size={12} />
                </a>
              </>
            ) : null}
          </small>
        </div>
        <div className="snapshot-summary-statuses">
          <StatusBadge tone={claims.tone}>
            {claims.code === "with_claims"
              ? "发现宣传线索"
              : claims.code === "zero"
                ? "未发现重点线索"
                : claims.label}
          </StatusBadge>
          <StatusBadge tone={review.tone}>{review.label}</StatusBadge>
          {workspace.sampling.inCurrentList && (
            <StatusBadge tone="success">已在抽检清单</StatusBadge>
          )}
          {showHealthFoodStatus && (
            <StatusBadge tone={healthFood.tone}>{healthFood.summary}</StatusBadge>
          )}
        </div>
      </div>
      <dl className="snapshot-summary-grid">
        <div>
          <dt><ScanSearch size={15} />发现了什么宣传</dt>
          <dd>{claimSummary}</dd>
        </div>
        <div>
          <dt><FileSearch size={15} />关键页面证据</dt>
          <dd>{keyEvidence}</dd>
        </div>
        <div>
          <dt><FlaskConical size={15} />检测建议</dt>
          <dd>{recommendationSummary}</dd>
        </div>
        <div>
          <dt><ClipboardCheck size={15} />人工处理</dt>
          <dd>{reviewSummary}</dd>
        </div>
      </dl>
    </section>
  );
}
