// frontend/src/admin/LiveTab.tsx
import type { CompetitionRead, EventRead, VotingSessionRead, CompetitionSetupStatus } from "./types";
import { Form, Panel, MiniTable } from "./components";

type Props = {
  competition: CompetitionRead | null;
  event: EventRead | null;
  sessions: VotingSessionRead[];
  setupStatus: CompetitionSetupStatus | null;
  canOpenVoting: boolean;
  isEventLive: boolean;
  setupReady: boolean;
  onGoLive: () => Promise<void>;
  onOpenVoting: (form: HTMLFormElement) => Promise<void>;
  onCloseVoting: () => Promise<void>;
};

const setupIssueMap: Record<string, string> = {
  missing_active_participants: "Servono almeno 2 partecipanti attivi",
  missing_voting_mode: "Abilita voto pubblico o voto giudici",
  missing_public_vote_method: "Configura il metodo di voto pubblico",
  invalid_public_weight: "Peso pubblico non valido",
  invalid_judge_weight: "Peso giudici non valido",
  missing_assigned_judges: "Mancano giudici attivi assegnati",
  missing_judge_criteria: "Mancano i criteri di voto per i giudici",
  missing_public_criteria: "Mancano i criteri di voto per il pubblico",
  event_not_live: "Evento non ancora live",
  missing_competitions: "Crea almeno una competizione",
};

export function LiveTab({
  competition,
  event,
  sessions,
  setupStatus,
  canOpenVoting,
  isEventLive,
  setupReady,
  onGoLive,
  onOpenVoting,
  onCloseVoting,
}: Props) {
  if (!competition) return <p className="empty">Seleziona una competizione.</p>;
  const openSession = sessions.find((session) => session.status === "open");

  return (
    <div className="grid">
      <Panel title="Votazione">
        {setupStatus && !setupStatus.is_ready && (
          <div className="setup-checklist">
            <p><strong>Configurazione richiesta:</strong></p>
            <ul>
              {setupStatus.issues.map((issue) => (
                <li key={issue}>{setupIssueMap[issue] || issue}</li>
              ))}
            </ul>
          </div>
        )}
        {setupStatus && setupStatus.is_ready && !isEventLive && (
          <div className="setup-success">
            <p>Setup completo. Porta evento live per abilitare voto e schermo.</p>
          </div>
        )}
        {setupStatus && setupStatus.is_ready && isEventLive && !openSession && (
          <div className="setup-success">
            <p>Configurazione completata. Votazione apribile.</p>
          </div>
        )}
        {!isEventLive ? (
          <div className="button-strip">
            <button
              type="button"
              disabled={!setupReady}
              onClick={onGoLive}
            >
              Porta evento live
            </button>
          </div>
        ) : null}
        <Form
          submitLabel="Apri votazione"
          onSubmit={onOpenVoting}
          disabled={!canOpenVoting || !!openSession}
        >
          <input name="label" placeholder="Round" defaultValue="Round live" />
        </Form>
        <div className="button-strip">
          <button
            type="button"
            disabled={!openSession}
            onClick={onCloseVoting}
          >
            Chiudi votazione
          </button>
        </div>
        <MiniTable
          rows={sessions.map((session) => [
            session.label ?? "Sessione",
            session.status,
            session.opened_at ? new Date(session.opened_at).toLocaleTimeString() : "-",
          ])}
        />
      </Panel>
    </div>
  );
}
