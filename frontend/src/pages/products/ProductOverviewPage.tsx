import { PackageSearch } from "lucide-react";

import { EmptyState } from "../../components/EmptyState";
import { PageHeader } from "../../layout/PageHeader";

export function ProductOverviewPage({ productId }: { productId?: string }) {
  return (
    <div className="page-frame">
      <PageHeader
        eyebrow="商品档案"
        title="商品总览"
        description="按商品汇总排查快照，并查看人工复核与抽检辅助信息。"
      />
      <div className="content-card">
        <EmptyState
          icon={PackageSearch}
          title={productId ? "正在准备商品详情" : "正在接入真实商品索引"}
          description="Phase 1 商品查询与 Snapshot 工作区将在此基础上连接本地 API。"
        />
      </div>
    </div>
  );
}
