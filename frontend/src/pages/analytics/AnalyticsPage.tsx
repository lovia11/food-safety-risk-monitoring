import {
  AlertCircle,
  ClipboardCheck,
  FlaskConical,
  MapPinned,
  PackageSearch,
  RefreshCw,
  SearchCheck,
  SlidersHorizontal,
} from "lucide-react";
import { type FormEvent, useEffect, useMemo, useState } from "react";

import type {
  AnalyticsMetric,
  AnalyticsMetricBucket,
  AnalyticsResponse,
} from "../../api/contracts";
import {
  getAnalyticsClaims,
  getAnalyticsGeography,
  getAnalyticsPipeline,
} from "../../api/analytics";
import { EmptyState } from "../../components/EmptyState";
import { LoadingState } from "../../components/LoadingState";
import { PageHeader } from "../../layout/PageHeader";

import "./AnalyticsPage.css";

type AnalyticsPageProps = {
  search: string;
};

type AnalyticsFilters = {
  from: string;
  to: string;
  region: string;
};

type DashboardData = {
  pipeline: AnalyticsResponse;
  claims: AnalyticsResponse;
  geography: AnalyticsResponse;
};

type GeographyMode = "search" | "origin";

const CLAIM_LABELS: Record<string, string> = {
  sleep_related: "睡眠相关",
  weight_management: "体重管理",
  male_function_related: "男性功能相关",
  blood_lipid_related: "血脂相关",
  blood_pressure_related: "血压相关",
};

const REVIEW_LABELS: Record<string, string> = {
  pending: "待复核",
  recommend_follow_up: "建议跟进",
  no_further_action: "暂不纳入",
};

const PROVINCE_POINTS: Record<string, [number, number]> = {
  北京: [554, 190],
  天津: [574, 205],
  河北: [540, 216],
  山西: [506, 221],
  内蒙古: [465, 155],
  辽宁: [610, 165],
  吉林: [640, 134],
  黑龙江: [666, 94],
  上海: [623, 302],
  江苏: [597, 281],
  浙江: [610, 327],
  安徽: [562, 293],
  福建: [582, 361],
  江西: [543, 338],
  山东: [582, 246],
  河南: [520, 268],
  湖北: [495, 304],
  湖南: [482, 348],
  广东: [507, 398],
  广西: [452, 397],
  海南: [486, 447],
  重庆: [432, 320],
  四川: [383, 314],
  贵州: [421, 363],
  云南: [348, 395],
  西藏: [220, 333],
  陕西: [452, 263],
  甘肃: [370, 230],
  青海: [301, 264],
  宁夏: [413, 226],
  新疆: [168, 194],
  台湾: [644, 375],
  香港: [526, 408],
  澳门: [516, 412],
};

function parseFilters(search: string): AnalyticsFilters {
  const params = new URLSearchParams(search);
  return {
    from: params.get("from") ?? "",
    to: params.get("to") ?? "",
    region: params.get("region") ?? "",
  };
}

function analyticsHash(filters: AnalyticsFilters) {
  const params = new URLSearchParams();
  if (filters.from) params.set("from", filters.from);
  if (filters.to) params.set("to", filters.to);
  if (filters.region) params.set("region", filters.region);
  const query = params.toString();
  return `#/analytics${query ? `?${query}` : ""}`;
}

function findMetric(response: AnalyticsResponse | null, metricId: string) {
  return response?.metrics.find((metric) => metric.metricId === metricId) ?? null;
}

function findBucket(metric: AnalyticsMetric | null, key: string) {
  return metric?.buckets?.find((bucket) => bucket.key === key) ?? null;
}

function claimLabel(bucket: AnalyticsMetricBucket) {
  return CLAIM_LABELS[bucket.key] ?? bucket.label ?? bucket.key;
}

function normalizeProvince(value: string) {
  return value
    .replace(/壮族自治区$|回族自治区$|维吾尔自治区$|自治区$|特别行政区$/g, "")
    .replace(/[省市]$/, "")
    .trim();
}

function isSpecialRegionBucket(bucket: AnalyticsMetricBucket) {
  return ["unknown", "not_recorded", "conflict"].includes(bucket.key);
}

function displayRegion(bucket: AnalyticsMetricBucket) {
  if (bucket.key === "unknown" || bucket.key === "not_recorded") return "未明确";
  if (bucket.key === "conflict") return "存在多个页面产地";
  return bucket.label || bucket.key;
}

