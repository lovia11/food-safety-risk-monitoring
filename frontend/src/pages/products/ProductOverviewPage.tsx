import { AlertCircle, FilterX, PackageSearch, RefreshCw, Search } from "lucide-react";
import { type FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import type {
  ProductFilterOptions,
  ProductPage,
  ProductQuery,
} from "../../api/contracts";
import { getProductFilterOptions, getProducts } from "../../api/products";
import { EmptyState } from "../../components/EmptyState";
import { LoadingState } from "../../components/LoadingState";
import { StatusBadge } from "../../components/StatusBadge";
import { DEFAULT_PRODUCT_QUERY } from "../../domain/product";
import { PageHeader } from "../../layout/PageHeader";
import { ProductDetailPanel } from "./ProductDetailPanel";
import { ProductTable } from "./ProductTable";

type ProductOverviewPageProps = {
  productId?: string;
};

export function ProductOverviewPage({ productId }: ProductOverviewPageProps) {
  const [query, setQuery] = useState<ProductQuery>({ ...DEFAULT_PRODUCT_QUERY });
  const [draftSearch, setDraftSearch] = useState("");
  const [page, setPage] = useState<ProductPage | null>(null);
  const [options, setOptions] = useState<ProductFilterOptions | null>(null);
  const [loading, setLoading] = useState(true);
  const [optionsError, setOptionsError] = useState("");
  const [error, setError] = useState("");
  const [reloadToken, setReloadToken] = useState(0);

  const reloadProducts = useCallback(
    () => setReloadToken((value) => value + 1),
    [],
  );

  useEffect(() => {
    const controller = new AbortController();
    setOptionsError("");
    getProductFilterOptions(controller.signal)
      .then(setOptions)
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setOptionsError(reason instanceof Error ? reason.message : "筛选项加载失败");
        }
      });
    return () => controller.abort();
  }, [reloadToken]);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    getProducts(query, controller.signal)
      .then(setPage)
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : "商品加载失败");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [query, reloadToken]);

  const updateFilter = (field: keyof ProductQuery, value: string | number) => {
    setQuery((current) =>
      field === "page"
        ? { ...current, page: Number(value) }
        : { ...current, [field]: value, page: 1 },
    );
  };

  const submitSearch = (event: FormEvent) => {
    event.preventDefault();
    updateFilter("query", draftSearch.trim());
  };

  const resetFilters = () => {
    setDraftSearch("");
    setQuery({ ...DEFAULT_PRODUCT_QUERY });
  };

  const hasFilters = useMemo(
    () =>
      Boolean(
        query.query ||
          query.targetId ||
          query.taskId ||
          query.reviewStatus ||
          query.effect ||
          query.samplingStatus ||
          query.collectedFrom ||
          query.collectedTo,
      ),
    [query],
  );

  const selectProduct = (selectedProductId: string) => {
    window.location.hash = `#/products/${encodeURIComponent(selectedProductId)}`;
  };

  const closeDetail = () => {
    window.location.hash = "#/products";
  };

  return (
    <div className="page-frame product-page" data-detail-open={Boolean(productId)}>
      <PageHeader
        eyebrow="商品档案"
        title="商品总览"
        description="一件商品一行；筛选后展示匹配范围内最近一次快照。"
        actions={
          page ? <StatusBadge tone="info">共 {page.total} 件商品</StatusBadge> : undefined
        }
      />

      <div className="product-workspace">
        <section className="product-list-pane">
          <form className="product-filters" onSubmit={submitSearch}>
            <div className="search-control">
              <Search size={16} aria-hidden="true" />
              <input
                value={draftSearch}
                onChange={(event) => setDraftSearch(event.target.value)}
                placeholder="搜索商品名、店铺或商品 ID"
                aria-label="搜索商品"
              />
              <button type="submit">搜索</button>
            </div>
            <div className="filter-grid">
              <label>
                所属排查/采集批次
                <select
                  value={query.taskId}
                  onChange={(event) => updateFilter("taskId", event.target.value)}
                  disabled={!options}
                >
                  <option value="">全部排查</option>
                  {options?.tasks.map((item) => (
                    <option key={item.value} value={item.value}>{item.label}</option>
                  ))}
                </select>
              </label>
              <label>
                监测对象
                <select
                  value={query.targetId}
                  onChange={(event) => updateFilter("targetId", event.target.value)}
                  disabled={!options}
                >
                  <option value="">全部对象</option>
                  {options?.targets.map((item) => (
                    <option key={item.value} value={item.value}>{item.label}</option>
                  ))}
                </select>
              </label>
              <label>
                页面功效线索
                <select
                  value={query.effect}
                  onChange={(event) => updateFilter("effect", event.target.value)}
                  disabled={!options}
                >
                  <option value="">全部线索</option>
                  {options?.effects.map((item) => (
                    <option key={item.value} value={item.value}>{item.label}</option>
                  ))}
                </select>
              </label>
              <label>
                人工复核
                <select
                  value={query.reviewStatus}
                  onChange={(event) => updateFilter("reviewStatus", event.target.value)}
                  disabled={!options}
                >
                  <option value="">全部状态</option>
                  {options?.reviewStatuses.map((item) => (
                    <option key={item.value} value={item.value}>{item.label}</option>
                  ))}
                </select>
              </label>
              <label>
                抽检清单
                <select
                  value={query.samplingStatus}
                  onChange={(event) => updateFilter("samplingStatus", event.target.value)}
                  disabled={!options}
                >
                  <option value="">全部状态</option>
                  {options?.samplingStatuses.map((item) => (
                    <option key={item.value} value={item.value}>{item.label}</option>
                  ))}
                </select>
              </label>
              <label>
                采集开始日期
                <input
                  type="date"
                  value={query.collectedFrom}
                  onChange={(event) => updateFilter("collectedFrom", event.target.value)}
                />
              </label>
              <label>
                采集结束日期
                <input
                  type="date"
                  value={query.collectedTo}
                  onChange={(event) => updateFilter("collectedTo", event.target.value)}
                />
              </label>
              <button
                type="button"
                className="secondary-button filter-reset"
                onClick={resetFilters}
                disabled={!hasFilters && !draftSearch}
              >
                <FilterX size={15} /> 清除筛选
              </button>
            </div>
            {optionsError && (
              <div className="filter-error">
                <AlertCircle size={14} /> {optionsError}
              </div>
            )}
          </form>

          <div className="product-table-card">
            {loading && !page ? (
              <LoadingState label="正在读取商品索引" />
            ) : error ? (
              <EmptyState
                icon={AlertCircle}
                title="商品数据加载失败"
                description={error}
                action={
                  <button type="button" className="primary-button" onClick={reloadProducts}>
                    <RefreshCw size={15} /> 重试
                  </button>
                }
              />
            ) : page?.total === 0 ? (
              <EmptyState
                icon={PackageSearch}
                title={hasFilters ? "没有符合条件的商品" : "尚无已索引商品"}
                description={
                  hasFilters
                    ? "请调整筛选条件后重试。"
                    : "完成一次排查并建立业务索引后，商品会显示在这里。"
                }
                action={
                  hasFilters ? (
                    <button type="button" className="secondary-button" onClick={resetFilters}>
                      清除筛选
                    </button>
                  ) : (
                    <a className="primary-button" href="#/inspections">前往排查档案</a>
                  )
                }
              />
            ) : page ? (
              <>
                <ProductTable
                  products={page.products}
                  selectedProductId={productId}
                  onSelect={selectProduct}
                />
                <footer className="pagination">
                  <span>
                    第 {page.page} / {Math.max(page.totalPages, 1)} 页 · 当前 {page.count} 件
                  </span>
                  <div>
                    <button
                      type="button"
                      className="secondary-button"
                      disabled={page.page <= 1 || loading}
                      onClick={() => updateFilter("page", page.page - 1)}
                    >
                      上一页
                    </button>
                    <button
                      type="button"
                      className="secondary-button"
                      disabled={page.page >= page.totalPages || loading}
                      onClick={() => updateFilter("page", page.page + 1)}
                    >
                      下一页
                    </button>
                  </div>
                </footer>
              </>
            ) : null}
            {loading && page && <div className="table-loading-overlay">正在更新列表…</div>}
          </div>
        </section>

        {productId && (
          <ProductDetailPanel
            productId={productId}
            onClose={closeDetail}
            onProductChanged={reloadProducts}
          />
        )}
      </div>
    </div>
  );
}
