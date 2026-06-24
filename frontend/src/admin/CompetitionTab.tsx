// frontend/src/admin/CompetitionTab.tsx
import type { CompetitionRead, CompetitionStatus, VotingSessionRead } from "./types";
import {
  Form,
  List,
  Badge,
  Metric,
  formatPublicVoteMethod,
  formatAccessMethod,
} from "./components";

type Props = {
  competitions: CompetitionRead[];
  selectedCompetitionId: string;
  selectedEventId: string;
  configurationLocked: boolean;
  onSelect: (id: string) => void;
  onDelete: (comp: CompetitionRead) => void;
  onCreate: (form: HTMLFormElement) => Promise<void>;
  sessions: VotingSessionRead[];
};

const competitionStatusLabels: Record<CompetitionStatus, string> = {
  draft: "Bozza",
  ready: "Pronto",
  voting_open: "Voto Aperto",
  voting_closed: "Voto Chiuso",
  results_frozen: "Congelato",
  revealed: "Svelato",
};

export function CompetitionTab({
  competitions,
  selectedCompetitionId,
  selectedEventId,
  configurationLocked,
  onSelect,
  onDelete,
  onCreate,
  sessions,
}: Props) {
  const selectedCompetition = competitions.find((c) => c.id === selectedCompetitionId);
  const openSession = sessions.find((s) => s.status === "open");

  return (
    <div className="split">
      <div>
        <h2>Competizioni</h2>
        <Form
          submitLabel="Crea competizione"
          onSubmit={onCreate}
          disabled={!selectedEventId || configurationLocked}
        >
          {configurationLocked ? (
            <p className="lock-note">Evento live o chiuso: configurazione bloccata.</p>
          ) : null}
          <label className="field-stack">
            <span>Nome competizione</span>
            <input name="name" placeholder="Es. Miglior performance" required />
          </label>
          <div className="inline-grid">
            <label className="checkline">
              <input name="public_voting_enabled" type="checkbox" defaultChecked />
              Voto pubblico
            </label>
            <label className="checkline">
              <input name="judge_voting_enabled" type="checkbox" defaultChecked />
              Voto giudici
            </label>
            <label className="checkline">
              <input name="allow_vote_update" type="checkbox" />
              Aggiornamento voto
            </label>
          </div>
          <label className="field-stack">
            <span>Metodo voto pubblico</span>
            <select name="public_vote_method" defaultValue="single_choice">
              <option value="single_choice">Scelta singola</option>
              <option value="ranked_choice">Classifica</option>
              <option value="criteria_rating">Valutazione per criteri</option>
            </select>
          </label>
          <div className="inline-grid" style={{ gridTemplateColumns: "repeat(2, 1fr)" }}>
            <label className="field-stack">
              <span>Peso pubblico</span>
              <input name="public_weight" type="number" defaultValue="50" min="0" />
            </label>
            <label className="field-stack">
              <span>Peso giudici</span>
              <input name="judge_weight" type="number" defaultValue="50" min="0" />
            </label>
          </div>
          <div className="inline-grid" style={{ gridTemplateColumns: "repeat(2, 1fr)", marginTop: "8px" }}>
            <label className="field-stack">
              <span>Max voti per utente</span>
              <input name="max_votes_per_user" type="number" defaultValue="1" min="1" />
              <span className="form-hint" style={{ fontWeight: "normal" }}>
                Candidati selezionabili in una singola scheda di voto (es. per metodo classifica).
              </span>
            </label>
            <label className="field-stack">
              <span>Max votazioni per competizione</span>
              <input name="max_votes_per_competition" type="number" defaultValue="1" min="1" />
              <span className="form-hint" style={{ fontWeight: "normal" }}>
                Numero massimo di volte (round/sessioni) in cui lo stesso utente può votare per questa competizione.
              </span>
            </label>
          </div>
          <div className="inline-grid">
            <label className="field-stack">
              <span>Metodo accesso</span>
              <select name="access_method" defaultValue="public_link">
                <option value="public_link">Link pubblico</option>
                <option value="qr_pin">QR + PIN</option>
                <option value="private_link">Link privato</option>
              </select>
            </label>
            <label className="field-stack">
              <span>PIN se QR/PIN</span>
              <input name="access_pin" placeholder="PIN pubblico" />
            </label>
          </div>
        </Form>
        <List>
          {competitions.map((competition) => (
            <div
              className={
                competition.id === selectedCompetitionId ? "row active event-row" : "row event-row"
              }
              key={competition.id}
            >
              <button
                className="event-select"
                onClick={() => onSelect(competition.id)}
                type="button"
              >
                <span>{competition.name}</span>
                <Badge>{competitionStatusLabels[competition.status] || competition.status}</Badge>
              </button>
              <button
                className="danger-button"
                disabled={configurationLocked}
                type="button"
                onClick={() => onDelete(competition)}
              >
                Elimina
              </button>
            </div>
          ))}
        </List>
      </div>

      <div>
        <h2>{selectedCompetition ? selectedCompetition.name : "Dettaglio"}</h2>
        {selectedCompetition ? (
          <>
            {selectedCompetition.description ? (
              <p className="form-hint">{selectedCompetition.description}</p>
            ) : null}
            <div className="metrics">
              <Metric label="ID voto" value={selectedCompetition.id} />
              <Metric label="Stato" value={competitionStatusLabels[selectedCompetition.status] || selectedCompetition.status} />
              <Metric
                label="Metodo voto pubblico"
                value={formatPublicVoteMethod(selectedCompetition.public_vote_method)}
              />
              <Metric
                label="Accesso pubblico"
                value={formatAccessMethod(selectedCompetition.access_method)}
              />
              <Metric label="Peso pubblico" value={selectedCompetition.public_weight} />
              <Metric label="Peso giudici" value={selectedCompetition.judge_weight} />
              <Metric
                label="Voto pubblico"
                value={selectedCompetition.public_voting_enabled ? "attivo" : "disattivato"}
              />
              <Metric
                label="Voto giudici"
                value={selectedCompetition.judge_voting_enabled ? "attivo" : "disattivato"}
              />
              <Metric
                label="Max voti per utente"
                value={selectedCompetition.max_votes_per_user}
              />
              <Metric
                label="Max votazioni per competizione"
                value={selectedCompetition.max_votes_per_competition}
              />
              <Metric
                label="Aggiornamento voto"
                value={selectedCompetition.allow_vote_update ? "consentito" : "bloccato"}
              />
              <Metric label="Sessione" value={openSession ? "aperta" : "chiusa"} />
              <Metric label="Tipo" value={selectedCompetition.type || "non impostato"} />
            </div>
          </>
        ) : (
          <p className="empty">Seleziona o crea una competizione.</p>
        )}
      </div>
    </div>
  );
}
