// frontend/src/admin/VoterAccountsTab.tsx
import { FormEvent, useState } from "react";
import type {
  CompetitionRead,
  ParticipantRead,
  VoterAccountCreatedRead,
  VoterAccountRead,
  VoterCredentialNotice,
} from "./types";
import { api } from "./api";

type Props = {
  eventId: string;
  competitions: CompetitionRead[];
  participants: ParticipantRead[]; // tutti i partecipanti dell'evento, di tutte le competizioni
  voterAccounts: VoterAccountRead[];
  configurationLocked: boolean;
  onChanged: () => Promise<void>;
  onCredential: (notice: VoterCredentialNotice) => void;
};

function participantVoterAccountIds(participant: ParticipantRead): string[] {
  return participant.voter_account_ids.length
    ? participant.voter_account_ids
    : participant.voter_account_id
      ? [participant.voter_account_id]
      : [];
}

export function VoterAccountsTab({
  eventId,
  competitions,
  participants,
  voterAccounts,
  configurationLocked,
  onChanged,
  onCredential,
}: Props) {
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Errore inatteso");
    } finally {
      setBusy(false);
    }
  }

  async function createVoterAccount(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const data = new FormData(form);
    const display_name = (data.get("display_name") as string).trim();
    const notes = (data.get("notes") as string).trim() || null;
    if (!display_name) return;
    await run(async () => {
      const result = await api<VoterAccountCreatedRead>(
        `/api/events/${eventId}/voter-accounts`,
        {
          method: "POST",
          body: JSON.stringify({ display_name, notes }),
        }
      );
      onCredential({
        voterAccountId: result.voter_account.id,
        displayName: result.voter_account.display_name,
        accessCode: result.access_code,
      });
      form.reset();
      await onChanged();
    });
  }

  async function deleteVoterAccount(id: string) {
    await run(async () => {
      await api(`/api/voter-accounts/${id}`, { method: "DELETE" });
      await onChanged();
    });
  }

  async function regenerateCode(id: string, displayName: string) {
    await run(async () => {
      const result = await api<{ voter_account: VoterAccountRead; access_code: string }>(
        `/api/voter-accounts/${id}/regenerate-code`,
        { method: "POST" }
      );
      onCredential({
        voterAccountId: id,
        displayName,
        accessCode: result.access_code,
      });
      await onChanged();
    });
  }

  async function linkParticipant(voterAccountId: string, participantId: string) {
    await run(async () => {
      await api(
        `/api/voter-accounts/${voterAccountId}/link-participant`,
        {
          method: "POST",
          body: JSON.stringify({ participant_id: participantId }),
        }
      );
      await onChanged();
    });
  }

  async function unlinkParticipant(voterAccountId: string, participantId: string) {
    await run(async () => {
      await api(
        `/api/voter-accounts/${voterAccountId}/unlink-participant/${participantId}`,
        { method: "DELETE" }
      );
      await onChanged();
    });
  }

  return (
    <div className="voter-accounts-tab">
      <h2>Account votanti</h2>
      <p className="form-hint">
        Ogni account votante ha un codice di accesso personale. Se un votante è anche
        partecipante a una competizione, collegalo qui: il sistema bloccherà il voto su
        se stesso automaticamente.
      </p>

      {error && <p className="error-banner">{error}</p>}

      {!configurationLocked && (
        <form className="voter-create-form" onSubmit={createVoterAccount}>
          <fieldset disabled={busy}>
            <legend>Nuovo account votante</legend>
            <div className="inline-grid">
              <label className="field-stack">
                <span>Nome visualizzato</span>
                <input name="display_name" placeholder="Es. Mario Rossi" required />
              </label>
              <label className="field-stack">
                <span>Note (opzionale)</span>
                <input name="notes" placeholder="Note interne" />
              </label>
            </div>
            <button type="submit">Crea account</button>
          </fieldset>
        </form>
      )}

      {configurationLocked && (
        <p className="lock-note">Evento live: creazione nuovi account bloccata.</p>
      )}

      <div className="voter-list">
        {voterAccounts.length === 0 && (
          <p className="form-hint">Nessun account votante creato.</p>
        )}
        {voterAccounts.map((va) => {
          const linked = participants.filter((p) => participantVoterAccountIds(p).includes(va.id));
          const linkedCompetitionIds = new Set(linked.map((p) => p.competition_id));
          return (
            <div key={va.id} className="voter-row">
              <div className="voter-row-header">
                <strong>{va.display_name}</strong>
                {va.notes && <span className="voter-notes">{va.notes}</span>}
                <span className={`badge ${va.active ? "badge-success" : "badge-muted"}`}>
                  {va.active ? "Attivo" : "Disattivato"}
                </span>
              </div>
              <div className="voter-row-actions">
                <button
                  type="button"
                  className="secondary-button"
                  disabled={busy}
                  onClick={() => regenerateCode(va.id, va.display_name)}
                >
                  Rigenera codice
                </button>
                {!configurationLocked && (
                  <button
                    type="button"
                    className="danger-button"
                    disabled={busy}
                    onClick={() => deleteVoterAccount(va.id)}
                  >
                    Elimina
                  </button>
                )}
              </div>

              {/* Partecipanti collegati */}
              <div className="voter-links">
                <span className="voter-links-label">Collegato a:</span>
                {linked.length === 0 ? (
                  <span className="form-hint">nessun partecipante</span>
                ) : (
                  linked.map((p) => {
                    const compName = competitions.find((c) => c.id === p.competition_id)?.name ?? "Competizione sconosciuta";
                    return (
                      <span key={p.id} className="voter-link-chip">
                        {p.display_name} ({compName})
                        {!configurationLocked && (
                          <button
                            type="button"
                            className="chip-remove"
                            disabled={busy}
                            onClick={() => unlinkParticipant(va.id, p.id)}
                          >
                            ✕
                          </button>
                        )}
                      </span>
                    );
                  })
                )}
              </div>

              {/* Selezione partecipante da collegare */}
              {!configurationLocked && (
                <div className="voter-link-add">
                  <select
                    id={`link-select-${va.id}`}
                    defaultValue=""
                    onChange={(e) => {
                      const participantId = e.target.value;
                      if (participantId) {
                        void linkParticipant(va.id, participantId);
                        e.target.value = "";
                      }
                    }}
                    disabled={busy}
                  >
                    <option value="">— Collega partecipante —</option>
                    {competitions.map((comp) => {
                      const compParticipants = participants.filter(
                        (p) =>
                          p.competition_id === comp.id &&
                          !linkedCompetitionIds.has(comp.id) &&
                          !participantVoterAccountIds(p).includes(va.id)
                      );
                      if (compParticipants.length === 0) return null;
                      return (
                        <optgroup key={comp.id} label={comp.name}>
                          {compParticipants.map((p) => (
                            <option key={p.id} value={p.id}>
                              {p.display_name}
                            </option>
                          ))}
                        </optgroup>
                      );
                    })}
                  </select>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
