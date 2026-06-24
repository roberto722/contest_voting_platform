// frontend/src/admin/ResultsTab.tsx
import type { ResultsRead, CompetitionRead } from "./types";
import { Panel } from "./components";

type Props = {
  results: ResultsRead | null;
  competition: CompetitionRead | null;
  onFreeze: () => Promise<void>;
  onRefresh: () => Promise<void>;
};

export function ResultsTab({
  results,
  competition,
  onFreeze,
  onRefresh,
}: Props) {
  if (!competition) return <p className="empty">Seleziona una competizione.</p>;

  return (
    <Panel title="Risultati">
      <div className="button-strip" style={{ marginBottom: "16px" }}>
        <button type="button" onClick={onRefresh}>
          Aggiorna risultati
        </button>
        <button type="button" onClick={onFreeze}>
          Congela risultati (Freeze)
        </button>
      </div>
      {results && results.results.length > 0 ? (
        <ol className="ranking">
          {results.results.map((result) => (
            <li key={result.participant_id}>
              <strong>
                {result.rank}. {result.display_name}
              </strong>
              <span>{result.final_score.toFixed(2)}</span>
              <small>
                Pub {result.public_score.normalized_score.toFixed(1)} / Giu{" "}
                {result.judge_score.normalized_score.toFixed(1)}
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
