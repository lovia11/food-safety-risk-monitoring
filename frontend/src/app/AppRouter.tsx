import { useEffect, useState } from "react";

import { AppShell } from "../layout/AppShell";
import { InspectionArchivePlaceholder } from "../pages/inspections/InspectionArchivePlaceholder";
import { ProductOverviewPage } from "../pages/products/ProductOverviewPage";
import { SamplingPlaceholder } from "../pages/sampling/SamplingPlaceholder";

export type AppRoute =
  | { section: "products"; productId?: string }
  | { section: "inspections"; taskId?: string }
  | { section: "sampling"; listId?: string };

function parseHash(hash: string): AppRoute {
  const parts = hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  if (parts[0] === "inspections") {
    return { section: "inspections", taskId: parts[1] };
  }
  if (parts[0] === "sampling") {
    return {
      section: "sampling",
      listId: parts[1] === "history" ? parts[2] : undefined,
    };
  }
  return { section: "products", productId: parts[1] };
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
      (route.section === "inspections" && route.taskId) ||
      (route.section === "sampling" && route.listId),
  );

  return (
    <AppShell route={route} autoExpanded={!detailOpen}>
      {route.section === "products" ? (
        <ProductOverviewPage productId={route.productId} />
      ) : route.section === "inspections" ? (
        <InspectionArchivePlaceholder />
      ) : (
        <SamplingPlaceholder />
      )}
    </AppShell>
  );
}
