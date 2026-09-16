import {
  AlertCircle,
  BarChart3,
  Info,
  RefreshCw,
} from "lucide-react";
import {
  type FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import type {
  AnalyticsMetric,
  AnalyticsMetricBucket,
  AnalyticsMetricDefinition,
  AnalyticsMetricDictionary,
  AnalyticsResponse,
} from "../../api/contracts";
import {
  getAnalyticsClaims,
  getAnalyticsGeography,
  getAnalyticsKnowledge,
  getAnalyticsMetricDictionary,
  getAnalyticsPipeline,
} from "../../api/analytics";
import { EmptyState } from "../../components/EmptyState";
import { LoadingState } from "../../components/LoadingState";
import { PageHeader } from "../../layout/PageHeader";

import "./AnalyticsPage.css";

type AnalyticsSection = "pipeline" | "claims" | "geography" | "knowledge";

type AnalyticsRouteState = {
  section: AnalyticsSection;
  from: string;
  to: string;
  region: string;
  stage: string;
  claimType: string;
};

type AnalyticsPageProps = {
  search: string;
};

const SECTION_LABELS: Record<AnalyticsSection, string> = {
  pipeline: "运营流程",
  claims: "页面宣传线索",
  geography: "地区分布",
  knowledge: "知识覆盖",
};

const SECTION_DESCRIPTIONS: Record<AnalyticsSection, string> = {
  pipeline: "按真实处理分母查看采集、OCR、分析、人工复核与当前抽检清单状态。",
  claims: "仅统计 V2 formal ClaimSignal，并区分完成零线索、未生成与错误状态。",
  geography: "搜索地区反映采集上下文；商品标称产地来自页面明确声明，两者不可互相替代。",
  knowledge: "覆盖率仅针对项目当前治理数据集和既定分母，不代表全国覆盖情况。",
};

const DEFAULT_ROUTE: AnalyticsRouteState = {
  section: "pipeline",
  from: "",
  to: "",
  region: "",
  stage: "",
  claimType: "",
};

function parseRoute(search: string): AnalyticsRouteState {
  const params = new URLSearchParams(search);
  const section = params.get("section");
  return {
    section:
      section === "claims" || section === "geography" || section === "knowledge"
        ? section
        : "pipeline",
    from: params.get("from") ?? "",
    to: params.get("to") ?? "",
    region: params.get("region") ?? "",
    stage: params.get("stage") ?? "",
    claimType: params.get("claim_type") ?? "",
  };
}

function routeHash(state: AnalyticsRouteState) {
  const params = new URLSearchParams();
  if (state.section !== "pipeline") params.set("section", state.section);
  if (state.section !== "knowledge") {
    if (state.from) params.set("from", state.from);
    if (state.to) params.set("to", state.to);
    if (state.region) params.set("region", state.region);
    if (state.section === "pipeline" && state.stage) params.set("stage", state.stage);
    if ((state.section === "claims" || state.section === "geography") && state.claimType) {
      params.set("claim_type", state.claimType);
    }
  }
  const query = params.toString();
  return `#/analytics${query ? `?${query}` : ""}`;
}

function loadSection(state: AnalyticsRouteState, signal: AbortSignal): Promise<AnalyticsResponse> {
  const common = {
    from: state.from || undefined,
    to: state.to || undefined,
    region: state.region || undefined,
  };
  switch (state.section) {
    case "pipeline":
      return getAnalyticsPipeline({ ...common, stage: state.stage || undefined }, signal);
    case "claims":
      return getAnalyticsClaims({ ...common, claimType: state.claimType || undefined }, signal);
    case "geography":
      return getAnalyticsGeography({ ...common, claimType: state.claimType || undefined }, signal);
    case "knowledge":
      return getAnalyticsKnowledge(signal);
  }
}

function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined) return "—";
  return `${(value * 100).toFixed(value === 0 || value === 1 ? 0 : 1)}%`;
}

function metricDefinitionMap(dictionary: AnalyticsMetricDictionary | null) {
  return new Map((dictionary?.metrics ?? []).map((definition) => [definition.metric_id, definition]));
}

