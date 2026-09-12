import { ImageOff } from "lucide-react";
import { useEffect, useState } from "react";

import { productThumbnailSource } from "../domain/product";

type ProductThumbnailProps = {
  src: string | null | undefined;
  alt: string;
  variant?: "list" | "summary" | "evidence";
  onPreview?: () => void;
};

export function ProductThumbnail({
  src,
  alt,
  variant = "list",
  onPreview,
}: ProductThumbnailProps) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [src]);
  const resolved = productThumbnailSource(src, failed);
  const content = resolved ? (
    <img src={resolved} alt={alt} onError={() => setFailed(true)} />
  ) : (
    <span className="product-thumbnail-placeholder" role="img" aria-label={`${alt}暂无图片`}>
      <ImageOff size={variant === "summary" ? 24 : 18} aria-hidden="true" />
    </span>
  );

  if (onPreview && resolved) {
    return (
      <button
        type="button"
        className="product-thumbnail product-thumbnail-button"
        data-variant={variant}
        onClick={onPreview}
        aria-label={`预览${alt}`}
      >
        {content}
      </button>
    );
  }
  return (
    <span className="product-thumbnail" data-variant={variant}>
      {content}
    </span>
  );
}
