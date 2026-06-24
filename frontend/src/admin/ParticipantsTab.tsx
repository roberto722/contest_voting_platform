// frontend/src/admin/ParticipantsTab.tsx
import type { ParticipantRead, VoterAccountRead } from "./types";
import { Form, List, Panel } from "./components";

type Props = {
  participants: ParticipantRead[];
  competitionId: string;
  configurationLocked: boolean;
  onAdd: (form: HTMLFormElement) => Promise<void>;
  onToggleActive: (id: string, active: boolean) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  voterAccounts: VoterAccountRead[];
};

export function ParticipantsTab({
  participants,
  competitionId,
  configurationLocked,
  onAdd,
  onToggleActive,
  onDelete,
  voterAccounts,
}: Props) {
  return (
    <Panel title="Partecipanti">
      <Form submitLabel="Aggiungi" onSubmit={onAdd} disabled={configurationLocked}>
        <input name="display_name" placeholder="Nome pubblico" required />
        <input name="order_index" type="number" placeholder="Ordine" defaultValue={participants.length} />
      </Form>
      <List>
        {participants.length === 0 && (
          <p className="empty">Nessun partecipante aggiunto.</p>
        )}
        {participants.map((participant) => {
          const linkedAccount = voterAccounts.find(
            (va) => va.id === participant.voter_account_id
          );

          return (
            <div className="row compact participant-row" key={participant.id}>
              <span>
                <strong>{participant.display_name}</strong>
                <small>Ordine: #{participant.order_index}</small>
                <div style={{ marginTop: "4px" }}>
                  <span className="voter-links-label" style={{ fontSize: "0.75rem", marginRight: "6px" }}>Votante collegato:</span>
                  {linkedAccount ? (
                    <span className="voter-link-chip" style={{ fontSize: "0.75rem", padding: "1px 6px" }}>{linkedAccount.display_name}</span>
                  ) : (
                    <span className="form-hint" style={{ display: "inline", fontSize: "0.75rem" }}>nessun account votante</span>
                  )}
                </div>
              </span>
              <div className="button-strip" style={{ gap: "10px", alignItems: "center" }}>
                <label className="checkline" style={{ margin: 0 }}>
                  <input
                    type="checkbox"
                    checked={participant.active}
                    disabled={configurationLocked}
                    onChange={(e) => onToggleActive(participant.id, e.target.checked)}
                  />
                  <span>Attivo</span>
                </label>
                <button
                  className="danger-button"
                  disabled={configurationLocked}
                  type="button"
                  onClick={() => onDelete(participant.id)}
                >
                  Elimina
                </button>
              </div>
            </div>
          );
        })}
      </List>
    </Panel>
  );
}