function SummaryCard({
  icon: Icon,
  label,
  value,
  note,
}: {
  icon: typeof PackageSearch;
  label: string;
  value: number;
  note: string;
}) {
  return (
    <article className="analytics-summary-card">
      <span className="analytics-summary-icon" aria-hidden="true">
        <Icon size={20} />
      </span>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
        <small>{note}</small>
      </div>
    </article>
  );
}

function SectionHeading({ title, description }: { title: string; description: string }) {
  return (
    <div className="analytics-product-section-heading">
      <div>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
    </div>
  );
}

function ClaimBars({ metric }: { metric: AnalyticsMetric | null }) {
  const buckets = metric?.buckets ?? [];
  const sorted = [...buckets].sort((a, b) => b.count - a.count);
  const max = Math.max(1, ...sorted.map((bucket) => bucket.count));

  if (!metric || metric.denominator === 0 || sorted.length === 0) {
    return (
      <div className="analytics-friendly-empty">
        当前范围内还没有可展示的页面宣传线索分类数据。
      </div>
    );
  }

  return (
    <div className="analytics-claim-chart" role="list" aria-label="页面宣传线索类型分布">
      {sorted.map((bucket) => (
        <div className="analytics-claim-row" role="listitem" key={bucket.key}>
          <span className="analytics-claim-label">{claimLabel(bucket)}</span>
          <div className="analytics-claim-track" aria-hidden="true">
            <span style={{ width: `${(bucket.count / max) * 100}%` }} />
          </div>
          <strong>{bucket.count}</strong>
        </div>
      ))}
    </div>
  );
}

function ReviewSummary({ metric }: { metric: AnalyticsMetric | null }) {
  const buckets = REVIEW_LABELS;
  return (
    <div className="analytics-review-grid">
      {Object.entries(buckets).map(([key, label]) => {
        const bucket = findBucket(metric, key);
        return (
          <div className="analytics-review-item" key={key} data-status={key}>
            <span>{label}</span>
            <strong>{bucket?.count ?? 0}</strong>
          </div>
        );
      })}
    </div>
  );
}

function RegionHeatMap({ metric, mode }: { metric: AnalyticsMetric | null; mode: GeographyMode }) {
  const buckets = metric?.buckets ?? [];
  const ordinary = buckets.filter((bucket) => !isSpecialRegionBucket(bucket) && bucket.count > 0);
  const ranked = [...ordinary].sort((a, b) => b.count - a.count);
  const max = Math.max(1, ...ranked.map((bucket) => bucket.count));
  const plotted = ranked
    .map((bucket) => ({ bucket, point: PROVINCE_POINTS[normalizeProvince(bucket.label || bucket.key)] }))
    .filter((item): item is { bucket: AnalyticsMetricBucket; point: [number, number] } => Boolean(item.point));
  const special = buckets.filter((bucket) => isSpecialRegionBucket(bucket) && bucket.count > 0);

  if (!metric || metric.denominator === 0) {
    return <div className="analytics-friendly-empty">当前范围内还没有地区分布数据。</div>;
  }

  return (
    <div className="analytics-map-layout">
      <div className="analytics-map-panel">
        <svg
          className="analytics-china-map"
          viewBox="0 0 760 500"
          role="img"
          aria-label={mode === "search" ? "已采集商品搜索地区分布图" : "商品标称产地分布图"}
        >
          <path
            className="analytics-china-outline"
            d="M70 175 L100 132 L155 105 L225 90 L298 102 L360 88 L430 103 L493 78 L565 70 L635 92 L690 130 L705 174 L683 204 L710 235 L686 267 L699 300 L660 326 L642 364 L602 381 L572 417 L527 425 L500 454 L456 438 L421 456 L374 426 L329 443 L292 409 L245 399 L207 371 L166 355 L139 322 L111 305 L104 269 L78 244 L94 214 Z"
          />
          <ellipse className="analytics-island-outline" cx="488" cy="452" rx="11" ry="8" />
          <ellipse className="analytics-island-outline" cx="647" cy="379" rx="7" ry="15" />
          {plotted.map(({ bucket, point }) => {
            const intensity = bucket.count / max;
            const radius = 10 + intensity * 13;
            const name = normalizeProvince(bucket.label || bucket.key);
            return (
              <g key={bucket.key} className="analytics-map-point">
                <circle cx={point[0]} cy={point[1]} r={radius} style={{ opacity: 0.28 + intensity * 0.62 }}>
                  <title>{`${displayRegion(bucket)}：${bucket.count}`}</title>
                </circle>
                <text x={point[0]} y={point[1] + 4} textAnchor="middle">{name}</text>
              </g>
            );
          })}
        </svg>
        <p className="analytics-map-caption">颜色深浅和圆点大小仅表示当前数据中的商品数量，不表示地区风险高低。</p>
      </div>

      <aside className="analytics-region-ranking" aria-label="地区数量排行">
        <h3>{mode === "search" ? "采集商品较多的地区" : "标称产地较多的地区"}</h3>
        {ranked.length ? (
          <ol>
            {ranked.slice(0, 6).map((bucket) => (
              <li key={bucket.key}>
                <span>{displayRegion(bucket)}</span>
                <strong>{bucket.count}</strong>
              </li>
            ))}
          </ol>
        ) : (
          <p>暂无可排行地区。</p>
        )}
        {special.length ? (
          <div className="analytics-region-special">
            {special.map((bucket) => (
              <span key={bucket.key}>{displayRegion(bucket)}：{bucket.count}</span>
            ))}
          </div>
        ) : null}
      </aside>
    </div>
  );
}

