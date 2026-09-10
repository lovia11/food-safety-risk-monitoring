import { X } from "lucide-react";
import { type ReactNode, useEffect, useId, useRef } from "react";

type DrawerProps = {
  title: string;
  subtitle?: string;
  kicker?: string;
  closeLabel?: string;
  onClose: () => void;
  children: ReactNode;
};

const FOCUSABLE = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  '[tabindex]:not([tabindex="-1"])',
].join(",");

export function Drawer({
  title,
  subtitle,
  kicker = "商品快照档案",
  closeLabel = "关闭商品详情",
  onClose,
  children,
}: DrawerProps) {
  const drawerRef = useRef<HTMLElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const closeHandlerRef = useRef(onClose);
  const titleId = useId();
  closeHandlerRef.current = onClose;

  useEffect(() => {
    const restoreTarget = document.activeElement as HTMLElement | null;
    const drawer = drawerRef.current;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        closeHandlerRef.current();
        return;
      }
      if (event.key !== "Tab" || !drawer) return;
      const focusable = Array.from(
        drawer.querySelectorAll<HTMLElement>(FOCUSABLE),
      ).filter((element) => !element.hasAttribute("disabled"));
      const first = focusable[0];
      const last = focusable.at(-1);
      if (!first || !last) return;
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    drawer?.addEventListener("keydown", handleKeyDown);
    closeRef.current?.focus();
    return () => {
      drawer?.removeEventListener("keydown", handleKeyDown);
      if (restoreTarget?.isConnected) restoreTarget.focus();
    };
  }, []);

  return (
    <aside
      ref={drawerRef}
      className="detail-drawer"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
    >
      <div className="detail-drawer-header">
        <div>
          <p className="detail-drawer-kicker">{kicker}</p>
          <h2 id={titleId}>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        <button
          type="button"
          ref={closeRef}
          className="icon-button"
          onClick={onClose}
          aria-label={closeLabel}
          title={closeLabel}
        >
          <X size={18} />
        </button>
      </div>
      <div className="detail-drawer-body">{children}</div>
    </aside>
  );
}
