import { Eye, FileSearch, FileText } from "lucide-react";
import { useMemo, useState } from "react";

import type { DeclaredOrigin, ProductAssets, ProductFact } from "../api/contracts";
import { evidenceAssetKey } from "../domain/evidence";
import { runFileUrl } from "../domain/product";
import {
  declaredOriginText,
  productFactArtifactPath,
  productFactSourceLabel,
  productFactSourcesForValue,
} from "../domain/productFacts";
import { ImageLightbox, type LightboxImage } from "./ImageLightbox";
import { Modal } from "./Modal";
import { OcrTextModal } from "./OcrTextModal";
import { StatusBadge } from "./StatusBadge";

type Props = {
  origin: DeclaredOrigin;
  assets: ProductAssets;
  runId: string;
  productId: string;
};

function sourceAsset(source: ProductFact, assets: ProductAssets) {
  const key = evidenceAssetKey(source.sourcePath);
  if (!key) return null;
  return assets.ocrItems.find((item) => (
    evidenceAssetKey(item.textPath) === key || evidenceAssetKey(item.jsonPath) === key
  )) || null;
}

export function DeclaredOriginFact({ origin, assets, runId, productId }: Props) {
  const [traceOpen, setTraceOpen] = useState(false);
  const [sourceText, setSourceText] = useState<{ url: string; title: string } | null>(null);
  const [lightbox, setLightbox] = useState<LightboxImage[] | null>(null);
  const sourceTypes = [...new Set(origin.sources.map((source) => source.sourceType))];
  const sourceCount = origin.sources.length;
  const valueGroups = useMemo(() => origin.values.map((value) => ({
    value,
    sources: productFactSourcesForValue(origin, value),
  })), [origin]);

  if (origin.state === "none" || origin.values.length === 0) return <>—</>;

  const openSourceText = (source: ProductFact) => {
    const artifact = productFactArtifactPath(source);
    const relative = `products/${productId}/${artifact}`;
    const url = runFileUrl(runId, relative);
    if (url) {
      setTraceOpen(false);
      setSourceText({ url, title: `${productFactSourceLabel(source.sourceType)} · 来源文本` });
    }
  };
  const openImage = (source: ProductFact) => {
    const asset = sourceAsset(source, assets);
    if (!asset?.imagePath) return;
    const url = runFileUrl(runId, asset.imagePath);
    if (!url) return;
    const related = origin.sources.filter((item) => (
      evidenceAssetKey(item.sourcePath) === evidenceAssetKey(source.sourcePath)
    ));
    setTraceOpen(false);
    setLightbox([{
      path: asset.imagePath,
      url,
      label: `商品标称产地依据 · ${source.normalizedValue}`,
      evidenceGroups: [],
      factSources: related,
    }]);
  };

  return (
    <div className="declared-origin-fact" data-state={origin.state}>
      <div className="declared-origin-summary">
        {origin.state === "conflict" ? (
          <StatusBadge tone="warning">存在多个声明</StatusBadge>
        ) : <strong>{declaredOriginText(origin)}</strong>}
        <span>
          {sourceCount > 1 ? `${sourceCount} 处页面依据` : productFactSourceLabel(sourceTypes[0])}
        </span>
        <button type="button" onClick={() => setTraceOpen(true)}>
          <FileSearch size={13} /> 查看依据
        </button>
      </div>
      {origin.state === "conflict" && (
        <ul className="declared-origin-values">
          {valueGroups.map(({ value, sources }) => (
            <li key={value}>
              <strong>{value}</strong>
              {[...new Set(sources.map((source) => productFactSourceLabel(source.sourceType)))].map(
                (label) => <span key={label}>[{label}]</span>,
              )}
            </li>
          ))}
        </ul>
      )}
      {traceOpen && (
        <Modal title="商品标称产地依据" className="product-fact-modal" onClose={() => setTraceOpen(false)}>
          <div className="product-fact-traces">
            <p className="product-fact-note">页面声明按来源保留；多个值并存时不自动判断哪一个正确。</p>
            {origin.sources.map((source) => {
              const asset = sourceAsset(source, assets);
              return (
                <article key={source.factId}>
                  <header>
                    <strong>{source.normalizedValue}</strong>
                    <span>[{productFactSourceLabel(source.sourceType)}]</span>
                  </header>
                  <blockquote>{source.sourceText}</blockquote>
                  <code>{source.sourcePath}</code>
                  <div>
                    {asset?.imagePath && (
                      <button type="button" onClick={() => openImage(source)}>
                        <Eye size={14} /> 在原图中查看
                      </button>
                    )}
                    <button type="button" onClick={() => openSourceText(source)}>
                      <FileText size={14} /> 查看来源文件
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        </Modal>
      )}
      {sourceText && (
        <OcrTextModal
          url={sourceText.url}
          title={sourceText.title}
          onClose={() => setSourceText(null)}
        />
      )}
      {lightbox && (
        <ImageLightbox
          images={lightbox}
          activeIndex={0}
          onSelect={() => undefined}
          onClose={() => setLightbox(null)}
        />
      )}
    </div>
  );
}