function MetricDetails({ metric, definition }: { metric: AnalyticsMetric; definition?: AnalyticsMetricDefinition }) {
  return (
    <details className="analytics-metric-details">
      <summary><Info size={14} aria-hidden="true" />指标口径</summary>
      <dl>
        <div><dt>统计粒度</dt><dd>{metric.grain}</dd></div>
        <div><dt>时间口径</dt><dd>{metric.timeBasis}</dd></div>
        {definition?.numerator_definition ? <div><dt>分子</dt><dd>{definition.numerator_definition}</dd></div> : null}
        {definition?.denominator_definition ? <div><dt>分母</dt><dd>{definition.denominator_definition}</dd></div> : null}
        <div><dt>缺失规则</dt><dd>{metric.missingRule}</dd></div>
        <div><dt>可解释为</dt><dd>{metric.interpretation}</dd></div>
        <div><dt>不可解释为</dt><dd>{metric.forbiddenInterpretation}</dd></div>
        <div><dt>数据版本</dt><dd>{metric.datasetVersion || "未提供"}</dd></div>
      </dl>
    </details>
  );
}

function CountMetricCard({ metric, definition }: { metric: AnalyticsMetric; definition?: AnalyticsMetricDefinition }) {
  return (
    <article className="analytics-metric-card">
      <div className="analytics-metric-heading"><span>{metric.title}</span><small>{metric.grain}</small></div>
      <strong className="analytics-metric-value">{metric.value ?? 0}</strong>
      <p>{metric.interpretation}</p>
      <MetricDetails metric={metric} definition={definition} />
    </article>
  );
}

function RatioMetricCard({ metric, definition }: { metric: AnalyticsMetric; definition?: AnalyticsMetricDefinition }) {
  const noDenominator = metric.reason === "zero_denominator" || metric.denominator === 0 || metric.rate === null;
  return (
    <article className="analytics-metric-card">
      <div className="analytics-metric-heading"><span>{metric.title}</span><small>{metric.grain}</small></div>
      {noDenominator ? (
        <div className="analytics-zero-denominator">暂无可计算分母</div>
      ) : (
        <>
          <strong className="analytics-metric-value">{formatPercent(metric.rate)}</strong>
          <div className="analytics-ratio-caption">{metric.numerator} / {metric.denominator}</div>
          <div className="analytics-progress" role="img" aria-label={`${metric.title} ${metric.numerator}/${metric.denominator}，${formatPercent(metric.rate)}`}>
            <span style={{ width: `${Math.max(0, Math.min(100, (metric.rate ?? 0) * 100))}%` }} />
          </div>
        </>
      )}
      <p>{metric.interpretation}</p>
      <MetricDetails metric={metric} definition={definition} />
    </article>
  );
}

function bucketLabel(bucket: AnalyticsMetricBucket) {
  const labels: Record<string, string> = {
    pending: "待复核",
    recommend_follow_up: "建议跟进",
    no_further_action: "暂不纳入",
    complete_with_claims: "已完成且存在页面宣传线索",
    complete_zero: "已完成且零正式线索",
    not_generated: "尚未生成",
    error: "生成失败",
    seller_managed: "页面经营者内容",
    user_generated: "用户生成内容",
    excluded_other_product: "排除的其他商品内容",
    unknown: "未记录 / 未知",
    not_recorded: "尚未记录",
    conflict: "存在多个明确页面产地事实",
  };
  return labels[bucket.key] ?? bucket.label ?? bucket.key;
}

function DistributionMetric({ metric, definition }: { metric: AnalyticsMetric; definition?: AnalyticsMetricDefinition }) {
  const buckets = metric.buckets ?? [];
  const noDenominator = metric.denominator === 0;
  return (
    <article className="analytics-distribution-card">
      <div className="analytics-distribution-heading">
        <div><h3>{metric.title}</h3><p>{metric.interpretation}</p></div>
        <span className="analytics-denominator">分母：{metric.denominator ?? 0}</span>
      </div>
      {noDenominator ? (
        <div className="analytics-zero-denominator">暂无可计算分母</div>
      ) : buckets.length === 0 ? (
        <p className="analytics-empty-inline">当前筛选下暂无分布记录。</p>
      ) : (
        <div className="analytics-bars" role="list" aria-label={metric.title}>
          {buckets.map((bucket) => (
            <div className="analytics-bar-row" role="listitem" key={bucket.key}>
              <div className="analytics-bar-meta">
                <span>{bucketLabel(bucket)}</span>
                <strong>{bucket.count} / {bucket.denominator}{bucket.rate !== null ? ` · ${formatPercent(bucket.rate)}` : ""}</strong>
              </div>
              <div className="analytics-bar-track" role="img" aria-label={`${bucketLabel(bucket)} ${bucket.count}/${bucket.denominator}${bucket.rate !== null ? `，${formatPercent(bucket.rate)}` : ""}`}>
                <span style={{ width: `${Math.max(0, Math.min(100, (bucket.rate ?? 0) * 100))}%` }} />
              </div>
            </div>
          ))}
        </div>
      )}
      {metric.metricId === "claim_type_snapshot_distribution" ? (
        <div className="analytics-inline-note">同一采集记录可包含多个宣传主题，因此各类别占比之和可能超过 100%。</div>
      ) : null}
      <MetricDetails metric={metric} definition={definition} />
    </article>
  );
}

