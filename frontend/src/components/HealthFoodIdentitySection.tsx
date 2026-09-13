import { ExternalLink, Eye, FileSearch, FileText, ShieldCheck } from "lucide-react";
import { useMemo, useState } from "react";

import type {
  HealthFoodIdentity,
  HealthFoodIdentitySource,
  ProductAssets,
} from "../api/contracts";
import { evidenceAssetKey } from "../domain/evidence";
import {
  healthFoodArtifactPath,
  healthFoodIdentityPresentation,
  healthFoodSourceLabel,
} from "../domain/healthFoodIdentity";
import { formatDateTime, runFileUrl, safeHttpUrl } from "../domain/product";
import { ImageLightbox, type LightboxImage } from "./ImageLightbox";
import { Modal } from "./Modal";
import { OcrTextModal } from "./OcrTextModal";
import { StatusBadge } from "./StatusBadge";

type Props = {
  identity: HealthFoodIdentity;
  assets: ProductAssets;
  runId: string;
  productId: string;
};

function sourceAsset(source: HealthFoodIdentitySource, assets: ProductAssets) {
  if (!source.sourcePath) return null;
  const key = evidenceAssetKey(source.sourcePath);
  if (!key) return null;
  return assets.ocrItems.find((item) => (
    evidenceAssetKey(item.textPath) === key || evidenceAssetKey(item.jsonPath) === key
  )) || null;
}

