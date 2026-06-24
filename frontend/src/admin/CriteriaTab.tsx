// frontend/src/admin/CriteriaTab.tsx
import type { CriterionRead } from "./types";
import { CriterionForm, List, Panel } from "./components";

type Props = {
  criteria: CriterionRead[];
  type: "public" | "judge";
  competitionId: string;
  configurationLocked: boolean;
  onAdd: (form: HTMLFormElement) => Promise<void>;
  onToggleActive: (id: string, active: boolean) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  required: boolean;
  emptyMessage: string;
};

export function CriteriaTab({
  criteria,
  type,
  competitionId,
  configurationLocked,
  onAdd,
  onToggleActive,
  onDelete,
  required,
  emptyMessage,
}: Props) {
  const title = type === "public" ? "Criteri pubblico" : "Criteri giudici";

  return (
    <Panel title={title}>
      {!required ? (
        <p className="empty">{emptyMessage}</p>
      ) : (
        <>
          <CriterionForm onSubmit={onAdd} disabled={configurationLocked} />
          <List>
            {criteria.length === 0 && (
              <p className="empty">Nessun criterio aggiunto.</p>
            )}
            {criteria.map((criterion) => (
              <div className="row compact criterion-row" key={criterion.id}>
                <span>
                  <strong>{criterion.name}</strong>
                  <small>Scala: {criterion.min_score}-{criterion.max_score} · Peso: x{criterion.weight}</small>
                </span>
                <div className="button-strip" style={{ gap: "10px", alignItems: "center" }}>
                  <label className="checkline" style={{ margin: 0 }}>
                    <input
                      type="checkbox"
                      checked={criterion.active}
                      disabled={configurationLocked}
                      onChange={(e) => onToggleActive(criterion.id, e.target.checked)}
                    />
                    <span>Attivo</span>
                  </label>
                  <button
                    className="danger-button"
                    disabled={configurationLocked}
                    type="button"
                    onClick={() => onDelete(criterion.id)}
                  >
                    Elimina
                  </button>
                </div>
              </div>
            ))}
          </List>
        </>
      )}
    </Panel>
  );
}
