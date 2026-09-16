import {
  AlertCircle,
  BookOpenText,
  FilterX,
  RefreshCw,
  Search,
} from "lucide-react";
import {
  type FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import type {
  KnowledgeHealthFunction,
  KnowledgePage,
  KnowledgeSummary,
} from "../../api/contracts";
import {
  getKnowledgeHealthFunctions,
  getKnowledgeInspectionMethods,
  getKnowledgeMonitorTargets,
  getKnowledgeRegulatoryDocuments,
  getKnowledgeRiskMappings,
  getKnowledgeSubstances,
  getKnowledgeSummary,
} from "../../api/knowledge";
import { EmptyState } from "../../components/EmptyState";
import { LoadingState } from "../../components/LoadingState";
import {
  DEFAULT_KNOWLEDGE_ROUTE,
  KNOWLEDGE_TAB_IDS,
  KNOWLEDGE_TAB_LABELS,
  knowledgeRouteHash,
  parseKnowledgeRoute,
  type KnowledgeRouteState,
} from "../../domain/knowledge";
import { PageHeader } from "../../layout/PageHeader";
import { KnowledgeDetailDrawer } from "./KnowledgeDetailDrawer";
import { KnowledgeTable } from "./KnowledgeTable";
import {
  KNOWLEDGE_EMPTY_TITLES,
  knowledgeRecordId,
  type KnowledgeRecord,
} from "./types";

const PAGE_SIZE = 25;

type KnowledgeBasePageProps = {
  search: string;
};

function loadKnowledgePage(
  state: KnowledgeRouteState,
  signal: AbortSignal,
): Promise<KnowledgePage<KnowledgeRecord>> {
  const common = {
    query: state.query,
    limit: PAGE_SIZE,
    offset: state.offset,
  };
  switch (state.tab) {
    case "monitor-targets":
      return getKnowledgeMonitorTargets(
        { ...common, availability: state.availability },
        signal,
      );
    case "health-functions":
      return getKnowledgeHealthFunctions(
        { ...common, framework: state.framework, status: state.status },
        signal,
      );
    case "substances":
      return getKnowledgeSubstances(common, signal);
    case "risk-mappings":
      return getKnowledgeRiskMappings(
        { ...common, target_type: state.targetType, status: state.status },
        signal,
      );
    case "inspection-methods":
      return getKnowledgeInspectionMethods(
        {
          ...common,
          status: state.status,
          knowledge_depth: state.knowledgeDepth,
        },
        signal,
      );
    case "regulatory-documents":
      return getKnowledgeRegulatoryDocuments(
        {
          ...common,
          status: state.status,
          document_type: state.documentType,
        },
        signal,
      );
  }
}

function SummaryCards({ summary }: { summary: KnowledgeSummary }) {
  const cards = [
    {
      label: "食药目录对象",
      value: summary.counts.referenceMonitorTargets,
      detail: `其中 ${summary.counts.operationalMonitorTargets} 个当前可排查`,
    },
    {
      label: "保健功能",
      value: summary.counts.healthFunctions,
      detail: "按治理框架独立记录",
    },
    {
      label: "风险物质",
      value: summary.counts.substances,
      detail: "物质记录不代表商品检出",
    },
    {
      label: "检验方法",
      value: summary.counts.inspectionMethods,
      detail: `其中 ${summary.counts.recommendationReadyMethods} 个达到 recommendation-ready`,
    },
  ];
  return (
    <section className="knowledge-summary" aria-label="知识事实摘要">
      {cards.map((card) => (
        <article key={card.label}>
          <span>{card.label}</span>
          <strong>{card.value}</strong>
          <small>{card.detail}</small>
        </article>
      ))}
    </section>
  );
}

function TabFilters({
  state,
  frameworks,
  onChange,
}: {
  state: KnowledgeRouteState;
  frameworks: Array<{ id: string; label: string }>;
  onChange: (patch: Partial<KnowledgeRouteState>) => void;
}) {
  switch (state.tab) {
    case "monitor-targets":
      return (
        <label>
          当前可排查状态
          <select value={state.availability} onChange={(event) => onChange({ availability: event.target.value })}>
            <option value="">全部状态</option>
            <option value="operational">当前可排查</option>
            <option value="query_pending">搜索策略待验证</option>
            <option value="paused">已暂停</option>
          </select>
        </label>
      );
    case "health-functions":
      return (
        <>
          <label>
            Framework
            <input
              list="knowledge-framework-options"
              value={state.framework}
              onChange={(event) => onChange({ framework: event.target.value })}
              placeholder="输入或选择 Framework"
            />
            <datalist id="knowledge-framework-options">
              {frameworks.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
            </datalist>
          </label>
          <label>
            状态
            <select value={state.status} onChange={(event) => onChange({ status: event.target.value })}>
              <option value="">全部状态</option>
              <option value="verified_reference">已核验参考</option>
            </select>
          </label>
        </>
      );
    case "substances":
      return null;
    case "risk-mappings":
      return (
        <>
          <label>
            Target Type
            <select value={state.targetType} onChange={(event) => onChange({ targetType: event.target.value })}>
              <option value="">全部类型</option>
              <option value="substance">单一物质</option>
              <option value="substance_group">组级映射</option>
            </select>
          </label>
          <label>
            Temporal Status
            <select value={state.status} onChange={(event) => onChange({ status: event.target.value })}>
              <option value="">全部时态</option>
              <option value="current">当前</option>
              <option value="historical">历史</option>
            </select>
          </label>
        </>
      );
    case "inspection-methods":
      return (
        <>
          <label>
            官方生命周期
            <select value={state.status} onChange={(event) => onChange({ status: event.target.value })}>
              <option value="">全部生命周期</option>
              <option value="current">现行</option>
              <option value="superseded">已被替代</option>
              <option value="revoked">废止</option>
              <option value="verification_pending">待核验</option>
            </select>
          </label>
          <label>
            知识深度
            <select value={state.knowledgeDepth} onChange={(event) => onChange({ knowledgeDepth: event.target.value })}>
              <option value="">全部知识深度</option>
              <option value="reference_only">仅供参考</option>
              <option value="analyte_verified">分析物已核验</option>
              <option value="applicability_verified">适用范围已核验</option>
              <option value="recommendation_ready">可用于抽检建议</option>
            </select>
          </label>
        </>
      );
    case "regulatory-documents":
      return (
        <>
          <label>
            Lifecycle
            <select value={state.status} onChange={(event) => onChange({ status: event.target.value })}>
              <option value="">全部生命周期</option>
              <option value="current">现行</option>
              <option value="superseded">已被替代</option>
              <option value="revoked">废止</option>
              <option value="verification_pending">待核验</option>
            </select>
          </label>
          <label>
            文件类型
            <select value={state.documentType} onChange={(event) => onChange({ documentType: event.target.value })}>
              <option value="">全部类型</option>
              <option value="official_method_page">官方方法页面</option>
              <option value="official_announcement">官方公告</option>
              <option value="national_standard_record">国家标准记录</option>
            </select>
          </label>
        </>
      );
  }
}

export function KnowledgeBasePage({ search }: KnowledgeBasePageProps) {
  const routeState = useMemo(() => parseKnowledgeRoute(search), [search]);
  const loadKey = useMemo(() => JSON.stringify(routeState), [routeState]);
  const [summary, setSummary] = useState<KnowledgeSummary | null>(null);
  const [summaryError, setSummaryError] = useState("");
  const [summaryReload, setSummaryReload] = useState(0);
  const [page, setPage] = useState<KnowledgePage<KnowledgeRecord> | null>(null);
  const [loadedKey, setLoadedKey] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadToken, setReloadToken] = useState(0);
  const [draftSearch, setDraftSearch] = useState(routeState.query);
  const [selectedRecord, setSelectedRecord] = useState<KnowledgeRecord | null>(null);
  const [frameworks, setFrameworks] = useState<Array<{ id: string; label: string }>>([]);

  const visiblePage = loadedKey === loadKey ? page : null;

  useEffect(() => setDraftSearch(routeState.query), [routeState.query]);
  useEffect(() => setSelectedRecord(null), [loadKey]);

  useEffect(() => {
    const controller = new AbortController();
    setSummaryError("");
    getKnowledgeSummary(controller.signal)
      .then(setSummary)
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setSummaryError(reason instanceof Error ? reason.message : "知识摘要加载失败");
        }
      });
    return () => controller.abort();
  }, [summaryReload]);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    loadKnowledgePage(routeState, controller.signal)
      .then((result) => {
        setPage(result);
        setLoadedKey(loadKey);
        if (routeState.tab === "health-functions") {
          const options = new Map(
            (result.items as KnowledgeHealthFunction[]).map((item) => [
              item.frameworkId,
              item.frameworkName,
            ]),
          );
          setFrameworks((current) => {
            current.forEach((item) => options.set(item.id, item.label));
            return Array.from(options, ([id, label]) => ({ id, label }));
          });
        }
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setLoadedKey(loadKey);
          setPage(null);
          setError(reason instanceof Error ? reason.message : "知识记录加载失败");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [loadKey, reloadToken]);

  const navigate = useCallback(
    (next: KnowledgeRouteState) => {
      window.location.hash = knowledgeRouteHash(next);
    },
    [],
  );

  const updateFilters = (patch: Partial<KnowledgeRouteState>) => {
    navigate({ ...routeState, ...patch, offset: 0 });
  };

  const submitSearch = (event: FormEvent) => {
    event.preventDefault();
    updateFilters({ query: draftSearch.trim() });
  };

  const resetFilters = () => {
    setDraftSearch("");
    navigate({ ...DEFAULT_KNOWLEDGE_ROUTE, tab: routeState.tab });
  };

  const hasFilters = Boolean(
    routeState.query ||
      routeState.availability ||
      routeState.framework ||
      routeState.status ||
      routeState.targetType ||
      routeState.knowledgeDepth ||
      routeState.documentType,
  );

  return (
    <div className="page-frame knowledge-page">
      <PageHeader
        eyebrow="治理知识"
        title="知识库"
        description="查看系统当前使用的治理知识、来源、版本与知识缺口。"
      />

      {summary ? <SummaryCards summary={summary} /> : summaryError ? (
        <div className="knowledge-summary-error" role="alert">
          <AlertCircle size={15} />
          <span>知识摘要加载失败：{summaryError}</span>
          <button type="button" onClick={() => setSummaryReload((value) => value + 1)}>重试</button>
        </div>
      ) : <div className="knowledge-summary-loading"><LoadingState label="正在读取知识摘要" /></div>}

      <nav className="knowledge-tabs" role="tablist" aria-label="知识域">
        {KNOWLEDGE_TAB_IDS.map((tab) => (
          <a
            key={tab}
            id={`knowledge-tab-${tab}`}
            role="tab"
            aria-selected={routeState.tab === tab}
            aria-controls="knowledge-tabpanel"
            href={knowledgeRouteHash({ ...DEFAULT_KNOWLEDGE_ROUTE, tab })}
            data-active={routeState.tab === tab}
          >
            {KNOWLEDGE_TAB_LABELS[tab]}
          </a>
        ))}
      </nav>

      <section
        id="knowledge-tabpanel"
        className="knowledge-panel"
        role="tabpanel"
        aria-labelledby={`knowledge-tab-${routeState.tab}`}
      >
        <form className="knowledge-filters" onSubmit={submitSearch}>
          <div className="search-control">
            <Search size={16} aria-hidden="true" />
            <input
              value={draftSearch}
              onChange={(event) => setDraftSearch(event.target.value)}
              placeholder={`搜索${KNOWLEDGE_TAB_LABELS[routeState.tab]}`}
              aria-label={`搜索${KNOWLEDGE_TAB_LABELS[routeState.tab]}`}
            />
            <button type="submit">搜索</button>
          </div>
          <div className="knowledge-filter-row">
            <TabFilters state={routeState} frameworks={frameworks} onChange={updateFilters} />
            <button type="button" className="secondary-button" onClick={resetFilters} disabled={!hasFilters && !draftSearch}>
              <FilterX size={15} />清除筛选
            </button>
          </div>
        </form>

        <div className="knowledge-table-card">
          {loading && !visiblePage ? (
            <LoadingState label={`正在读取${KNOWLEDGE_TAB_LABELS[routeState.tab]}`} />
          ) : error ? (
            <div className="knowledge-error-state">
              <EmptyState
                icon={AlertCircle}
                title="知识记录加载失败"
                description={error}
                action={<button type="button" className="primary-button" onClick={() => setReloadToken((value) => value + 1)}><RefreshCw size={15} />重试</button>}
              />
            </div>
          ) : visiblePage?.total === 0 ? (
            <EmptyState
              icon={BookOpenText}
              title={KNOWLEDGE_EMPTY_TITLES[routeState.tab]}
              description="请调整搜索词或筛选条件后重试。"
              action={hasFilters ? <button type="button" className="secondary-button" onClick={resetFilters}>清除筛选</button> : undefined}
            />
          ) : visiblePage ? (
            <>
              <KnowledgeTable
                tab={routeState.tab}
                records={visiblePage.items}
                selectedId={selectedRecord ? knowledgeRecordId(routeState.tab, selectedRecord) : undefined}
                onSelect={setSelectedRecord}
              />
              <footer className="pagination">
                <span>第 {Math.floor(visiblePage.offset / visiblePage.limit) + 1} 页 · 当前 {visiblePage.count} 条 · 共 {visiblePage.total} 条</span>
                <div>
                  <button type="button" className="secondary-button" disabled={visiblePage.offset <= 0 || loading} onClick={() => navigate({ ...routeState, offset: Math.max(0, visiblePage.offset - visiblePage.limit) })}>上一页</button>
                  <button type="button" className="secondary-button" disabled={!visiblePage.hasMore || loading} onClick={() => navigate({ ...routeState, offset: visiblePage.offset + visiblePage.limit })}>下一页</button>
                </div>
              </footer>
            </>
          ) : null}
          {loading && visiblePage && <div className="table-loading-overlay">正在更新列表…</div>}
        </div>
      </section>

      {selectedRecord && (
        <KnowledgeDetailDrawer
          tab={routeState.tab}
          record={selectedRecord}
          onClose={() => setSelectedRecord(null)}
        />
      )}
    </div>
  );
}
