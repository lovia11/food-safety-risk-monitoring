import { AlertCircle, FlaskConical, PackageOpen, RefreshCw, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import type { SamplingList } from "../../api/contracts";
import { addSamplingItem, getSamplingList, removeSamplingItem } from "../../api/products";
import { useAppState } from "../../app/AppState";
import { EmptyState } from "../../components/EmptyState";
import { LoadingState } from "../../components/LoadingState";
import { useToast } from "../../components/ToastProvider";
import { formatDateTime } from "../../domain/product";
import { PageHeader } from "../../layout/PageHeader";

export function CurrentSamplingPage() {
  const [data, setData] = useState<SamplingList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const { refreshSamplingCount } = useAppState();
  const { pushToast } = useToast();

  const load = useCallback(async () => {
    setError("");
    try { setData(await getSamplingList()); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "当前清单加载失败"); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void load(); }, [load]);

  const remove = async (productId: string) => {
    try {
      const removed = await removeSamplingItem(productId);
      await Promise.all([load(), refreshSamplingCount()]);
      pushToast("已移出当前抽检清单，人工复核结论保持不变", "info", {
        label: "撤销",
        run: async () => {
          await addSamplingItem(removed.productId, removed.sourceSnapshotId, removed.addedFrom);
          await Promise.all([load(), refreshSamplingCount()]);
          pushToast("已恢复到当前抽检清单", "success");
        },
      });
    } catch (reason) {
      pushToast(reason instanceof Error ? reason.message : "移出清单失败", "danger");
    }
  };

  return (
    <div className="page-frame sampling-page">
      <PageHeader eyebrow="抽检管理" title="当前抽检清单" description="这里仅维护当前清单关系；单独移出不会改变已完成的人工复核结论。" />
      {loading ? <LoadingState label="正在读取当前抽检清单" /> : error ? <EmptyState icon={AlertCircle} title="当前清单加载失败" description={error} action={<button type="button" className="primary-button" onClick={() => { setLoading(true); void load(); }}><RefreshCw size={15} />重试</button>} /> : !data?.items.length ? <EmptyState icon={PackageOpen} title="当前抽检清单为空" description="在商品总览或排查工作区完成复核并加入后，商品会显示在这里。" action={<a className="primary-button" href="#/products">前往商品总览</a>} /> : (
        <div className="current-sampling-list">
          {data.items.map((item) => (
            <article key={item.productId} className="sampling-item-card">
              <span className="sampling-item-icon"><FlaskConical size={18} /></span>
              <div><h2>{item.productName || item.productId}</h2><p>{item.shopName || "店铺未记录"} · 加入于 {formatDateTime(item.addedAt)}</p><small>依据 Snapshot {item.sourceSnapshotId}</small></div>
              <a className="secondary-button" href={`#/products/${encodeURIComponent(item.productId)}`}>查看商品</a>
              <button type="button" className="danger-button" onClick={() => void remove(item.productId)}><Trash2 size={15} />移出</button>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
