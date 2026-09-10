import { AlertCircle, ArrowLeft, Check, ClipboardCheck, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { ProductPage, SnapshotSummary, TaskDetail } from "../../api/contracts";
import { getProducts } from "../../api/products";
import { getTask } from "../../api/tasks";
import { EmptyState } from "../../components/EmptyState";
import { LoadingState } from "../../components/LoadingState";
import { StatusBadge } from "../../components/StatusBadge";
import { taskFlowSteps, taskStatusPresentation } from "../../domain/task";
import { InspectionWorkspaceDetail } from "./InspectionWorkspaceDetail";
import { ManualActionBanner } from "./ManualActionBanner";
import { type QueueFilter, ReviewQueue } from "./ReviewQueue";

type ReviewChange = {
  type: "decision" | "membership_removed" | "membership_restored";
  decision?: "recommend_follow_up" | "no_further_action";
};

const workspaceQuery = (taskId: string) => ({
  query: "", targetId: "", taskId, reviewStatus: "", effect: "", samplingStatus: "",
  collectedFrom: "", collectedTo: "", page: 1, pageSize: 100,
});

function FlowStrip({ task }: { task: TaskDetail }) {
  return (
    <ol className="task-flow" aria-label="排查流程">
      {taskFlowSteps(task).map((step, index) => (
        <li key={step.key} data-state={step.state}>
          <span>{step.state === "done" ? <Check size={13} /> : index + 1}</span>
          <strong>{step.label}</strong>
          {step.target > 0 && step.key !== "search" && (
            <small>{step.completed}/{step.target}</small>
          )}
        </li>
      ))}
    </ol>
  );
}

export function InspectionWorkspacePage({ taskId }: { taskId: string }) {
  const [task, setTask] = useState<TaskDetail | null>(null);
  const [products, setProducts] = useState<SnapshotSummary[]>([]);
  const [selectedSnapshotId, setSelectedSnapshotId] = useState("");
  const [filter, setFilter] = useState<QueueFilter>("all");
  const [pendingCompleted, setPendingCompleted] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const initialized = useRef(false);

  const loadTask = useCallback(async () => {
    const result = await getTask(taskId);
    setTask(result);
    return result;
  }, [taskId]);

  const loadProducts = useCallback(async () => {
    const result: ProductPage = await getProducts(workspaceQuery(taskId));
    setProducts(result.products);
    return result.products;
  }, [taskId]);

  const load = useCallback(async () => {
    setError("");
    try {
      const [, items] = await Promise.all([loadTask(), loadProducts()]);
      const reviewable = items.filter((item) => item.readiness.reviewEligible);
      if (!initialized.current) {
        const pending = reviewable.find((item) => item.sampling.decisionStatus === "pending");
        setFilter(pending ? "pending" : "all");
        setSelectedSnapshotId((pending || reviewable[0])?.snapshotId || "");
        initialized.current = true;
      } else {
        setSelectedSnapshotId((current) => (
          reviewable.some((item) => item.snapshotId === current)
            ? current
            : reviewable[0]?.snapshotId || ""
        ));
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "排查工作区加载失败");
    } finally {
      setLoading(false);
    }
  }, [loadProducts, loadTask]);

  useEffect(() => {
    initialized.current = false;
    setLoading(true);
    void load();
  }, [load, taskId]);

  useEffect(() => {
    if (!task?.active) return;
    const interval = window.setInterval(() => {
      void Promise.all([loadTask(), loadProducts()]).catch(() => undefined);
    }, 3000);
    return () => window.clearInterval(interval);
  }, [loadProducts, loadTask, task?.active]);

  const handleChanged = async (change?: ReviewChange) => {
    const previous = products;
    const currentIndex = previous.findIndex((item) => item.snapshotId === selectedSnapshotId);
    const [nextProducts] = await Promise.all([loadProducts(), loadTask()]);
    if (change?.type === "decision") {
      const ordered = [...nextProducts.slice(currentIndex + 1), ...nextProducts.slice(0, Math.max(currentIndex, 0))];
      const nextPending = ordered.find((item) => item.sampling.decisionStatus === "pending");
      if (nextPending) {
        setFilter("pending");
        setSelectedSnapshotId(nextPending.snapshotId);
        setPendingCompleted(false);
      } else {
        setPendingCompleted(true);
      }
    }
  };

  const status = task ? taskStatusPresentation[task.businessStatus] : null;
  const selected = useMemo(() => products.find((item) => item.snapshotId === selectedSnapshotId), [products, selectedSnapshotId]);

  if (loading) return <div className="page-frame inspection-workspace-page"><LoadingState label="正在打开排查工作区" /></div>;
  if (error || !task) return <div className="page-frame"><EmptyState icon={AlertCircle} title="排查工作区加载失败" description={error || "任务不存在"} action={<button type="button" className="primary-button" onClick={() => { setLoading(true); void load(); }}><RefreshCw size={15} />重试</button>} /></div>;

  return (
    <div className="inspection-workspace-page">
      <header className="workspace-page-header">
        <div>
          <a href="#/inspections"><ArrowLeft size={14} />排查档案</a>
          <div className="workspace-title-line"><h1>{task.displayName}</h1>{status && <StatusBadge tone={status.tone}>{status.label}</StatusBadge>}</div>
          <p>{task.taskType === "monitor" ? task.targetName || task.keyword : `搜索词：${task.keyword}`} · {task.message}</p>
        </div>
        <small>Task ID {task.taskId}</small>
      </header>
      <ManualActionBanner task={task} onAcknowledged={async () => { await loadTask(); }} />
      <FlowStrip task={task} />
      <div className="inspection-split">
        <ReviewQueue products={products} selectedSnapshotId={selectedSnapshotId} filter={filter} onFilterChange={(next) => { setFilter(next); setPendingCompleted(false); }} onSelect={(id) => { setSelectedSnapshotId(id); setPendingCompleted(false); }} pendingCompleted={pendingCompleted} />
        <main className="workspace-detail-pane">
          {selected ? <InspectionWorkspaceDetail key={selected.snapshotId} snapshotId={selected.snapshotId} onChanged={handleChanged} /> : <EmptyState icon={ClipboardCheck} title="尚无可研判商品" description="采集到商品快照后，将在左侧队列中显示。" />}
        </main>
      </div>
    </div>
  );
}
