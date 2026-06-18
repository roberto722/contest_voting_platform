const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export default function App() {
  return (
    <main className="app-shell">
      <section className="intro">
        <p className="eyebrow">Contest Voting Platform</p>
        <h1>Console eventi live</h1>
        <p>
          Base frontend pronta. Le prossime milestone aggiungeranno admin, voto pubblico,
          giudici e schermo pubblico.
        </p>
        <a href={`${apiBaseUrl}/health`}>Verifica backend</a>
      </section>
    </main>
  );
}
