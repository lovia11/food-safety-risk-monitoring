import { AlertCircle, ArrowLeft, Play, Search } from "lucide-react";
import { type FormEvent, useEffect, useMemo, useState } from "react";

import type { MonitorTarget, TaskList } from "../../api/contracts";
import { createTask, getMonitorTargets, getTasks } from "../../api/tasks";
import { LoadingState } from "../../components/LoadingState";
import { buildWebTaskRequest } from "../../domain/task";
import { PageHeader } from "../../layout/PageHeader";

export function NewInspectionPage() {
  const [mode, setMode] = useState<"quick" | "monitor">("quick");
  const [name, setName] = useState("");
  const [keyword, setKeyword] = useState("");
  const [targetId, setTargetId] = useState("");
  const [analysisLimit, setAnalysisLimit] = useState(10);
  const [targets, setTargets] = useState<MonitorTarget[]>([]);
  const [tasks, setTasks] = useState<TaskList | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([getTasks(controller.signal), getMonitorTargets(controller.signal)])
      .then(([taskData, targetData]) => {
        setTasks(taskData);
        setTargets(targetData);
        setTargetId(targetData[0]?.target_id || "");
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : "创建选项加载失败");
        }
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  const selectedTarget = useMemo(
    () => targets.find((target) => target.target_id === targetId),
    [targetId, targets],
  );
  const queries = selectedTarget?.queries
    .filter((query) => query.enabled && query.validation_status === "search_validated")
    .sort((left, right) => left.order - right.order) || [];
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (tasks?.activeTaskId) return;
    setSubmitting(true);
    setError("");
    try {
      const payload = buildWebTaskRequest({
        mode,
        name,
        keyword,
        targetId,
        analysisLimit,
      });
      const created = await createTask(payload);
      window.location.hash = `#/inspections/${encodeURIComponent(created.task.id)}`;
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "排查创建失败");
      setSubmitting(false);
    }
  };

  if (loading) return <div className="page-frame"><LoadingState label="正在读取排查配置" /></div>;
  return (
    <div className="page-frame new-inspection-page">
      <PageHeader eyebrow="排查管理" title="新建排查" description="搜索词和对象词组均来自明确输入或已保存配置。" actions={
        <a className="secondary-button" href="#/inspections"><ArrowLeft size={15} />返回档案</a>
      } />
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
          <label>搜索关键词<div className="input-with-icon"><Search size={16} /><input required value={keyword} maxLength={80} onChange={(event) => setKeyword(event.target.value)} /></div></label>
        ) : (
          <>
            <label>监测对象<select required value={targetId} onChange={(event) => setTargetId(event.target.value)}>{targets.map((target) => <option key={target.target_id} value={target.target_id}>{target.standard_name}</option>)}</select></label>
            <div className="query-preview"><strong>将使用已验证搜索词</strong>{queries.length ? <ul>{queries.map((query) => <li key={query.query_id}>{query.query_text}</li>)}</ul> : <p>该对象暂无可执行的已验证搜索词。</p>}</div>
          </>
        )}
        <label>
          最多分析商品数
          <input type="number" min={1} max={50} value={analysisLimit} onChange={(event) => setAnalysisLimit(Number(event.target.value))} />
          <small>搜索结果合并去重后，最多选择这些商品继续采集详情、识别文字并分析线索。</small>
        </label>
        {error && <div className="inline-message" data-tone="danger"><AlertCircle size={17} />{error}</div>}
        <button type="submit" className="primary-button start-task-button" disabled={Boolean(tasks?.activeTaskId) || submitting || (mode === "monitor" && !queries.length)}>
          <Play size={16} />{submitting ? "正在启动" : "开始排查"}
        </button>
      </form>
    </div>
  );
}
