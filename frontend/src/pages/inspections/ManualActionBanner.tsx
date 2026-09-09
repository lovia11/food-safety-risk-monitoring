import { CheckCircle2, ShieldAlert } from "lucide-react";
import { useState } from "react";

import type { TaskDetail } from "../../api/contracts";
import { acknowledgeManualAction } from "../../api/tasks";
import { useToast } from "../../components/ToastProvider";

export function ManualActionBanner({ task, onAcknowledged }: { task: TaskDetail; onAcknowledged: () => Promise<void> }) {
  const [sending, setSending] = useState(false);
  const { pushToast } = useToast();
  const state = task.manualAction;
  if (task.businessStatus !== "waiting_for_manual_action" || !state || state.status !== "waiting") return null;

  const acknowledge = async () => {
    setSending(true);
    try {
      await acknowledgeManualAction(task.taskId, state.generation);
      await onAcknowledged();
      pushToast("已通知采集线程立即复检淘宝页面", "info");
    } catch (reason) {
      pushToast(reason instanceof Error ? reason.message : "人工验证确认失败", "danger");
    } finally {
      setSending(false);
    }
  };

  return (
    <section className="manual-action-banner" role="alert">
      <span className="manual-action-icon"><ShieldAlert size={21} /></span>
      <div>
        <h2>淘宝需要人工验证</h2>
        <p>当前任务已安全等待，已采集结果不会因等待丢失。</p>
        <p>请在系统已打开的淘宝 Chrome 窗口完成登录/验证。</p>
        {state.reason && <small>当前提示：{state.reason} · 第 {state.attempt + 1} 次等待</small>}
      </div>
      <button type="button" onClick={() => void acknowledge()} disabled={sending || !state.canAcknowledge}>
        <CheckCircle2 size={16} />
        {state.canAcknowledge ? (sending ? "正在通知" : "我已完成验证") : "正在等待复检"}
      </button>
    </section>
  );
}
