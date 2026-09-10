import {
  ClipboardList,
  FlaskConical,
  PackageSearch,
  PanelLeftClose,
  PanelLeftOpen,
  ScanSearch,
} from "lucide-react";
import { useEffect, useState } from "react";

const SIDEBAR_STORAGE_KEY = "food-risk.sidebar-state";

type SidebarProps = {
  activeSection: "products" | "inspections" | "sampling";
  autoExpanded: boolean;
  samplingCount: number | null;
};

const navigation = [
  { id: "products", label: "商品总览", href: "#/products", icon: PackageSearch },
  {
    id: "inspections",
    label: "排查档案",
    href: "#/inspections",
    icon: ClipboardList,
  },
  { id: "sampling", label: "抽检清单", href: "#/sampling", icon: FlaskConical },
] as const;

function storedPreference(): boolean | null {
  const value = window.sessionStorage.getItem(SIDEBAR_STORAGE_KEY);
  return value === "expanded" ? true : value === "collapsed" ? false : null;
}

export function Sidebar({
  activeSection,
  autoExpanded,
  samplingCount,
}: SidebarProps) {
  const [manualPreference, setManualPreference] = useState<boolean | null>(() =>
    storedPreference(),
  );
  const expanded = manualPreference ?? autoExpanded;

  useEffect(() => {
    const handleStorage = () => setManualPreference(storedPreference());
    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  const toggle = () => {
    const next = !expanded;
    setManualPreference(next);
    window.sessionStorage.setItem(
      SIDEBAR_STORAGE_KEY,
      next ? "expanded" : "collapsed",
    );
  };

  return (
    <aside className="sidebar" data-expanded={expanded}>
      <div className="sidebar-brand">
        <span className="sidebar-logo" aria-hidden="true">
          <ScanSearch size={20} strokeWidth={2.2} />
        </span>
        {expanded && (
          <span className="sidebar-brand-copy">
            <strong>食安线索</strong>
            <small>抽检辅助筛查</small>
          </span>
        )}
      </div>

      <nav className="sidebar-nav" aria-label="主导航">
        {navigation.map((item) => {
          const Icon = item.icon;
          const active = item.id === activeSection;
          return (
            <a
              key={item.id}
              href={item.href}
              className="sidebar-link"
              data-active={active}
              aria-current={active ? "page" : undefined}
              aria-label={!expanded ? item.label : undefined}
              title={!expanded ? item.label : undefined}
            >
              <Icon size={18} aria-hidden="true" />
              {expanded && <span>{item.label}</span>}
              {item.id === "sampling" && samplingCount !== null && (
                <span className="sidebar-badge">{samplingCount}</span>
              )}
            </a>
          );
        })}
      </nav>

      <button
        type="button"
        className="sidebar-toggle"
        onClick={toggle}
        aria-label={expanded ? "收起侧边栏" : "展开侧边栏"}
        title={expanded ? "收起侧边栏" : "展开侧边栏"}
      >
        {expanded ? <PanelLeftClose size={18} /> : <PanelLeftOpen size={18} />}
        {expanded && <span>收起导航</span>}
      </button>
    </aside>
  );
}
