import { AlertCircle, ArrowRight, ClipboardList, Plus, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import type { TaskList, TaskSummary } from "../../api/contracts";
import { getTasks, resumeTask } from "../../api/tasks";
import { EmptyState } from "../../components/EmptyState";
import { LoadingState } from "../../components/LoadingState";
import { StatusBadge } from "../../components/StatusBadge";
import { useToast } from "../../components/ToastProvider";
import { formatDateTime } from "../../domain/product";
import { shouldResumeTask, taskStatusPresentation } from "../../domain/task";
import { PageHeader } from "../../layout/PageHeader";

function TaskCard({ task }: { task: TaskSummary }) {
  const [resuming, setResuming] = useState(false);
  const { pushToast } = useToast();
  const status = taskStatusPresentation[task.businessStatus];
  const open = async () => {
    if (shouldResumeTask(task)) {
      setResuming(true);
      try {
        await resumeTask(task.taskId);
      } catch (reason) {
        pushToast(reason instanceof Error ? reason.message : "继续任务失败", "danger");
        setResuming(false);
        return;
      }
    }
    window.location.hash = `#/inspections/${encodeURIComponent(task.taskId)}`;
  };
  return (
    <article className="inspection-card">
      <div className="inspection-card-heading">
        <div>
          <h2>{task.displayName}</h2>
          <p>{task.taskType === "monitor" ? task.targetName || task.keyword : `搜索词：${task.keyword}`}</p>
        </div>
        <StatusBadge tone={status.tone}>{status.label}</StatusBadge>
      </div>
      <p className="inspection-created">创建于 {formatDateTime(task.createdAt)}</p>
      <dl className="inspection-metrics">
        <div><dt>采集进度</dt><dd>{task.archiveSummary.detailCompleted}/{task.archiveSummary.detailTarget}</dd></div>
        <div><dt>发现线索</dt><dd>{task.archiveSummary.clueProducts}</dd></div>
        <div><dt>建议跟进</dt><dd>{task.archiveSummary.recommendFollowUpCount}</dd></div>
        <div><dt>暂不纳入</dt><dd>{task.archiveSummary.noFurtherActionCount}</dd></div>
      </dl>
      <div className="inspection-card-meta">
        {task.archiveSummary.currentSamplingItems > 0 && (
          <span>当前清单中 {task.archiveSummary.currentSamplingItems}</span>
        )}
        {task.archiveSummary.errorCount > 0 && (
          <span className="danger-text">异常 {task.archiveSummary.errorCount}</span>
        )}
        <small>Task ID {task.taskId}</small>
      </div>
      <button type="button" className="card-action" onClick={() => void open()} disabled={resuming}>
        {resuming ? "正在继续任务" : task.actionLabel} <ArrowRight size={16} />
      </button>
    </article>
  );
}

export function InspectionArchivePage() {
  const [data, setData] = useState<TaskList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setData(await getTasks());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "排查档案加载失败");
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => { void load(); }, [load]);

  return (
    <div className="page-frame archive-page">
      <PageHeader
        eyebrow="排查管理"
        title="排查档案"
        description="按持久人工复核结果查看每次排查，不受当前抽检清单变化影响。"
        actions={<a className="primary-button" href="#/inspections/new"><Plus size={16} />新建排查</a>}
      />
      {loading ? (
        <LoadingState label="正在读取排查档案" />
      ) : error ? (
        <EmptyState icon={AlertCircle} title="排查档案加载失败" description={error} action={
          <button type="button" className="primary-button" onClick={() => void load()}><RefreshCw size={15} />重试</button>
        } />
      ) : !data?.tasks.length ? (
        <EmptyState icon={ClipboardList} title="尚无排查档案" description="创建一次排查后，可在这里查看进度与人工处理统计。" action={
          <a className="primary-button" href="#/inspections/new">新建排查</a>
        } />
      ) : (
        <div className="inspection-grid">
          {data.tasks.map((task) => <TaskCard key={task.taskId} task={task} />)}
        </div>
      )}
    </div>
  );
}
