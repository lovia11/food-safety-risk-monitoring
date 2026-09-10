import { useEffect, useState } from "react";

import { AppShell } from "../layout/AppShell";
import { InspectionArchivePage } from "../pages/inspections/InspectionArchivePage";
import { InspectionWorkspacePage } from "../pages/inspections/InspectionWorkspacePage";
import { NewInspectionPage } from "../pages/inspections/NewInspectionPage";
import { ProductOverviewPage } from "../pages/products/ProductOverviewPage";
import { SamplingListPage } from "../pages/sampling/SamplingListPage";

export type AppRoute =
  | { section: "products"; productId?: string }
  | { section: "inspections"; taskId?: string }
  | {
      section: "sampling";
      view: "current" | "history";
      listId?: string;
    };

function parseHash(hash: string): AppRoute {
  const parts = hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  const decode = (value: string | undefined) => {
    if (!value) return undefined;
    try {
      return decodeURIComponent(value);
    } catch {
      return undefined;
    }
  };
  if (parts[0] === "inspections") {
    return { section: "inspections", taskId: decode(parts[1]) };
  }
  if (parts[0] === "sampling") {
    return {
      section: "sampling",
      view: parts[1] === "history" ? "history" : "current",
      listId: parts[1] === "history" ? decode(parts[2]) : undefined,
    };
  }
  return { section: "products", productId: decode(parts[1]) };
}

export function AppRouter() {
  const [route, setRoute] = useState<AppRoute>(() => parseHash(window.location.hash));

  useEffect(() => {
    if (!window.location.hash) {
      window.history.replaceState(null, "", "#/products");
      setRoute({ section: "products" });
    }
    const handleHashChange = () => setRoute(parseHash(window.location.hash));
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  const detailOpen = Boolean(
    (route.section === "products" && route.productId) ||
      (route.section === "inspections" && route.taskId && route.taskId !== "new") ||
      (route.section === "sampling" && route.listId),
  );

  return (
    <AppShell route={route} autoExpanded={!detailOpen}>
      {route.section === "products" ? (
        <ProductOverviewPage productId={route.productId} />
      ) : route.section === "inspections" ? (
        route.taskId === "new" ? <NewInspectionPage /> : route.taskId ? <InspectionWorkspacePage taskId={route.taskId} /> : <InspectionArchivePage />
      ) : (
        <SamplingListPage view={route.view} listId={route.listId} />
      )}
    </AppShell>
  );
}
