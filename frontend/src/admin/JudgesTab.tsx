// frontend/src/admin/JudgesTab.tsx
import type { JudgeRead, CompetitionRead, JudgeCredentialNotice } from "./types";
import { Form, List, Panel, Metric, competitionNamesForJudge } from "./components";

type Props = {
  judges: JudgeRead[];
  competitions: CompetitionRead[];
  eventId: string;
  configurationLocked: boolean;
  onAdd: (form: HTMLFormElement) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  onToggleCompetition: (judgeId: string, competitionId: string, isAssigned: boolean) => Promise<void>;
  onRegenerateCode: (judgeId: string) => Promise<void>;
  judgeCredentialNotice: JudgeCredentialNotice | null;
};

export function JudgesTab({
  judges,
  competitions,
  eventId,
  configurationLocked,
  onAdd,
  onDelete,
  onToggleCompetition,
  onRegenerateCode,
  judgeCredentialNotice,
}: Props) {
  return (
    <Panel title="Giudici">
      <Form
        submitLabel="Crea giudice"
        onSubmit={onAdd}
        disabled={configurationLocked}
      >
        <input name="display_name" placeholder="Nome giudice" required />
        <input name="access_code" placeholder="Codice accesso" required />
        <p className="form-hint">L'ID tecnico del giudice viene mostrato dopo il salvataggio.</p>
      </Form>
      {judgeCredentialNotice ? (
        <div className="credential-notice">
          <strong>Credenziali da consegnare</strong>
          <div className="credential-grid">
            <Metric label="Giudice" value={judgeCredentialNotice.displayName} />
            <Metric label="ID tecnico" value={judgeCredentialNotice.judgeId} />
            <Metric label="Codice accesso" value={judgeCredentialNotice.accessCode} />
            <Metric label="Link di login" value={`${window.location.origin}/judge`} />
          </div>
        </div>
      ) : null}
      <List>
        {judges.length === 0 && (
          <p className="empty">Nessun giudice aggiunto.</p>
        )}
        {judges.map((judge) => (
          <div className="row compact judge-row" key={judge.id}>
            <span>
              <strong>{judge.display_name}</strong>
              <small>ID tecnico: {judge.id}</small>
              <small style={{ marginTop: "4px" }}>
                Competizioni:{" "}
                {competitionNamesForJudge(judge, competitions) || "nessuna"}
              </small>
            </span>
            <div className="judge-competition-list">
              {competitions.length ? (
                competitions.map((competition) => {
                  const isAssigned = judge.assigned_competition_ids.includes(competition.id);
                  return (
                    <label
                      className={
                        !competition.judge_voting_enabled
                          ? "assignment-chip disabled-chip"
                          : isAssigned
                            ? "assignment-chip selected"
                            : "assignment-chip"
                      }
                      title={
                        !competition.judge_voting_enabled
                          ? "Il voto dei giudici è disabilitato per questa competizione"
                          : undefined
                      }
                      key={competition.id}
                    >
                      <input
                        checked={isAssigned}
                        type="checkbox"
                        disabled={configurationLocked || !competition.judge_voting_enabled}
                        onChange={() =>
                          onToggleCompetition(judge.id, competition.id, isAssigned)
                        }
                      />
                      <span>
                        {competition.name}
                        {!competition.judge_voting_enabled && " (no voto giudici)"}
                      </span>
                    </label>
                  );
                })
              ) : (
                <small>Nessuna competizione.</small>
              )}
            </div>
            <div className="judge-actions">
              <button
                className="secondary-button"
                type="button"
                onClick={() => onRegenerateCode(judge.id)}
              >
                Rigenera codice
              </button>
              <button
                className="danger-button"
                disabled={configurationLocked}
                type="button"
                onClick={() => onDelete(judge.id)}
              >
                Elimina
              </button>
            </div>
          </div>
        ))}
      </List>
    </Panel>
  );
}
