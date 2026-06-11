import { Panel } from "../components/Panel";
import type { AuditLog } from "../types";

export function AuditView({ auditLogs }: { auditLogs: AuditLog[] }) {
  return (
    <Panel title="Audit-Logs" icon="file">
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Zeitpunkt</th>
              <th>Aktion</th>
              <th>Entitaet</th>
              <th>Nutzer-ID</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {auditLogs.map((entry) => (
              <tr key={entry.id}>
                <td>{new Date(entry.timestamp).toLocaleString("de-DE")}</td>
                <td>{entry.action}</td>
                <td>
                  {entry.entity_type} #{entry.entity_id ?? "-"}
                </td>
                <td>{entry.actor_user_id ?? "-"}</td>
                <td>
                  <code>{entry.details ? JSON.stringify(entry.details) : "{}"}</code>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}
