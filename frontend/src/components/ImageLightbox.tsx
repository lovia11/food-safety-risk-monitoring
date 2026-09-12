import { ChevronLeft, ChevronRight, Minus, Plus, RotateCcw } from "lucide-react";
import { useEffect, useState } from "react";

import type { EvidenceSourceGroup } from "../domain/evidence";
import {
  LIGHTBOX_ZOOM_STEP,
  clampLightboxZoom,
  moveLightboxIndex,
} from "../domain/media";
import { Modal } from "./Modal";

export type LightboxImage = {
  path: string;
  url: string;
  label: string;
  evidenceGroups: EvidenceSourceGroup[];
};

type ImageLightboxProps = {
  images: LightboxImage[];
  activeIndex: number;
  onSelect: (index: number) => void;
  onClose: () => void;
};

export function ImageLightbox({
  images,
  activeIndex,
  onSelect,
  onClose,
}: ImageLightboxProps) {
  const [zoom, setZoom] = useState(1);
  const active = images[activeIndex];

  useEffect(() => setZoom(1), [activeIndex]);
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (images.length < 2) return;
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        onSelect(moveLightboxIndex(activeIndex, -1, images.length));
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        onSelect(moveLightboxIndex(activeIndex, 1, images.length));
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [activeIndex, images.length, onSelect]);

  if (!active) return null;
  const changeImage = (delta: number) => {
    onSelect(moveLightboxIndex(activeIndex, delta, images.length));
  };

  return (
    <Modal title={active.label} className="image-lightbox" onClose={onClose}>
      <div className="lightbox-toolbar">
        <span>{activeIndex + 1} / {images.length}</span>
        <div>
          <button
            type="button"
            className="icon-button"
            onClick={() => setZoom((value) => clampLightboxZoom(value - LIGHTBOX_ZOOM_STEP))}
            aria-label="缩小图片"
            title="缩小图片"
          ><Minus size={17} /></button>
          <output aria-label="当前缩放比例">{Math.round(zoom * 100)}%</output>
          <button
            type="button"
            className="icon-button"
            onClick={() => setZoom((value) => clampLightboxZoom(value + LIGHTBOX_ZOOM_STEP))}
            aria-label="放大图片"
            title="放大图片"
          ><Plus size={17} /></button>
          <button
            type="button"
            className="icon-button"
            onClick={() => setZoom(1)}
            aria-label="重置图片缩放"
            title="重置图片缩放"
          ><RotateCcw size={16} /></button>
        </div>
      </div>
      <div className="lightbox-layout">
        <div className="lightbox-stage">
          {images.length > 1 && (
            <button
              type="button"
              className="lightbox-nav lightbox-nav-previous"
              onClick={() => changeImage(-1)}
              aria-label="上一张图片"
            ><ChevronLeft size={22} /></button>
          )}
          <div className="lightbox-media">
            <img
              src={active.url}
              alt={active.label}
              style={{
                width: zoom === 1 ? "auto" : `${zoom * 100}%`,
                maxWidth: zoom === 1 ? "100%" : "none",
                maxHeight: zoom === 1 ? "calc(100vh - 210px)" : "none",
              }}
            />
          </div>
          {images.length > 1 && (
            <button
              type="button"
              className="lightbox-nav lightbox-nav-next"
              onClick={() => changeImage(1)}
              aria-label="下一张图片"
            ><ChevronRight size={22} /></button>
          )}
        </div>
        <aside className="lightbox-evidence" aria-label="当前图片对应证据">
          <h3>当前图片对应 Evidence</h3>
          {active.evidenceGroups.length ? active.evidenceGroups.map((group) => (
            <section key={group.key}>
              <strong>{group.sourceLabel}</strong>
              <span>{group.recordCount} 条命中</span>
              {group.snippets.slice(0, 3).map((snippet) => (
                <p key={snippet.evidenceIds.join("|")}>{snippet.text}</p>
              ))}
              {group.snippets.length > 3 && <small>另有 {group.snippets.length - 3} 条</small>}
            </section>
          )) : (
            <p className="lightbox-empty">当前规则未在这张图片上形成结构化 Evidence。</p>
          )}
          <code>{active.path}</code>
        </aside>
      </div>
    </Modal>
  );
}