export function AnalyticsPage({ search }: AnalyticsPageProps) {
  const filters = useMemo(() => parseFilters(search), [search]);
  const [draft, setDraft] = useState(filters);
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadToken, setReloadToken] = useState(0);
  const [geographyMode, setGeographyMode] = useState<GeographyMode>("search");

  useEffect(() => setDraft(filters), [filters]);

  useEffect(() => {
    const controller = new AbortController();
    const common = {
      from: filters.from || undefined,
      to: filters.to || undefined,
      region: filters.region || undefined,
    };
    setLoading(true);
    setError("");
    Promise.all([
      getAnalyticsPipeline(common, controller.signal),
      getAnalyticsClaims(common, controller.signal),
      getAnalyticsGeography(common, controller.signal),
    ])
      .then(([pipeline, claims, geography]) => setData({ pipeline, claims, geography }))
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setData(null);
          setError(reason instanceof Error ? reason.message : "统计数据加载失败");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [filters, reloadToken]);

  const applyFilters = (event: FormEvent) => {
    event.preventDefault();
    window.location.hash = analyticsHash({
      from: draft.from.trim(),
      to: draft.to.trim(),
      region: draft.region.trim(),
    });
  };

  const clearFilters = () => {
    setDraft({ from: "", to: "", region: "" });
    window.location.hash = "#/analytics";
  };

  const hasFilters = Boolean(filters.from || filters.to || filters.region);

  const uniqueProducts = findMetric(data?.pipeline ?? null, "unique_product_count")?.value ?? 0;
  const claimStatus = findMetric(data?.claims ?? null, "claim_analysis_status_distribution");
  const claimRecords = findBucket(claimStatus, "complete_with_claims")?.count ?? 0;
  const reviewStatus = findMetric(data?.pipeline ?? null, "review_status_distribution");
  const followUpCount = findBucket(reviewStatus, "recommend_follow_up")?.count ?? 0;
  const samplingCount = findMetric(data?.pipeline ?? null, "current_sampling_membership_count")?.value ?? 0;
  const claimTypes = findMetric(data?.claims ?? null, "claim_type_snapshot_distribution");
  const searchRegions = findMetric(data?.geography ?? null, "collected_product_search_region_distribution");
  const declaredOrigins = findMetric(data?.geography ?? null, "declared_origin_distribution");
  const activeGeographyMetric = geographyMode === "search" ? searchRegions : declaredOrigins;

  return (
    <div className="page-frame analytics-page analytics-product-dashboard">
      <PageHeader
        eyebrow="数据概览"
        title="统计分析"
        description="快速查看当前已采集商品中的页面宣传线索、地区分布与人工复核结果。"
      />

      <div className="analytics-product-scope-note">
        统计结果仅反映当前系统已采集的数据，不代表市场总体情况或地区风险水平。
      </div>

      <details className="analytics-filter-panel">
        <summary>
          <SlidersHorizontal size={16} aria-hidden="true" />
          筛选统计范围
          {hasFilters ? <span>已筛选</span> : null}
        </summary>
        <form className="analytics-simple-filters" onSubmit={applyFilters}>
          <label>
            开始日期
            <input type="date" value={draft.from} onChange={(event) => setDraft((current) => ({ ...current, from: event.target.value }))} />
          </label>
          <label>
            结束日期
            <input type="date" value={draft.to} onChange={(event) => setDraft((current) => ({ ...current, to: event.target.value }))} />
          </label>
          <label>
            搜索地区
            <input value={draft.region} onChange={(event) => setDraft((current) => ({ ...current, region: event.target.value }))} placeholder="全部地区" />
          </label>
          <div className="analytics-filter-actions">
            <button type="submit" className="primary-button">应用</button>
            <button type="button" className="secondary-button" onClick={clearFilters} disabled={!hasFilters && !draft.from && !draft.to && !draft.region}>清除</button>
          </div>
        </form>
      </details>

      {loading && !data ? (
        <LoadingState label="正在读取统计数据" />
      ) : error ? (
        <div className="analytics-load-error">
          <EmptyState
            icon={AlertCircle}
            title="统计数据加载失败"
            description={error}
            action={<button type="button" className="primary-button" onClick={() => setReloadToken((value) => value + 1)}><RefreshCw size={15} />重试</button>}
          />
        </div>
      ) : data ? (
        <>
          <section className="analytics-summary-grid" aria-label="总体概览">
            <SummaryCard icon={PackageSearch} label="已采集商品" value={uniqueProducts} note="当前范围内去重商品数" />
            <SummaryCard icon={SearchCheck} label="发现宣传线索" value={claimRecords} note="出现页面宣传线索的采集记录" />
            <SummaryCard icon={ClipboardCheck} label="建议跟进" value={followUpCount} note="人工复核后建议进一步关注" />
            <SummaryCard icon={FlaskConical} label="当前抽检清单" value={samplingCount} note="当前已纳入的商品" />
          </section>

          <section className="analytics-product-section">
            <SectionHeading title="页面宣传线索" description="看看当前采集商品主要出现了哪些宣传主题。" />
            <div className="analytics-product-card analytics-claim-card">
              <ClaimBars metric={claimTypes} />
              <p className="analytics-friendly-note">一个采集记录可能同时包含多个宣传主题，因此类别数量可以重复计算。</p>
            </div>
          </section>

          <section className="analytics-product-section">
            <SectionHeading title="地区分布" description="从采集上下文或商品页面标称产地两个角度查看商品分布。" />
            <div className="analytics-geo-switch" role="group" aria-label="地区分布类型">
              <button type="button" data-active={geographyMode === "search"} onClick={() => setGeographyMode("search")}>搜索地区</button>
              <button type="button" data-active={geographyMode === "origin"} onClick={() => setGeographyMode("origin")}>标称产地</button>
            </div>
            <div className="analytics-product-card">
              <RegionHeatMap metric={activeGeographyMetric} mode={geographyMode} />
              <p className="analytics-friendly-note">搜索地区表示商品在哪个采集任务地区被发现；标称产地来自商品页面明确声明，两者不能互相替代。</p>
            </div>
          </section>

          <section className="analytics-product-section">
            <SectionHeading title="人工复核与抽检" description="查看线索经过人工判断后的当前处理情况。" />
            <div className="analytics-product-card analytics-review-card">
              <ReviewSummary metric={reviewStatus} />
              <div className="analytics-sampling-callout">
                <div>
                  <span>当前抽检清单</span>
                  <strong>{samplingCount} 个商品</strong>
                </div>
                <a className="primary-button" href="#/sampling">查看抽检清单</a>
              </div>
            </div>
          </section>

          <details className="analytics-friendly-explanation">
            <summary>统计说明</summary>
            <ul>
              <li>页面宣传线索表示商品页面出现了值得关注的宣传主题，不代表违法、功效真实或已检出某种物质。</li>
              <li>“建议跟进 / 暂不纳入 / 待复核”来自人工复核流程，不是自动风险等级。</li>
              <li>地区图中的深浅和数量只表示当前已采集数据的多少，不代表某个地区风险更高。</li>
            </ul>
          </details>
        </>
      ) : null}
    </div>
  );
}
