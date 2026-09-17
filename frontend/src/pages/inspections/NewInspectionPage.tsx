import { AlertCircle, ArrowLeft, Check, Play, Search } from "lucide-react";
import { type FormEvent, useEffect, useMemo, useState } from "react";

import type { MonitorTarget, MonitorTargetList, TaskList } from "../../api/contracts";
import { createTask, getMonitorTargets, getTasks } from "../../api/tasks";
import { LoadingState } from "../../components/LoadingState";
import {
  canCreateMonitorTask,
  filterMonitorTargets,
  monitorAvailabilityLabel,
  monitorAvailabilityMessage,
  type MonitorAvailabilityFilter,
} from "../../domain/monitorTargets";
import { buildWebTaskRequest } from "../../domain/task";
import { PageHeader } from "../../layout/PageHeader";

const AVAILABILITY_FILTERS: Array<{
  value: MonitorAvailabilityFilter;
  label: string;
}> = [
  { value: "all", label: "全部" },
  { value: "operational", label: "可排查" },
  { value: "query_pending", label: "待验证" },
  { value: "paused", label: "暂停" },
];

export function NewInspectionPage() {
  const [mode, setMode] = useState<"quick" | "monitor">("quick");
  const [name, setName] = useState("");
  const [keyword, setKeyword] = useState("");
  const [targetId, setTargetId] = useState("");
  const [targetSearch, setTargetSearch] = useState("");
  const [availabilityFilter, setAvailabilityFilter] =
    useState<MonitorAvailabilityFilter>("all");
  const [quickAnalysisLimit, setQuickAnalysisLimit] = useState(10);
  const [monitorCandidateLimit, setMonitorCandidateLimit] = useState(30);
  const [monitorAnalysisLimit, setMonitorAnalysisLimit] = useState(8);
  const [targetList, setTargetList] = useState<MonitorTargetList | null>(null);
  const [tasks, setTasks] = useState<TaskList | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      getTasks(controller.signal),
      getMonitorTargets("reference", controller.signal),
    ])
      .then(([taskData, targetData]) => {
        setTasks(taskData);
        setTargetList(targetData);
        setTargetId(
          targetData.targets.find((target) => target.availability === "operational")
            ?.target_id || targetData.targets[0]?.target_id || "",
        );
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : "创建选项加载失败");
        }
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  const targets = targetList?.targets || [];
  const selectedTarget = useMemo(
    () => targets.find((target) => target.target_id === targetId),
    [targetId, targets],
  );
  const visibleTargets = useMemo(
    () => filterMonitorTargets(targets, targetSearch, availabilityFilter),
    [availabilityFilter, targetSearch, targets],
  );
  const monitorReady = canCreateMonitorTask(selectedTarget);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (tasks?.activeTaskId || (mode === "monitor" && !monitorReady)) return;
    setSubmitting(true);
    setError("");
    try {
      const payload = buildWebTaskRequest({
        mode,
        name,
        keyword,
        targetId,
        analysisLimit: mode === "quick" ? quickAnalysisLimit : monitorAnalysisLimit,
        candidateLimit: mode === "monitor" ? monitorCandidateLimit : undefined,
      });
      const created = await createTask(payload);
      window.location.hash = `#/inspections/${encodeURIComponent(created.task.id)}`;
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "排查创建失败");
      setSubmitting(false);
    }
  };

  if (loading) {
    return <div className="page-frame"><LoadingState label="正在读取排查配置" /></div>;
  }
  return (
    <div className="page-frame new-inspection-page">
      <PageHeader
        eyebrow="排查管理"
        title="新建排查"
        description="快速任务使用明确输入；检测任务仅运行已经完成真实搜索验证的对象策略。"
        actions={<a className="secondary-button" href="#/inspections"><ArrowLeft size={15} />返回档案</a>}
      />
      {tasks?.activeTaskId && (
        <div className="active-task-notice">
          <AlertCircle size={18} />
          <div><strong>已有排查正在运行</strong><p>单机采集器一次只运行一个任务。</p></div>
          <a href={`#/inspections/${encodeURIComponent(tasks.activeTaskId)}`}>查看当前排查</a>
        </div>
      )}
      <form className="inspection-form" onSubmit={submit}>
        <div className="task-mode-tabs" role="tablist">
          <button type="button" data-active={mode === "quick"} onClick={() => setMode("quick")}>快速任务</button>
          <button type="button" data-active={mode === "monitor"} onClick={() => setMode("monitor")}>检测任务</button>
        </div>
        <label>排查名称（可选）<input value={name} maxLength={120} onChange={(event) => setName(event.target.value)} placeholder="例如：九月重点商品排查" /></label>
        <label>采集平台<input value="淘宝" readOnly /></label>
        {mode === "quick" ? (
          <>
            <label>搜索关键词<div className="input-with-icon"><Search size={16} /><input required value={keyword} maxLength={80} onChange={(event) => setKeyword(event.target.value)} /></div></label>
            <label>
              最多分析商品数
              <input type="number" min={1} max={50} value={quickAnalysisLimit} onChange={(event) => setQuickAnalysisLimit(Number(event.target.value))} />
              <small>快速任务会按搜索顺序选择这些商品继续采集详情、识别文字并分析线索。</small>
            </label>
          </>
        ) : (
          <>
            <MonitorTargetPicker
              targetList={targetList}
              visibleTargets={visibleTargets}
              selectedTarget={selectedTarget}
              targetSearch={targetSearch}
              availabilityFilter={availabilityFilter}
              onSearch={setTargetSearch}
              onFilter={setAvailabilityFilter}
              onSelect={setTargetId}
            />
            <label>
              每个搜索词最多收集候选
              <input type="number" min={1} max={50} value={monitorCandidateLimit} onChange={(event) => setMonitorCandidateLimit(Number(event.target.value))} />
              <small>先从每个已验证搜索策略收集候选商品，只读取搜索卡片，不进入详情页。</small>
            </label>
            <label>
              最多进入详情分析
              <input type="number" min={1} max={50} value={monitorAnalysisLimit} onChange={(event) => setMonitorAnalysisLimit(Number(event.target.value))} />
              <small>候选合并去重后，系统按搜索靠前、可见宣传线索和探索样本选择这些商品进入详情、OCR 与后续分析。</small>
            </label>
            <div className="monitor-target-guidance" data-availability="operational">
              当前设置：每个搜索词最多收集 {monitorCandidateLimit} 个候选，合并去重后最多分析 {monitorAnalysisLimit} 个商品。
            </div>
          </>
        )}
        {mode === "monitor" && selectedTarget && (
          <div className="monitor-target-guidance" data-availability={selectedTarget.availability}>
            {monitorAvailabilityMessage(selectedTarget)}
          </div>
        )}
        {error && <div className="inline-message" data-tone="danger"><AlertCircle size={17} />{error}</div>}
        <button
          type="submit"
          className="primary-button start-task-button"
          disabled={Boolean(tasks?.activeTaskId) || submitting || (mode === "monitor" && !monitorReady)}
        >
          <Play size={16} />{submitting ? "正在启动" : "开始排查"}
        </button>
      </form>
    </div>
  );
}

