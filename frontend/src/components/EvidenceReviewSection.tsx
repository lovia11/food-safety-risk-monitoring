import { FileSearch } from "lucide-react";
import { useMemo, useState } from "react";

import type { Evidence, ProductAssets } from "../api/contracts";
import {
  evidenceAssetKey,
  evidenceGroupAssets,
  groupEvidence,
  partitionEvidenceGroups,
  type EvidenceSourceGroup,
} from "../domain/evidence";
import { runFileUrl } from "../domain/product";
import { EvidenceGroupCard } from "./EvidenceGroupCard";
import { ImageLightbox, type LightboxImage } from "./ImageLightbox";
import { OcrTextModal } from "./OcrTextModal";

type EvidenceReviewSectionProps = {
  evidence: Evidence[];
  assets: ProductAssets;
  runId: string;
};

function groupsForPath(
  groups: EvidenceSourceGroup[],
  path: string,
  assets: ProductAssets,
) {
  const assetKey = evidenceAssetKey(path);
  return groups.filter((group) => (
    (assetKey && group.assetKey === assetKey)
    || evidenceGroupAssets(group, assets).imagePath === path
    || group.sourcePaths.some((sourcePath) => sourcePath === path)
  ));
}

function uniqueAssetPaths(assets: ProductAssets) {
  return [...new Set([
    ...assets.originalImages.map((image) => image.path),
    assets.overview,
    ...assets.screenshots,
  ].filter((path): path is string => Boolean(path)))];
}

export function EvidenceReviewSection({
  evidence,
  assets,
  runId,
}: EvidenceReviewSectionProps) {
  const groups = useMemo(() => groupEvidence(evidence), [evidence]);
  const partitions = useMemo(() => partitionEvidenceGroups(groups), [groups]);
  const [activeImageIndex, setActiveImageIndex] = useState<number | null>(null);
  const [ocrText, setOcrText] = useState<{ url: string; title: string } | null>(null);
  const images = useMemo<LightboxImage[]>(() => (
    uniqueAssetPaths(assets).map((path, index) => ({
      path,
      url: runFileUrl(runId, path)!,
      label: `商品页面图片 ${index + 1}`,
      evidenceGroups: groupsForPath(groups, path, assets),
    }))
  ), [assets, groups, runId]);

  const previewPath = (path: string) => {
    const index = images.findIndex((image) => image.path === path);
    if (index >= 0) setActiveImageIndex(index);
  };
  const renderGroups = (items: EvidenceSourceGroup[], secondary = false) => (
    <div className="evidence-group-list">
      {items.map((group) => (
        <EvidenceGroupCard
          key={group.key}
          group={group}
          assets={assets}
          runId={runId}
          secondary={secondary}
          onPreview={previewPath}
          onReadText={(url, title) => setOcrText({ url, title })}
        />
      ))}
    </div>
  );

  return (
    <section className="detail-section evidence-section">
      <h3><FileSearch size={17} />页面证据</h3>
      {groups.length === 0 ? (
        <div className="inline-message">
          已完成分析，但当前规则没有形成结构化页面 Evidence。
        </div>
      ) : (
        <>
          <details open>
            <summary>
              商家管理内容 · 主要证据（{partitions.seller.reduce((sum, group) => sum + group.recordCount, 0)}）
            </summary>
            {partitions.seller.length > 0
              ? renderGroups(partitions.seller)
              : <p className="section-description evidence-empty">没有商家管理内容证据。</p>}
          </details>
          {partitions.ugc.length > 0 && (
            <details className="evidence-auxiliary">
              <summary>
                用户生成内容 · 辅助线索（{partitions.ugc.reduce((sum, group) => sum + group.recordCount, 0)}）
              </summary>
              {renderGroups(partitions.ugc, true)}
            </details>
          )}
          {partitions.excluded.length > 0 && (
            <details className="evidence-excluded">
              <summary>
                已排除页面噪声（{partitions.excluded.reduce((sum, group) => sum + group.recordCount, 0)}）
              </summary>
              {renderGroups(partitions.excluded, true)}
            </details>
          )}
        </>
      )}
      {activeImageIndex !== null && (
        <ImageLightbox
          images={images}
          activeIndex={activeImageIndex}
          onSelect={setActiveImageIndex}
          onClose={() => setActiveImageIndex(null)}
        />
      )}
      {ocrText && (
        <OcrTextModal
          url={ocrText.url}
          title={ocrText.title}
          onClose={() => setOcrText(null)}
        />
      )}
    </section>
  );
}
