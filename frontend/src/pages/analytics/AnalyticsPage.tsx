import {
  AlertCircle,
  ClipboardCheck,
  FlaskConical,
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
type Position = [number, number];
type PolygonGeometry = { type: "Polygon"; coordinates: Position[][] };
type MultiPolygonGeometry = { type: "MultiPolygon"; coordinates: Position[][][] };
type ChinaFeature = {
  properties?: { name?: string };
  geometry?: PolygonGeometry | MultiPolygonGeometry;
};
type ChinaGeoJson = { features?: ChinaFeature[] };

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
    return <div className="analytics-friendly-empty">当前范围内还没有可展示的页面宣传线索分类数据。</div>;
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
  return (
    <div className="analytics-review-grid">
      {Object.entries(REVIEW_LABELS).map(([key, label]) => {
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

function geometryPath(geometry: PolygonGeometry | MultiPolygonGeometry | undefined) {
  if (!geometry) return "";
  const width = 520;
  const height = 300;
  const minLon = 73;
  const maxLon = 135;
  const minLat = 18;
  const maxLat = 54;
  const longitudeFactor = Math.cos((35 * Math.PI) / 180);
  const scale = Math.min(
    (width - 22) / ((maxLon - minLon) * longitudeFactor),
    (height - 18) / (maxLat - minLat),
  );
  const mapWidth = (maxLon - minLon) * longitudeFactor * scale;
  const mapHeight = (maxLat - minLat) * scale;
  const offsetX = (width - mapWidth) / 2;
  const offsetY = (height - mapHeight) / 2;
  const project = (coordinate: Position) => [
    offsetX + (coordinate[0] - minLon) * longitudeFactor * scale,
    offsetY + (maxLat - coordinate[1]) * scale,
  ];
  const ringPath = (ring: Position[]) => {
    const points = ring.filter((point) => point[0] >= 72 && point[0] <= 136 && point[1] >= 17 && point[1] <= 55);
    if (points.length < 3) return "";
    return `${points.map((point, index) => {
      const [x, y] = project(point);
      return `${index ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`;
    }).join(" ")} Z`;
  };
  const polygons = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates;
  return polygons.flatMap((polygon) => polygon.map(ringPath)).filter(Boolean).join(" ");
}

function provinceFill(value: number, max: number) {
  if (value <= 0) return "#edf5ff";
  const ratio = max > 0 ? value / max : 0;
  if (ratio >= 0.75) return "#2563eb";
  if (ratio >= 0.5) return "#5a9bf2";
  if (ratio >= 0.25) return "#8dbcf6";
  return "#bdd8fa";
}

function RegionHeatMap({ metric, mode }: { metric: AnalyticsMetric | null; mode: GeographyMode }) {
  const [geoJson, setGeoJson] = useState<ChinaGeoJson | null>(null);
  const [mapError, setMapError] = useState(false);
  const buckets = metric?.buckets ?? [];
  const ordinary = buckets.filter((bucket) => !isSpecialRegionBucket(bucket) && bucket.count > 0);
  const ranked = [...ordinary].sort((a, b) => b.count - a.count);
  const max = Math.max(1, ...ranked.map((bucket) => bucket.count));
  const special = buckets.filter((bucket) => isSpecialRegionBucket(bucket) && bucket.count > 0);
  const counts = useMemo(
    () => new Map(ordinary.map((bucket) => [normalizeProvince(bucket.label || bucket.key), bucket.count])),
    [ordinary],
  );

  useEffect(() => {
    const controller = new AbortController();
    setMapError(false);
    fetch("/data/china-provinces.geojson", { signal: controller.signal, cache: "force-cache" })
      .then((response) => {
        if (!response.ok) throw new Error(`地图数据请求失败：${response.status}`);
        return response.json() as Promise<ChinaGeoJson>;
      })
      .then(setGeoJson)
      .catch(() => {
        if (!controller.signal.aborted) setMapError(true);
      });
    return () => controller.abort();
  }, []);

  if (!metric || metric.denominator === 0) {
    return <div className="analytics-friendly-empty">当前范围内还没有地区分布数据。</div>;
  }

  return (
    <div className="analytics-map-layout">
      <div className="analytics-map-panel">
        {mapError ? (
          <div className="analytics-friendly-empty">中国地图数据暂时无法加载。</div>
        ) : !geoJson ? (
          <div className="analytics-friendly-empty">正在加载中国地图…</div>
        ) : (
          <svg
            className="analytics-china-map"
            viewBox="0 0 520 300"
            role="img"
            aria-label={mode === "search" ? "已采集商品搜索地区分布图" : "商品标称产地分布图"}
          >
            {(geoJson.features ?? []).map((feature, index) => {
              const rawName = feature.properties?.name ?? "";
              const name = normalizeProvince(rawName);
              const value = counts.get(name) ?? 0;
              const path = geometryPath(feature.geometry);
              if (!path) return null;
              return (
                <path
                  key={`${name}-${index}`}
                  d={path}
                  fill={provinceFill(value, max)}
                  fillRule="evenodd"
                  stroke="#ffffff"
                  strokeWidth="0.8"
                >
                  <title>{`${name || rawName}：${value} 件`}</title>
                </path>
              );
            })}
          </svg>
        )}
        <p className="analytics-map-caption">省份颜色深浅仅表示当前数据中的商品数量，不表示地区风险高低。</p>
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
        title="数据统计"
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
              <li>地区图中的颜色深浅和数量只表示当前已采集数据的多少，不代表某个地区风险更高。</li>
            </ul>
          </details>
        </>
      ) : null}
    </div>
  );
}