function MonitorTargetPicker({
  targetList,
  visibleTargets,
  selectedTarget,
  targetSearch,
  availabilityFilter,
  onSearch,
  onFilter,
  onSelect,
}: {
  targetList: MonitorTargetList | null;
  visibleTargets: MonitorTarget[];
  selectedTarget: MonitorTarget | undefined;
  targetSearch: string;
  availabilityFilter: MonitorAvailabilityFilter;
  onSearch: (value: string) => void;
  onFilter: (value: MonitorAvailabilityFilter) => void;
  onSelect: (value: string) => void;
}) {
  const coverage = targetList?.coverage;
  return (
    <section className="monitor-target-picker" aria-label="监测对象">
      <div className="monitor-target-heading">
        <div><strong>监测对象</strong><span>完整官方目录与当前可排查范围分别统计</span></div>
        <p>官方目录 {coverage?.reference_target_count || targetList?.count || 0}项 · 当前可排查 {coverage?.operational_target_count || 0}项</p>
      </div>
      <div className="input-with-icon monitor-target-search">
        <Search size={16} />
        <input value={targetSearch} onChange={(event) => onSearch(event.target.value)} placeholder="搜索官方标准名称或已验证搜索策略" />
      </div>
      <div className="monitor-target-filters" aria-label="对象可用状态">
        {AVAILABILITY_FILTERS.map((item) => (
          <button key={item.value} type="button" data-active={availabilityFilter === item.value} onClick={() => onFilter(item.value)}>{item.label}</button>
        ))}
      </div>
      <div className="monitor-target-results" role="listbox" aria-label="官方监测对象">
        {visibleTargets.length ? visibleTargets.map((target) => (
          <button
            type="button"
            role="option"
            aria-selected={selectedTarget?.target_id === target.target_id}
            className="monitor-target-row"
            key={target.target_id}
            data-selected={selectedTarget?.target_id === target.target_id}
            onClick={() => onSelect(target.target_id)}
          >
            <span className="monitor-target-row-main">
              <span className="monitor-target-name">{target.standard_name}</span>
              <span className="monitor-availability-badge" data-availability={target.availability}>{monitorAvailabilityLabel(target)}</span>
              {selectedTarget?.target_id === target.target_id && <Check size={15} aria-hidden="true" />}
            </span>
            {target.availability === "operational" ? (
              <span className="monitor-query-line">
                <span>已验证搜索策略 {target.validated_query_count}</span>
                {target.validated_queries.map((query) => <span className="monitor-query-chip" key={query.query_id}>{query.query_text}</span>)}
              </span>
            ) : target.availability === "paused" ? (
              <span className="monitor-target-note">{target.availability_reason || "现有搜索策略暂缓"}</span>
            ) : (
              <span className="monitor-target-note">已纳入官方食药物质目录，当前尚无经过真实搜索验证的搜索策略</span>
            )}
          </button>
        )) : <div className="monitor-target-empty">没有符合当前搜索与筛选条件的对象。</div>}
      </div>
    </section>
  );
}
