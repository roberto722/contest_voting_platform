// frontend/src/admin/api.ts

export const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
export const websocketBaseUrl = apiBaseUrl.replace(/^http/, "ws");

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

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: response.statusText }));
    const issueMessages = Array.isArray(payload.issues)
      ? payload.issues.map((issue: string) => setupIssueMap[issue] ?? issue)
      : [];
    const backendMessages = Array.isArray(payload.messages) ? payload.messages : [];
    const details = [...issueMessages, ...backendMessages].filter(Boolean);
    throw new Error(
      details.length
        ? `${payload.detail ?? response.statusText}: ${details.join("; ")}`
        : payload.detail ?? response.statusText
    );
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}
