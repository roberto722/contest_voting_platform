// frontend/src/admin/ReviewTab.tsx
import type { CompetitionSetupStatus, CompetitionRead, EventRead, EventStatus, CompetitionStatus } from "./types";
import { Panel, Metric } from "./components";

type Props = {
  setupStatus: CompetitionSetupStatus | null;
  competition: CompetitionRead | null;
  selectedEvent: EventRead | null;
  isUnpopulated: boolean;
  setupReady: boolean;
  canOpenVoting: boolean;
  onPopolaFakeData: () => void;
};

const eventStatusLabels: Record<EventStatus, string> = {
  draft: "draft",
  live: "live",
  closed: "chiuso",
  archived: "archiviato",
};

const competitionStatusLabels: Record<CompetitionStatus, string> = {
  draft: "Bozza",
  ready: "Pronto",
  voting_open: "Voto Aperto",
  voting_closed: "Voto Chiuso",
  results_frozen: "Congelato",
  revealed: "Svelato",
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
  missing_access_pin: "Manca il PIN per accesso QR/PIN",
  event_not_live: "Evento non ancora live",
  competition_results_final: "Risultati già finali",
  missing_competitions: "Crea almeno una competizione",
};

export function ReviewTab({
  setupStatus,
  competition,
  selectedEvent,
  isUnpopulated,
  setupReady,
  canOpenVoting,
  onPopolaFakeData,
}: Props) {
  if (!competition) return <p className="empty">Seleziona una competizione.</p>;

  return (
    <Panel title="Review configurazione">
      <div className="setup-checklist">
        <p><strong>Checklist setup</strong></p>
        <ul>
          {(setupStatus?.checks ?? []).map((check) => (
            <li className={check.completed ? "done" : ""} key={check.step}>
              <span>{check.completed ? "OK" : "NO"}</span> {check.message}
            </li>
          ))}
        </ul>
      </div>
      <div className="metrics">
        <Metric label="Setup" value={setupReady ? "completo" : "incompleto"} />
        <Metric label="Apertura voto" value={canOpenVoting ? "possibile" : "bloccata"} />
        <Metric label="Evento" value={selectedEvent ? eventStatusLabels[selectedEvent.status] : "-"} />
        <Metric label="Competizione" value={competitionStatusLabels[competition.status] || competition.status} />
      </div>
      {setupStatus?.issues.length ? (
        <ul className="issue-list">
          {setupStatus.issues.map((issue) => (
            <li key={issue}>{setupIssueMap[issue] || issue}</li>
          ))}
        </ul>
      ) : null}
      {isUnpopulated && selectedEvent?.status === "draft" && (
        <div
          className="setup-success"
          style={{
            marginTop: "1.2rem",
            backgroundColor: "rgba(22, 38, 56, 0.05)",
            borderColor: "#c7d0d9",
            color: "#162638",
          }}
        >
          <p style={{ marginBottom: "10px", fontWeight: "normal" }}>
            La competizione è vuota. Puoi popolarla rapidamente con partecipanti, criteri e giudici di prova coerenti con la configurazione scelta.
          </p>
          <button type="button" onClick={onPopolaFakeData}>
            Popola con Dati Fake
          </button>
        </div>
      )}
    </Panel>
  );
}
