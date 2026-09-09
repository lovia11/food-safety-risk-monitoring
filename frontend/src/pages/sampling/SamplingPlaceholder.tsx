import { FlaskConical } from "lucide-react";

import { EmptyState } from "../../components/EmptyState";
import { PageHeader } from "../../layout/PageHeader";

export function SamplingPlaceholder() {
  return (
    <div className="page-frame">
      <PageHeader eyebrow="抽检管理" title="抽检清单" />
      <div className="content-card">
        <EmptyState
          icon={FlaskConical}
          title="抽检清单将在 Phase 3 完成"
          description="本阶段只建立只读状态契约，不提供加入、移出或导出操作。"
        />
      </div>
    </div>
  );
}
