import { AlertCircle } from "lucide-react";
import { useEffect, useState } from "react";

import { LoadingState } from "./LoadingState";
import { Modal } from "./Modal";

type OcrTextModalProps = {
  url: string;
  title: string;
  onClose: () => void;
};

export function OcrTextModal({ url, title, onClose }: OcrTextModalProps) {
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    fetch(url, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error(`OCR 全文读取失败（${response.status}）`);
        return response.text();
      })
      .then(setText)
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : "OCR 全文读取失败");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [url]);

  return (
    <Modal title={title} className="ocr-text-modal" onClose={onClose}>
      <div className="ocr-text-body">
        {loading ? <LoadingState label="正在读取 OCR 全文" /> : error ? (
          <div className="inline-message" data-tone="danger">
            <AlertCircle size={17} /> {error}
          </div>
        ) : <pre>{text || "该文件没有可展示文本。"}</pre>}
      </div>
    </Modal>
  );
}
