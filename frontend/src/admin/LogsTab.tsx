// frontend/src/admin/LogsTab.tsx
import type { AuditLogRead, AuditFilters } from "./types";
import {
  Panel,
  List,
  Badge,
  auditActionLabel,
  auditDetailsText,
  auditLogMatchesQuery,
  uniqueStringValues,
} from "./components";

type Props = {
  auditLogs: AuditLogRead[];
  filters: AuditFilters;
  onFiltersChange: (filters: AuditFilters | ((current: AuditFilters) => AuditFilters)) => void;
};

export function LogsTab({ auditLogs, filters, onFiltersChange }: Props) {
  const auditActorTypes = uniqueStringValues(auditLogs.map((log) => log.actor_type));
  const auditEntityTypes = uniqueStringValues(auditLogs.map((log) => log.entity_type));
  const auditActions = uniqueStringValues(auditLogs.map((log) => log.action));

  const filteredAuditLogs = auditLogs.filter((log) => {
    if (filters.actorType !== "all" && log.actor_type !== filters.actorType) return false;
    if (filters.entityType !== "all" && log.entity_type !== filters.entityType) return false;
    if (filters.action !== "all" && log.action !== filters.action) return false;
    return auditLogMatchesQuery(log, filters.query);
  });

  const auditPage = filters.page;
  const auditPageCount = Math.max(1, Math.ceil(filteredAuditLogs.length / filters.pageSize));
  const pagedAuditLogs = filteredAuditLogs.slice(
    (auditPage - 1) * filters.pageSize,
    auditPage * filters.pageSize
  );

  return (
    <Panel title="Log attività">
      <div className="audit-controls">
        <input
          aria-label="Cerca log"
          placeholder="Cerca nei log"
          value={filters.query}
          onChange={(event) =>
            onFiltersChange((current) => ({
              ...current,
              query: event.target.value,
              page: 1,
            }))
          }
        />
        <select
          aria-label="Filtra attore"
          value={filters.actorType}
          onChange={(event) =>
            onFiltersChange((current) => ({
              ...current,
              actorType: event.target.value,
              page: 1,
            }))
          }
        >
          <option value="all">Tutti attori</option>
          {auditActorTypes.map((actorType) => (
            <option key={actorType} value={actorType}>
              {actorType}
            </option>
          ))}
        </select>
        <select
          aria-label="Filtra entità"
          value={filters.entityType}
          onChange={(event) =>
            onFiltersChange((current) => ({
              ...current,
              entityType: event.target.value,
              page: 1,
            }))
          }
        >
          <option value="all">Tutte entità</option>
          {auditEntityTypes.map((entityType) => (
            <option key={entityType} value={entityType}>
              {entityType}
            </option>
          ))}
        </select>
        <select
          aria-label="Filtra azione"
          value={filters.action}
          onChange={(event) =>
            onFiltersChange((current) => ({
              ...current,
              action: event.target.value,
              page: 1,
            }))
          }
        >
          <option value="all">Tutte azioni</option>
          {auditActions.map((action) => (
            <option key={action} value={action}>
              {auditActionLabel(action)}
            </option>
          ))}
        </select>
        <select
          aria-label="Log per pagina"
          value={filters.pageSize}
          onChange={(event) =>
            onFiltersChange((current) => ({
              ...current,
              pageSize: Number(event.target.value),
              page: 1,
            }))
          }
        >
          {[20, 40, 100, 200].map((pageSize) => (
            <option key={pageSize} value={pageSize}>
              {pageSize} per pagina
            </option>
          ))}
        </select>
      </div>
      <div className="audit-summary">
        <span>
          {filteredAuditLogs.length} log filtrati su {auditLogs.length}
        </span>
        <div className="audit-pagination">
          <button
            className="secondary-button"
            disabled={auditPage <= 1}
            type="button"
            onClick={() =>
              onFiltersChange((current) => ({
                ...current,
                page: Math.max(1, auditPage - 1),
              }))
            }
          >
            Precedente
          </button>
          <span>
            {auditPage}/{auditPageCount}
          </span>
          <button
            className="secondary-button"
            disabled={auditPage >= auditPageCount}
            type="button"
            onClick={() =>
              onFiltersChange((current) => ({
                ...current,
                page: Math.min(auditPageCount, auditPage + 1),
              }))
            }
          >
            Successiva
          </button>
        </div>
      </div>
      <List>
        {pagedAuditLogs.length > 0 ? (
          pagedAuditLogs.map((log) => (
            <div className="row compact audit-row" key={log.id}>
              <span>
                <strong>{auditActionLabel(log.action)}</strong>
                <small>{new Date(log.created_at).toLocaleString()}</small>
                <small>
                  {log.actor_label ?? log.actor_type} · {log.entity_type}
                  {log.entity_id ? ` · ${log.entity_id}` : ""}
                </small>
                <small>{auditDetailsText(log.details_json)}</small>
              </span>
              <Badge>{log.actor_type}</Badge>
            </div>
          ))
        ) : (
          <p className="empty">Nessun log per i filtri selezionati.</p>
        )}
      </List>
    </Panel>
  );
}
