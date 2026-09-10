import {
  AlertCircle,
  Archive,
  Download,
  FileSpreadsheet,
  PackageOpen,
  RefreshCw,
  X,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import type { SamplingItem, SamplingList } from "../../api/contracts";
import {
  addSamplingItem,
  exportSamplingList,
  getSamplingList,
  removeSamplingItem,
} from "../../api/sampling";
import { useAppState } from "../../app/AppState";
import { EmptyState } from "../../components/EmptyState";
import { LoadingState } from "../../components/LoadingState";
import { useToast } from "../../components/ToastProvider";
import { PageHeader } from "../../layout/PageHeader";
import { HistoricalListView } from "./HistoricalListView";
import { SamplingListDrawer } from "./SamplingListDrawer";
import { SamplingListTable } from "./SamplingListTable";

type SamplingListPageProps = {
  view: "current" | "history";
  listId?: string;
};

type ExportDialogProps = {
  count: number;
  exporting: boolean;
  onCancel: () => void;
  onConfirm: () => void;
};

function ExportDialog({
  count,
  exporting,
  onCancel,
  onConfirm,
}: ExportDialogProps) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const restoreTarget = document.activeElement as HTMLElement | null;
    const dialog = ref.current;
    if (dialog && !dialog.open) dialog.showModal();
    return () => {
      if (restoreTarget?.isConnected) restoreTarget.focus();
    };
  }, []);

  return (
    <dialog
      ref={ref}
      className="sampling-export-dialog"
      aria-labelledby="sampling-export-title"
      onCancel={(event) => {
        event.preventDefault();
        if (!exporting) onCancel();
      }}
    >
      <div className="export-dialog-heading">
        <span><FileSpreadsheet size={19} /></span>
        <div>
          <h2 id="sampling-export-title">导出当前抽检辅助清单</h2>
          <p>本次共 {count} 件商品</p>
        </div>
        <button type="button" className="icon-button" onClick={onCancel} disabled={exporting} aria-label="关闭导出确认" title="关闭">
          <X size={17} />
        </button>
      </div>
      <p>
        将生成 Excel，同时冻结一份只读历史清单并清空当前 Membership。
        已完成的人工 Review、页面 Evidence 和抽检辅助建议均不会改变。
      </p>
      <div className="export-dialog-actions">
        <button type="button" className="secondary-button" onClick={onCancel} disabled={exporting} autoFocus>取消</button>
        <button type="button" className="primary-button" onClick={onConfirm} disabled={exporting}>
          <Download size={15} />{exporting ? "正在冻结与生成…" : "确认导出"}
        </button>
      </div>
    </dialog>
  );
}

export function SamplingListPage({ view, listId }: SamplingListPageProps) {
  const [data, setData] = useState<SamplingList | null>(null);
  const [selectedItem, setSelectedItem] = useState<SamplingItem | null>(null);
  const [loading, setLoading] = useState(view === "current");
  const [error, setError] = useState("");
  const [confirmingExport, setConfirmingExport] = useState(false);
  const [exporting, setExporting] = useState(false);
  const { refreshSamplingCount, setCurrentSamplingCount } = useAppState();
  const { pushToast } = useToast();

  const load = useCallback(async () => {
    setError("");
    setLoading(true);
    try {
      setData(await getSamplingList());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "当前清单加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (view === "current") void load();
  }, [load, view]);

  const remove = async (productId: string) => {
    try {
      const removed = await removeSamplingItem(productId);
      if (selectedItem?.productId === productId) setSelectedItem(null);
      await Promise.all([load(), refreshSamplingCount()]);
      pushToast("已移出当前抽检清单，人工复核结论保持不变", "info", {
        label: "撤销",
        run: async () => {
          await addSamplingItem(
            removed.productId,
            removed.sourceSnapshotId,
            removed.addedFrom,
          );
          await Promise.all([load(), refreshSamplingCount()]);
          pushToast("已恢复到当前抽检清单", "success");
        },
      });
    } catch (reason) {
      pushToast(reason instanceof Error ? reason.message : "移出清单失败", "danger");
    }
  };

  const confirmExport = async () => {
    setExporting(true);
    try {
      const history = await exportSamplingList();
      setCurrentSamplingCount(0);
      setConfirmingExport(false);
      pushToast(`已生成历史清单 ${history.listId}`, "success", {
        label: "下载 Excel",
        run: () => {
          window.location.assign(history.downloadUrl);
        },
      });
      window.location.hash = `#/sampling/history/${encodeURIComponent(history.listId)}`;
    } catch (reason) {
      pushToast(reason instanceof Error ? reason.message : "导出抽检清单失败", "danger");
    } finally {
      setExporting(false);
    }
  };

  const currentContent = loading ? (
    <LoadingState label="正在读取当前抽检清单" />
  ) : error ? (
    <EmptyState
      icon={AlertCircle}
      title="当前清单加载失败"
      description={error}
      action={<button type="button" className="primary-button" onClick={() => void load()}><RefreshCw size={15} />重试</button>}
    />
  ) : !data?.items.length ? (
    <EmptyState
      icon={PackageOpen}
      title="当前抽检清单为空"
      description="在商品总览或排查工作区完成人工复核并纳入后，商品会显示在这里。"
      action={<a className="primary-button" href="#/products">前往商品总览</a>}
    />
  ) : (
    <div className="sampling-current-workspace" data-detail-open={Boolean(selectedItem)}>
      <section className="sampling-table-card" aria-label="当前抽检清单表格">
        <div className="sampling-section-heading">
          <div><h2>当前条目</h2><p>共 {data.count} 件商品，一件 Product 一条</p></div>
          <span>导出后当前清单将清空</span>
        </div>
        <SamplingListTable
          items={data.items}
          selectedProductId={selectedItem?.productId}
          onSelect={setSelectedItem}
          onRemove={(productId) => void remove(productId)}
        />
      </section>
      {selectedItem && (
        <SamplingListDrawer item={selectedItem} onClose={() => setSelectedItem(null)} />
      )}
    </div>
  );

  return (
    <div className="page-frame sampling-list-page" data-view={view}>
      <PageHeader
        eyebrow="抽检管理"
        title="抽检辅助清单"
        description="当前清单管理 Product Membership；历史清单以导出时冻结事实供查看与重新下载。"
        actions={view === "current" && data?.items.length ? (
          <button type="button" className="primary-button" onClick={() => setConfirmingExport(true)}>
            <FileSpreadsheet size={16} />导出当前抽检辅助清单（{data.count}）
          </button>
        ) : undefined}
      />
      <nav className="sampling-tabs" aria-label="抽检清单分类">
        <a href="#/sampling" aria-current={view === "current" ? "page" : undefined} data-active={view === "current"}>
          当前清单 {data && view === "current" ? <span>{data.count}</span> : null}
        </a>
        <a href="#/sampling/history" aria-current={view === "history" ? "page" : undefined} data-active={view === "history"}>
          <Archive size={15} />历史清单
        </a>
      </nav>
      <div className="sampling-page-content">
        {view === "history" ? <HistoricalListView selectedListId={listId} /> : currentContent}
      </div>
      {confirmingExport && (
        <ExportDialog
          count={data?.count || 0}
          exporting={exporting}
          onCancel={() => setConfirmingExport(false)}
          onConfirm={() => void confirmExport()}
        />
      )}
    </div>
  );
}
