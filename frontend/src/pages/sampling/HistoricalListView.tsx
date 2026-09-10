import {
  AlertCircle,
  Archive,
  Download,
  FileCheck2,
  RefreshCw,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import type {
  HistoricalSamplingList,
  HistoricalSamplingListPage,
  SamplingItem,
} from "../../api/contracts";
import {
  getSamplingHistories,
  getSamplingHistory,
} from "../../api/sampling";
import { EmptyState } from "../../components/EmptyState";
import { LoadingState } from "../../components/LoadingState";
import { StatusBadge } from "../../components/StatusBadge";
import { formatDateTime } from "../../domain/product";
import { SamplingListDrawer } from "./SamplingListDrawer";
import { SamplingListTable } from "./SamplingListTable";

type HistoricalListViewProps = {
  selectedListId?: string;
};

export function HistoricalListView({ selectedListId }: HistoricalListViewProps) {
  const [page, setPage] = useState<HistoricalSamplingListPage | null>(null);
  const [detail, setDetail] = useState<HistoricalSamplingList | null>(null);
  const [selectedItem, setSelectedItem] = useState<SamplingItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");
  const [detailError, setDetailError] = useState("");

  const loadPage = useCallback(async () => {
    setError("");
    setLoading(true);
    try {
      setPage(await getSamplingHistories());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "历史清单加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadPage();
  }, [loadPage]);

  useEffect(() => {
    setSelectedItem(null);
    setDetail(null);
    setDetailError("");
    if (!selectedListId) return;
    const controller = new AbortController();
    setDetailLoading(true);
    getSamplingHistory(selectedListId, controller.signal)
      .then(setDetail)
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setDetailError(
            reason instanceof Error ? reason.message : "历史清单详情加载失败",
          );
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setDetailLoading(false);
      });
    return () => controller.abort();
  }, [selectedListId]);

  if (loading) return <LoadingState label="正在读取历史抽检清单" />;
  if (error) {
    return (
      <EmptyState
        icon={AlertCircle}
        title="历史清单加载失败"
        description={error}
        action={<button type="button" className="primary-button" onClick={() => void loadPage()}><RefreshCw size={15} />重试</button>}
      />
    );
  }
  if (!page?.lists.length) {
    return (
      <EmptyState
        icon={Archive}
        title="暂无历史抽检清单"
        description="当前清单导出成功后，会在这里生成不随商品后续变化的只读记录。"
      />
    );
  }

  return (
    <div className="sampling-history-layout" data-detail-open={Boolean(selectedListId)}>
      <section className="sampling-history-index" aria-label="历史抽检清单">
        <div className="sampling-section-heading">
          <div>
            <h2>导出记录</h2>
            <p>共 {page.count} 份冻结清单</p>
          </div>
          <StatusBadge tone="info">只读档案</StatusBadge>
        </div>
        <div className="history-card-list">
          {page.lists.map((history) => (
            <article key={history.listId} data-selected={selectedListId === history.listId}>
              <a href={`#/sampling/history/${encodeURIComponent(history.listId)}`}>
                <span className="history-card-icon"><FileCheck2 size={17} /></span>
                <span>
                  <strong>{history.listId}</strong>
                  <small>{formatDateTime(history.exportedAt)} · {history.itemCount} 件商品</small>
                </span>
                <StatusBadge tone="success">已冻结</StatusBadge>
              </a>
              <a className="icon-button" href={history.downloadUrl} aria-label={`下载 ${history.listId}`} title="重新下载 Excel">
                <Download size={15} />
              </a>
            </article>
          ))}
        </div>
      </section>

      {selectedListId && (
        <section className="sampling-history-detail" aria-label="历史清单详情">
          {detailLoading ? <LoadingState label="正在读取冻结详情" /> : detailError ? (
            <EmptyState
              icon={AlertCircle}
              title="历史清单无法读取"
              description={detailError}
              action={<a className="secondary-button" href="#/sampling/history">返回历史列表</a>}
            />
          ) : detail ? (
            <>
              <div className="history-detail-heading">
                <div>
                  <a href="#/sampling/history">← 返回全部历史</a>
                  <h2>{detail.listId}</h2>
                  <p>{formatDateTime(detail.exportedAt)} · {detail.itemCount} 件商品 · 导出内容已冻结</p>
                </div>
                <a className="primary-button" href={detail.downloadUrl}>
                  <Download size={15} />下载 Excel
                </a>
              </div>
              <div className="readonly-inline-note">
                <FileCheck2 size={16} />
                以下展示导出时保存的 Evidence、Review 与抽检辅助建议，不会读取最新快照重算。
              </div>
              <div className="sampling-history-table-card">
                <SamplingListTable
                  items={detail.items}
                  selectedProductId={selectedItem?.productId}
                  readOnly
                  onSelect={setSelectedItem}
                />
              </div>
              <p className="sampling-disclaimer compact-disclaimer">{detail.disclaimer}</p>
            </>
          ) : null}
        </section>
      )}

      {selectedItem && (
        <div className="sampling-detail-overlay">
          <SamplingListDrawer
            item={selectedItem}
            historical
            onClose={() => setSelectedItem(null)}
          />
        </div>
      )}
    </div>
  );
}
