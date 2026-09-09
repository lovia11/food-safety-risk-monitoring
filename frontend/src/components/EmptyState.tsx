import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

type EmptyStateProps = {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: ReactNode;
};

export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <section className="empty-state">
      <span className="empty-state-icon" aria-hidden="true">
        <Icon size={24} />
      </span>
      <h2>{title}</h2>
      <p>{description}</p>
      {action && <div className="empty-state-action">{action}</div>}
    </section>
  );
}
