import type { ReactNode } from "react";

import type { StatusTone } from "../domain/presentation";

export function StatusBadge({
  tone = "neutral",
  children,
}: {
  tone?: StatusTone;
  children: ReactNode;
}) {
  return (
    <span className="status-badge" data-tone={tone}>
      {children}
    </span>
  );
}
