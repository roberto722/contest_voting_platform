// frontend/src/admin/ResultsTab.tsx
import type { ResultsRead, CompetitionRead } from "./types";
import { Panel } from "./components";

type Props = {
  results: ResultsRead | null;
  competition: CompetitionRead | null;
  onRefresh: () => Promise<void>;
};

export function ResultsTab({
  results,
  competition,
  onRefresh,
}: Props) {
  if (!competition) return <p className="empty">Seleziona una competizione.</p>;

  return (
    <Panel title="Risultati">
      <div className="button-strip" style={{ marginBottom: "16px" }}>
        <button type="button" onClick={onRefresh}>
          Aggiorna risultati
        </button>
      </div>
      {results && results.results.length > 0 ? (
        <ol className="ranking">
          {results.results.map((result) => (
            <li key={result.participant_id}>
              <strong>
                {result.rank}. {result.display_name}
              </strong>
              <span>Finale {result.final_score.toFixed(2)}</span>
              <small>
                Pubblico {result.public_score.toFixed(2)} / Giudici{" "}
                {result.judge_score.toFixed(2)} / Voti pubblico{" "}
                {result.public_votes} / Giudici completati{" "}
                {result.judge_votes_count}
              </small>
            </li>
          ))}
        </ol>
      ) : (
        <p className="empty">Nessun risultato disponibile.</p>
      )}
    </Panel>
  );
}