export function HealthFoodIdentitySection({ identity, assets, runId, productId }: Props) {
  const [pageEvidenceOpen, setPageEvidenceOpen] = useState(false);
  const [officialOpen, setOfficialOpen] = useState(false);
  const [sourceText, setSourceText] = useState<{ url: string; title: string } | null>(null);
  const [lightbox, setLightbox] = useState<LightboxImage[] | null>(null);
  const presentation = healthFoodIdentityPresentation[identity.state];
  const record = identity.registryRecord;
  const officialUrl = safeHttpUrl(identity.officialSource.reference);
  const pageSources = useMemo(() => {
    const items: Array<HealthFoodIdentitySource & { key: string; value: string }> = [
      ...identity.identifiers.map((item) => ({ ...item, key: item.candidateId, value: item.normalizedValue || item.rawValue })),
      ...identity.clues.map((item) => ({ ...item, key: item.clueId, value: item.text })),
      ...identity.productMatch.pageProductNames.map((item, index) => ({ ...item, key: `name-${index}-${item.sourcePath}`, value: `产品名称：${item.value}` })),
    ];
    return items;
  }, [identity]);

  const openSourceText = (source: HealthFoodIdentitySource) => {
    const artifactPath = healthFoodArtifactPath(source.sourcePath);
    if (!artifactPath) return;
    const relative = `products/${productId}/${artifactPath}`;
    const url = runFileUrl(runId, relative);
    if (!url) return;
    setPageEvidenceOpen(false);
    setSourceText({ url, title: `${healthFoodSourceLabel(source.sourceType)} · 身份页面依据` });
  };

  const openImage = (source: HealthFoodIdentitySource) => {
    const asset = sourceAsset(source, assets);
    if (!asset?.imagePath) return;
    const url = runFileUrl(runId, asset.imagePath);
    if (!url) return;
    setPageEvidenceOpen(false);
    setLightbox([{ path: asset.imagePath, url, label: "保健食品身份页面依据", evidenceGroups: [] }]);
  };

  return (
    <section className="detail-section health-food-identity" data-state={identity.state}>
      <div className="health-food-heading">
        <h3><ShieldCheck size={17} />保健食品身份</h3>
        <StatusBadge tone={presentation.tone}>{presentation.label}</StatusBadge>
      </div>
      <p className="health-food-message">{presentation.message}</p>

      {identity.identifiers.length > 0 && (
        <div className="health-food-identifiers">
          <span>页面识别编号</span>
          {identity.identifiers.map((item) => (
            <code key={item.candidateId}>{item.normalizedValue || item.rawValue}</code>
          ))}
        </div>
      )}

      {record && (
        <dl className="health-food-record-summary">
          <div><dt>注册/备案号</dt><dd>{record.identifier}</dd></div>
          <div><dt>登记产品名称</dt><dd>{record.productName || "官方未提供"}</dd></div>
          <div><dt>登记主体</dt><dd>{record.registrantOrFiler || "官方未提供"}</dd></div>
          <div>
            <dt>登记保健功能</dt>
            <dd>{record.officialHealthFunctions.length > 0 ? (
              <ul>{record.officialHealthFunctions.map((item) => <li key={item}>{item}</li>)}</ul>
            ) : "官方当前响应未提供"}</dd>
          </div>
          <div><dt>官方查询时间</dt><dd>{formatDateTime(record.retrievedAt)}</dd></div>
        </dl>
      )}

      <div className="health-food-actions">
        {pageSources.length > 0 && (
          <button type="button" onClick={() => setPageEvidenceOpen(true)}>
            <FileSearch size={14} /> 查看页面依据
          </button>
        )}
        {record && (
          <button type="button" onClick={() => setOfficialOpen(true)}>
            <ShieldCheck size={14} /> 查看官方依据
          </button>
        )}
      </div>

      {pageEvidenceOpen && (
        <Modal title="保健食品身份 · 页面依据" className="health-food-modal" onClose={() => setPageEvidenceOpen(false)}>
          <div className="health-food-source-list">
            <p>以下仅为当前商品页面的身份线索，与官方登记依据分开保留。</p>
            {pageSources.map((source) => {
              const asset = sourceAsset(source, assets);
              return (
                <article key={source.key}>
                  <header><strong>{source.value}</strong><span>[{healthFoodSourceLabel(source.sourceType)}]</span></header>
                  <blockquote>{source.sourceText || source.value}</blockquote>
                  <code>{source.sourcePath || "来源路径未记录"}</code>
                  <div>
                    {asset?.imagePath && <button type="button" onClick={() => openImage(source)}><Eye size={14} /> 在原图中查看</button>}
                    {healthFoodArtifactPath(source.sourcePath) && (
                      <button type="button" onClick={() => openSourceText(source)}><FileText size={14} /> 查看来源文件</button>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        </Modal>
      )}

      {officialOpen && record && (
        <Modal title="保健食品身份 · 官方登记依据" className="health-food-modal" onClose={() => setOfficialOpen(false)}>
          <div className="health-food-official-record">
            <p><strong>{identity.officialSource.name}</strong></p>
            <dl>
              <div><dt>注册/备案号</dt><dd>{record.identifier}</dd></div>
              <div><dt>产品名称</dt><dd>{record.productName || "—"}</dd></div>
              <div><dt>登记主体</dt><dd>{record.registrantOrFiler || "—"}</dd></div>
              <div><dt>主体地址</dt><dd>{record.registrantAddress || "—"}</dd></div>
              <div><dt>批准/备案日期</dt><dd>{record.issueOrFilingDate || "—"}</dd></div>
              <div><dt>有效期至</dt><dd>{record.validUntil || "—"}</dd></div>
              <div><dt>规格</dt><dd>{record.specification || "—"}</dd></div>
              <div><dt>登记保健功能</dt><dd>{record.officialHealthFunctions.length ? record.officialHealthFunctions.join("；") : "—"}</dd></div>
              <div><dt>功能/标志性成分</dt><dd>{record.functionalOrMarkerIngredients.length ? record.functionalOrMarkerIngredients.join("；") : "—"}</dd></div>
              <div><dt>查询时间</dt><dd>{formatDateTime(record.retrievedAt)}</dd></div>
            </dl>
            {officialUrl && <a className="text-link" href={officialUrl} target="_blank" rel="noreferrer">打开官方来源 <ExternalLink size={14} /></a>}
          </div>
        </Modal>
      )}

      {sourceText && <OcrTextModal url={sourceText.url} title={sourceText.title} onClose={() => setSourceText(null)} />}
      {lightbox && <ImageLightbox images={lightbox} activeIndex={0} onSelect={() => undefined} onClose={() => setLightbox(null)} />}
    </section>
  );
}
