import { X } from "lucide-react";
import type { ReactNode } from "react";

type DrawerProps = {
  title: string;
  subtitle?: string;
  onClose: () => void;
  children: ReactNode;
};

export function Drawer({ title, subtitle, onClose, children }: DrawerProps) {
  return (
    <aside className="detail-drawer" aria-label={title}>
      <div className="detail-drawer-header">
        <div>
          <p className="detail-drawer-kicker">商品快照档案</p>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        <button
          type="button"
          className="icon-button"
          onClick={onClose}
          aria-label="关闭商品详情"
          title="关闭商品详情"
        >
          <X size={18} />
        </button>
      </div>
      <div className="detail-drawer-body">{children}</div>
    </aside>
  );
}
