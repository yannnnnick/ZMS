import type { ReactNode } from "react";
import { Icon } from "./Icon";
import type { IconName } from "./Icon";

export function Panel({ title, icon, children }: { title: string; icon: IconName; children: ReactNode }) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <Icon name={icon} />
        <h2>{title}</h2>
      </div>
      {children}
    </section>
  );
}
