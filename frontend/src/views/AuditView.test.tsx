import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { AuditView } from "./AuditView";
import type { AuditLog } from "../types";

describe("AuditView", () => {
  it("renders a list of audit logs correctly", () => {
    const auditLogs: AuditLog[] = [
      {
        id: 1,
        timestamp: "2024-01-01T12:00:00Z",
        action: "CREATE",
        entity_type: "Species",
        entity_id: "100",
        actor_user_id: 42,
        details: { key: "value" },
      },
    ];

    render(<AuditView auditLogs={auditLogs} />);

    // Table headers
    expect(screen.getByText("Zeitpunkt")).toBeInTheDocument();
    expect(screen.getByText("Aktion")).toBeInTheDocument();
    expect(screen.getByText("Entitaet")).toBeInTheDocument();
    expect(screen.getByText("Nutzer-ID")).toBeInTheDocument();
    expect(screen.getByText("Details")).toBeInTheDocument();

    // Data rows
    const formattedDate = new Date("2024-01-01T12:00:00Z").toLocaleString("de-DE");
    expect(screen.getByText(formattedDate)).toBeInTheDocument();
    expect(screen.getByText("CREATE")).toBeInTheDocument();
    expect(screen.getByText("Species #100")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText('{"key":"value"}')).toBeInTheDocument();
  });

  it("handles missing optional fields gracefully", () => {
    const auditLogs: AuditLog[] = [
      {
        id: 2,
        timestamp: "2024-01-02T15:30:00Z",
        action: "DELETE",
        entity_type: "Animal",
        // entity_id missing
        // actor_user_id missing
        // details missing
      },
    ];

    render(<AuditView auditLogs={auditLogs} />);

    // Expected fallback values
    expect(screen.getByText("Animal #-")).toBeInTheDocument();
    expect(screen.getByText("-")).toBeInTheDocument();
    expect(screen.getByText("{}")).toBeInTheDocument();
  });
});
