import { ClipboardList } from "lucide-react";

import { EmptyState } from "../../components/EmptyState";
import { PageHeader } from "../../layout/PageHeader";

export function InspectionArchivePlaceholder() {
  return (
    <div className="page-frame">
      <PageHeader eyebrow="排查管理" title="排查档案" />
      <div className="content-card">
        <EmptyState
          icon={ClipboardList}
          title="排查档案将在 Phase 2 完成"
          description="本阶段保留导航入口，不提前实现任务工作区和淘宝人工验证流程。"
        />
      </div>
    </div>
  );
}
