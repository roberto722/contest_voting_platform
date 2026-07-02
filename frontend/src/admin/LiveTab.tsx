import { Form, Metric, Panel } from "./components";
import type { CompetitionRead, CompetitionSetupStatus, EventRead, VotingSessionRead } from "./types";

type LiveTabProps = {
  event: EventRead | null;
  competition: CompetitionRead;
  sessions: VotingSessionRead[];
  setupStatus: CompetitionSetupStatus | null;
  canOpenVoting?: boolean;
  isEventLive: boolean;
  setupReady: boolean;
  onGoLive: () => Promise<void>;
  onOpenVoting: (form: HTMLFormElement, channels?: string[]) => Promise<void>;
  onCloseVoting: (channels?: string[]) => Promise<void>;
};

const setupIssueMap: Record<string, string> = {
  missing_active_participants: "Mancano partecipanti attivi",
  missing_voting_mode: "Abilita voto pubblico o giudici",
  invalid_public_weight: "Peso pubblico non valido",
  missing_public_vote_method: "Configura il metodo pubblico",
  missing_public_criteria: "Mancano criteri pubblici",
  invalid_judge_weight: "Peso giudici non valido",
  missing_judge_criteria: "Mancano criteri giudici",
  missing_assigned_judges: "Mancano giudici assegnati",
  event_not_live: "Evento non live",
  competition_results_final: "Risultati finali",
};

export function LiveTab({
  event,
  competition,
  sessions,
  setupStatus,
  canOpenVoting: canOpenVotingProp,
  isEventLive,
  setupReady,
  onGoLive,
  onOpenVoting,
  onCloseVoting,
}: LiveTabProps) {
  const openSession = sessions.find((session) => session.status === "open") ?? null;
  const canOpenVoting = canOpenVotingProp ?? Boolean(setupStatus?.can_open_voting);
  const publicEnabled = competition.public_voting_enabled;
  const judgeEnabled = competition.judge_voting_enabled;
  const publicOpen = Boolean(openSession?.public_voting_open);
  const judgeOpen = Boolean(openSession?.judge_voting_open);
  const canOpenPublic = canOpenVoting && publicEnabled && !publicOpen;
  const canOpenJudge = canOpenVoting && judgeEnabled && !judgeOpen;
  const canClosePublic = publicOpen;
  const canCloseJudge = judgeOpen;

  return (
    <div className="stack">
      <Panel title="Live">
        <div className="metrics">
          <Metric label="Evento" value={event?.status ?? "draft"} />
          <Metric label="Setup" value={setupReady ? "Pronto" : "Incompleto"} />
          <Metric label="Pubblico" value={publicOpen ? "Aperto" : "Chiuso"} />
          <Metric label="Giudici" value={judgeOpen ? "Aperto" : "Chiuso"} />
        </div>

        {!isEventLive ? (
          <button type="button" disabled={!setupStatus?.is_ready} onClick={onGoLive}>
            Porta evento live
          </button>
        ) : null}

        {setupStatus?.issues.length ? (
          <ul className="checklist">
            {setupStatus.issues.map((issue) => (
              <li key={issue}>{setupIssueMap[issue] ?? issue}</li>
            ))}
          </ul>
        ) : null}

        <Form submitLabel="Apri entrambi" onSubmit={(form) => onOpenVoting(form)}>
          <input name="label" placeholder="Etichetta sessione" defaultValue="Round live" />
          <div className="button-strip">
            <button type="submit" disabled={!canOpenVoting}>
              Apri entrambi
            </button>
            <button
              type="button"
              disabled={!canOpenPublic}
              onClick={(event) => onOpenVoting(event.currentTarget.form!, ["public"])}
            >
              Apri pubblico
            </button>
            <button
              type="button"
              disabled={!canOpenJudge}
              onClick={(event) => onOpenVoting(event.currentTarget.form!, ["judge"])}
            >
              Apri giudici
            </button>
          </div>
        </Form>

        <div className="button-strip">
          <button type="button" disabled={!openSession} onClick={() => onCloseVoting()}>
            Chiudi entrambi
          </button>
          <button type="button" disabled={!canClosePublic} onClick={() => onCloseVoting(["public"])}>
            Chiudi pubblico
          </button>
          <button type="button" disabled={!canCloseJudge} onClick={() => onCloseVoting(["judge"])}>
            Chiudi giudici
          </button>
        </div>
      </Panel>
    </div>
  );
}
