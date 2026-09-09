import type { ReactNode } from "react";

import type { AppRoute } from "../app/AppRouter";
import { useAppState } from "../app/AppState";
import { Sidebar } from "./Sidebar";

type AppShellProps = {
  route: AppRoute;
  autoExpanded: boolean;
  children: ReactNode;
};

export function AppShell({ route, autoExpanded, children }: AppShellProps) {
  const { currentSamplingCount } = useAppState();

  return (
    <div className="app-shell">
      <Sidebar
        activeSection={route.section}
        autoExpanded={autoExpanded}
        samplingCount={currentSamplingCount}
      />
      <main className="app-main">{children}</main>
    </div>
  );
}