function renderMetric(metric: AnalyticsMetric, definitions: Map<string, AnalyticsMetricDefinition>) {
  const definition = definitions.get(metric.metricId);
  if (metric.metricType === "distribution") return <DistributionMetric key={metric.metricId} metric={metric} definition={definition} />;
  if (metric.metricType === "ratio" || metric.metricType === "coverage") return <RatioMetricCard key={metric.metricId} metric={metric} definition={definition} />;
  return <CountMetricCard key={metric.metricId} metric={metric} definition={definition} />;
}

export function AnalyticsPage({ search }: AnalyticsPageProps) {
  const routeState = useMemo(() => parseRoute(search), [search]);
  const [dictionary, setDictionary] = useState<AnalyticsMetricDictionary | null>(null);
  const [dictionaryError, setDictionaryError] = useState("");
  const [response, setResponse] = useState<AnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadToken, setReloadToken] = useState(0);
  const [draft, setDraft] = useState(routeState);
  const definitions = useMemo(() => metricDefinitionMap(dictionary), [dictionary]);

  useEffect(() => setDraft(routeState), [routeState]);

  useEffect(() => {
    const controller = new AbortController();
    getAnalyticsMetricDictionary(controller.signal).then(setDictionary).catch((reason: unknown) => {
      if (!controller.signal.aborted) setDictionaryError(reason instanceof Error ? reason.message : "指标字典加载失败");
    });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    loadSection(routeState, controller.signal).then(setResponse).catch((reason: unknown) => {
      if (!controller.signal.aborted) {
        setResponse(null);
        setError(reason instanceof Error ? reason.message : "统计指标加载失败");
      }
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, [routeState, reloadToken]);

  const navigate = useCallback((next: AnalyticsRouteState) => {
    window.location.hash = routeHash(next);
  }, []);

  const changeSection = (section: AnalyticsSection) => {
    navigate({
      ...routeState,
      section,
      stage: section === "pipeline" ? routeState.stage : "",
      claimType: section === "claims" || section === "geography" ? routeState.claimType : "",
    });
  };

  const applyFilters = (event: FormEvent) => {
    event.preventDefault();
    navigate({
      ...routeState,
      from: draft.from.trim(),
      to: draft.to.trim(),
      region: draft.region.trim(),
      stage: routeState.section === "pipeline" ? draft.stage.trim() : "",
      claimType: routeState.section === "claims" || routeState.section === "geography" ? draft.claimType.trim() : "",
    });
  };

  const clearFilters = () => navigate({ ...DEFAULT_ROUTE, section: routeState.section });
  const hasRuntimeFilters = routeState.section !== "knowledge" && Boolean(routeState.from || routeState.to || routeState.region || routeState.stage || routeState.claimType);
  const metrics = response?.metrics ?? [];
  const countMetrics = metrics.filter((metric) => metric.metricType === "count");
  const ratioMetrics = metrics.filter((metric) => metric.metricType === "ratio" || metric.metricType === "coverage");
  const distributionMetrics = metrics.filter((metric) => metric.metricType === "distribution");

  return (
    <div className="page-frame analytics-page">
      <PageHeader eyebrow="可复现统计" title="统计分析" description="基于当前采集数据和治理知识展示可复现的统计事实；结果不代表市场总体风险或全国覆盖情况。" />

      <div className="analytics-scope-note">
        <BarChart3 size={17} aria-hidden="true" />
        <span>统计结果仅反映当前系统数据范围，不代表市场总体情况。所有比例均保留各自真实分母。</span>
      </div>

      <nav className="analytics-tabs" role="tablist" aria-label="统计分析域">
        {(Object.keys(SECTION_LABELS) as AnalyticsSection[]).map((section) => (
          <button key={section} type="button" role="tab" aria-selected={routeState.section === section} data-active={routeState.section === section} onClick={() => changeSection(section)}>
            {SECTION_LABELS[section]}
          </button>
        ))}
      </nav>

      <section className="analytics-panel" role="tabpanel">
        <div className="analytics-section-heading">
          <div><h2>{SECTION_LABELS[routeState.section]}</h2><p>{SECTION_DESCRIPTIONS[routeState.section]}</p></div>
          {response?.dictionaryVersion ? <span className="analytics-version">{response.dictionaryVersion}</span> : null}
        </div>

        {routeState.section === "knowledge" ? (
          <div className="analytics-filter-note">知识覆盖按治理数据版本统计，不按运行时间筛选。</div>
        ) : (
          <form className="analytics-filters" onSubmit={applyFilters}>
            <label>开始日期<input type="date" value={draft.from} onChange={(event) => setDraft((current) => ({ ...current, from: event.target.value }))} /></label>
            <label>结束日期<input type="date" value={draft.to} onChange={(event) => setDraft((current) => ({ ...current, to: event.target.value }))} /></label>
            <label>搜索地区<input value={draft.region} onChange={(event) => setDraft((current) => ({ ...current, region: event.target.value }))} placeholder="按搜索上下文筛选" /></label>
            {routeState.section === "pipeline" ? <label>处理阶段<input value={draft.stage} onChange={(event) => setDraft((current) => ({ ...current, stage: event.target.value }))} placeholder="可选，使用后端 stage 值" /></label> : null}
            {routeState.section === "claims" || routeState.section === "geography" ? <label>Claim Type<input value={draft.claimType} onChange={(event) => setDraft((current) => ({ ...current, claimType: event.target.value }))} placeholder="可选，使用治理 Claim Type" /></label> : null}
            <div className="analytics-filter-actions">
              <button type="submit" className="primary-button">应用筛选</button>
              <button type="button" className="secondary-button" onClick={clearFilters} disabled={!hasRuntimeFilters}>清除筛选</button>
            </div>
            <small className="analytics-time-note">运行指标按所属任务创建时间统计。</small>
          </form>
        )}

        {routeState.section === "geography" ? <div className="analytics-boundary-note">搜索地区反映商品在哪个搜索任务/地区上下文中被发现；商品标称产地仅来自页面明确声明的 declared_origin 事实，两者不可互相替代。</div> : null}
        {routeState.section === "knowledge" ? <div className="analytics-boundary-note">这里的覆盖率只针对项目当前 Reference、治理映射与固定 Context Corpus；不是全国方法覆盖率、生产准确率或市场风险覆盖率。</div> : null}
        {dictionaryError ? <div className="analytics-dictionary-warning" role="status"><AlertCircle size={15} />指标口径说明暂时不可用：{dictionaryError}</div> : null}

        {loading && !response ? (
          <LoadingState label={`正在读取${SECTION_LABELS[routeState.section]}指标`} />
        ) : error ? (
          <EmptyState icon={AlertCircle} title="统计指标加载失败" description={error} action={<button type="button" className="primary-button" onClick={() => setReloadToken((value) => value + 1)}><RefreshCw size={15} />重试</button>} />
        ) : response && metrics.length === 0 ? (
          <EmptyState icon={BarChart3} title="当前范围暂无可展示指标" description="请调整筛选条件后重试；合法的零值不会被视为系统错误。" />
        ) : response ? (
          <div className="analytics-content">
            {countMetrics.length > 0 ? <div className="analytics-metric-grid">{countMetrics.map((metric) => renderMetric(metric, definitions))}</div> : null}
            {ratioMetrics.length > 0 ? <div className="analytics-metric-grid analytics-coverage-grid">{ratioMetrics.map((metric) => renderMetric(metric, definitions))}</div> : null}
            {distributionMetrics.length > 0 ? <div className="analytics-distribution-grid">{distributionMetrics.map((metric) => renderMetric(metric, definitions))}</div> : null}
          </div>
        ) : null}

        {dictionary?.unavailable_metrics?.length ? (
          <details className="analytics-unavailable">
            <summary>当前不可计算 / 未来指标</summary>
            <ul>{dictionary.unavailable_metrics.map((metric) => <li key={metric.metric_id}><strong>{metric.metric_id}</strong><span>{metric.reason}</span></li>)}</ul>
          </details>
        ) : null}
      </section>
    </div>
  );
}
