// frontend/src/admin/components.tsx
import { ReactNode, FormEvent } from "react";
import type { CriterionRead, JudgeRead, CompetitionRead, ScreenStateRead, AuditLogRead, PublicVoteMethod, ScreenMode } from "./types";

export function Form({
  children,
  submitLabel,
  onSubmit,
  disabled,
}: {
  children: ReactNode;
  submitLabel: string;
  onSubmit: (form: HTMLFormElement) => void;
  disabled?: boolean;
}) {
  return (
    <form
      className="form"
      onSubmit={(event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        if (disabled) return;
        onSubmit(event.currentTarget);
      }}
    >
      {children}
      <button type="submit" disabled={disabled}>{submitLabel}</button>
    </form>
  );
}

export function CriterionForm({
  onSubmit,
  disabled,
}: {
  onSubmit: (form: HTMLFormElement) => void;
  disabled?: boolean;
}) {
  return (
    <Form submitLabel="Aggiungi criterio" onSubmit={onSubmit} disabled={disabled}>
      <input name="name" placeholder="Nome criterio" required />
      <div className="inline-grid">
        <input name="min_score" type="number" defaultValue="1" />
        <input name="max_score" type="number" defaultValue="10" />
        <input name="weight" type="number" defaultValue="1" />
      </div>
    </Form>
  );
}

export function Panel({
  title,
  children,
  action,
  className,
}: {
  title: string;
  children: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <section className={className ? `panel ${className}` : "panel"}>
      <div className="panel-title">
        <h2>{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}

export function List({ children }: { children: ReactNode }) {
  return <div className="list">{children}</div>;
}

export function Badge({ children }: { children: ReactNode }) {
  return <span className="badge">{children}</span>;
}

export function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export function MiniTable({ rows }: { rows: string[][] }) {
  if (rows.length === 0) {
    return <p className="empty">Nessun dato.</p>;
  }
  return (
    <div className="mini-table">
      {rows.map((row, rowIndex) => (
        <div className="mini-row" key={`${row.join("-")}-${rowIndex}`}>
          {row.map((cell, cellIndex) => (
            <span key={`${cell}-${cellIndex}`}>{cell}</span>
          ))}
        </div>
      ))}
    </div>
  );
}

export function CriteriaList({ criteria }: { criteria: CriterionRead[] }) {
  return (
    <MiniTable
      rows={criteria.map((criterion) => [
        criterion.name,
        `${criterion.min_score}-${criterion.max_score}`,
        `x${criterion.weight}`,
      ])}
    />
  );
}

export function competitionNamesForJudge(judge: JudgeRead, competitions: CompetitionRead[]): string {
  return judge.assigned_competition_ids
    .map((competitionId) => competitions.find((competition) => competition.id === competitionId)?.name)
    .filter((name): name is string => Boolean(name))
    .join(", ");
}

export function screenModeLabel(mode: ScreenMode): string {
  const labels: Record<ScreenMode, string> = {
    idle: "Idle",
    show_qr: "QR code",
    voting_open: "Votazione aperta",
    countdown: "Countdown",
    show_results: "Risultati",
    reveal_ranking: "Reveal",
    show_podium: "Podio",
    show_final_winners: "Finale",
  };
  return labels[mode];
}

export function auditActionLabel(action: string): string {
  const labels: Record<string, string> = {
    admin_event_created: "Evento creato",
    admin_event_updated: "Evento aggiornato",
    admin_event_deleted: "Evento eliminato",
    admin_competition_created: "Competizione creata",
    admin_competition_updated: "Competizione aggiornata",
    admin_competition_deleted: "Competizione eliminata",
    admin_participant_created: "Partecipante creato",
    admin_participant_updated: "Partecipante aggiornato",
    admin_participant_deleted: "Partecipante eliminato",
    admin_public_criterion_created: "Criterio pubblico creato",
    admin_public_criterion_updated: "Criterio pubblico aggiornato",
    admin_public_criterion_deleted: "Criterio pubblico eliminato",
    admin_judge_criterion_created: "Criterio giudice creato",
    admin_judge_criterion_updated: "Criterio giudice aggiornato",
    admin_judge_criterion_deleted: "Criterio giudice eliminato",
    admin_judge_created: "Giudice creato",
    admin_judge_updated: "Giudice aggiornato",
    admin_judge_deleted: "Giudice eliminato",
    admin_judge_assigned: "Giudice assegnato",
    admin_judge_access_code_regenerated: "Codice giudice rigenerato",
    admin_judge_unassigned: "Giudice rimosso",
    admin_voting_session_opened: "Votazione aperta",
    admin_voting_session_closed: "Votazione chiusa",
    admin_results_frozen: "Risultati congelati",
    admin_screen_state_updated: "Schermo aggiornato",
    public_access_granted: "Accesso pubblico",
    public_vote_submitted: "Voto pubblico",
    judge_access_granted: "Accesso giudice",
    judge_vote_submitted: "Voto giudice",
  };
  return labels[action] ?? action.replace(/_/g, " ");
}

export function auditDetailsText(details: Record<string, unknown>): string {
  const entries = Object.entries(details).filter(
    ([, value]) => value !== null && value !== undefined && value !== ""
  );
  if (!entries.length) {
    return "Nessun dettaglio";
  }
  return entries
    .map(([key, value]) => {
      if (Array.isArray(value)) {
        return `${key}: ${value.join(", ")}`;
      }
      if (typeof value === "object") {
        return `${key}: ${JSON.stringify(value)}`;
      }
      return `${key}: ${String(value)}`;
    })
    .join(" · ");
}

export function auditLogMatchesQuery(log: AuditLogRead, query: string): boolean {
  const normalizedQuery = query.trim().toLowerCase();
  if (!normalizedQuery) {
    return true;
  }
  const searchableText = [
    auditActionLabel(log.action),
    log.action,
    log.actor_type,
    log.actor_label,
    log.entity_type,
    log.entity_id,
    log.competition_id,
    auditDetailsText(log.details_json),
    new Date(log.created_at).toLocaleString(),
  ]
    .filter((value): value is string => Boolean(value))
    .join(" ")
    .toLowerCase();

  return searchableText.includes(normalizedQuery);
}

export function uniqueStringValues(values: string[]): string[] {
  return Array.from(new Set(values)).sort((first, second) => first.localeCompare(second));
}

export function formatPublicVoteMethod(method: PublicVoteMethod): string {
  const labels: Record<PublicVoteMethod, string> = {
    single_choice: "scelta singola",
    ranked_choice: "classifica",
    criteria_rating: "valutazione per criteri",
  };
  return labels[method];
}

export function textPayload(screenState: ScreenStateRead | null, key: string): string {
  const value = screenState?.payload_json[key];
  return typeof value === "string" ? value : "";
}

export function numberPayload(screenState: ScreenStateRead | null, key: string, fallback: number): number {
  const value = screenState?.payload_json[key];
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

export function textValue(data: FormData, key: string): string {
  return String(data.get(key) ?? "").trim();
}

export function numberValue(data: FormData, key: string, fallback: number): number {
  const value = Number(data.get(key));
  return Number.isFinite(value) ? value : fallback;
}

export function slugValue(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
}
