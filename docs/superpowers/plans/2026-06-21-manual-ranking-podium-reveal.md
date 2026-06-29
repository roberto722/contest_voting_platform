# Manual Ranking and Podium Reveal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add manual, reversible last-to-first reveal controls for the full ranking and final podium.

**Architecture:** Keep `ScreenState.payload_json.reveal_upto` as the persisted reveal counter and use the existing screen-state PUT endpoint and WebSocket broadcast. Put sequence calculations in a pure `frontend/src/screen/reveal.ts` module, then consume them from the admin controls and public screen in `App.tsx`.

**Tech Stack:** React 18, TypeScript, Vite, Node test runner, FastAPI screen-state API/WebSocket

---

### Task 1: Pure reveal sequence

**Files:**
- Create: `frontend/src/screen/reveal.ts`
- Create: `frontend/tests/reveal.test.ts`

- [ ] **Step 1: Write the failing sequence tests**

Create `frontend/tests/reveal.test.ts`:

```ts
import assert from "node:assert/strict";
import test from "node:test";

import {
  clampRevealCount,
  nextRevealRank,
  revealTotal,
  visibleRevealedResults,
} from "../src/screen/reveal.ts";

const ranking = ["primo", "secondo", "terzo", "quarto"];

test("rivela la classifica cumulativamente dall'ultima posizione alla prima", () => {
  assert.deepEqual(visibleRevealedResults(ranking, "reveal_ranking", 0), []);
  assert.deepEqual(visibleRevealedResults(ranking, "reveal_ranking", 1), ["quarto"]);
  assert.deepEqual(visibleRevealedResults(ranking, "reveal_ranking", 2), ["terzo", "quarto"]);
  assert.deepEqual(visibleRevealedResults(ranking, "reveal_ranking", 4), ranking);
});

test("rivela il podio nel flusso terzo, secondo, primo", () => {
  assert.deepEqual(visibleRevealedResults(ranking, "show_podium", 0), []);
  assert.deepEqual(visibleRevealedResults(ranking, "show_podium", 1), ["terzo"]);
  assert.deepEqual(visibleRevealedResults(ranking, "show_podium", 2), ["secondo", "terzo"]);
  assert.deepEqual(visibleRevealedResults(ranking, "show_podium", 3), ["primo", "secondo", "terzo"]);
  assert.deepEqual(visibleRevealedResults(["primo", "secondo"], "show_final_winners", 1), ["secondo"]);
});

test("limita contatori invalidi e calcola la prossima posizione", () => {
  assert.equal(revealTotal("reveal_ranking", 7), 7);
  assert.equal(revealTotal("show_podium", 7), 3);
  assert.equal(revealTotal("show_final_winners", 2), 2);
  assert.equal(clampRevealCount(-3, 4), 0);
  assert.equal(clampRevealCount(8, 4), 4);
  assert.equal(nextRevealRank(4, 0), 4);
  assert.equal(nextRevealRank(4, 3), 1);
  assert.equal(nextRevealRank(4, 4), null);
});
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```powershell
cd frontend
node --test tests/reveal.test.ts
```

Expected: FAIL with `ERR_MODULE_NOT_FOUND` for `src/screen/reveal.ts`.

- [ ] **Step 3: Implement the minimal pure helpers**

Create `frontend/src/screen/reveal.ts`:

```ts
export type RevealMode = "reveal_ranking" | "show_podium" | "show_final_winners";

export function revealTotal(mode: RevealMode, resultCount: number): number {
  const safeResultCount = Math.max(0, Math.trunc(resultCount));
  return mode === "reveal_ranking" ? safeResultCount : Math.min(3, safeResultCount);
}

export function clampRevealCount(value: number, total: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.min(Math.max(0, Math.trunc(value)), Math.max(0, total));
}

export function nextRevealRank(total: number, visibleCount: number): number | null {
  const safeTotal = Math.max(0, Math.trunc(total));
  const safeVisibleCount = clampRevealCount(visibleCount, safeTotal);
  return safeVisibleCount < safeTotal ? safeTotal - safeVisibleCount : null;
}

export function visibleRevealedResults<T>(
  orderedResults: readonly T[],
  mode: RevealMode,
  visibleCount: number,
): T[] {
  const total = revealTotal(mode, orderedResults.length);
  const count = clampRevealCount(visibleCount, total);
  return orderedResults.slice(total - count, total);
}
```

- [ ] **Step 4: Run reveal and existing podium tests and verify GREEN**

Run:

```powershell
cd frontend
node --test tests/reveal.test.ts tests/podium.test.ts
```

Expected: all tests PASS.

- [ ] **Step 5: Commit the pure reveal behavior**

```powershell
git add frontend/src/screen/reveal.ts frontend/tests/reveal.test.ts
git commit -m "feat: define manual reveal sequence"
```

### Task 2: Admin reveal controls

**Files:**
- Modify: `frontend/src/App.tsx:1-8`
- Modify: `frontend/src/App.tsx:386-817`
- Modify: `frontend/src/App.tsx:1380-1470`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Add a failing test for counter transitions**

Extend `frontend/tests/reveal.test.ts` imports with `previousRevealCount` and add:

```ts
test("torna indietro e azzera senza superare i limiti", () => {
  assert.equal(previousRevealCount(3, 5), 2);
  assert.equal(previousRevealCount(0, 5), 0);
  assert.equal(previousRevealCount(9, 5), 4);
  assert.equal(previousRevealCount(-1, 5), 0);
});
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```powershell
cd frontend
node --test tests/reveal.test.ts
```

Expected: FAIL because `previousRevealCount` is not exported.

- [ ] **Step 3: Implement the minimal counter transition**

Add to `frontend/src/screen/reveal.ts`:

```ts
export function previousRevealCount(value: number, total: number): number {
  return Math.max(0, clampRevealCount(value, total) - 1);
}
```

Run `node --test tests/reveal.test.ts` and expect PASS.

- [ ] **Step 4: Import helpers and track update state**

In `frontend/src/App.tsx`, import:

```ts
import {
  clampRevealCount,
  nextRevealRank,
  previousRevealCount,
  revealTotal,
  type RevealMode,
} from "./screen/reveal";
```

Inside `App`, add:

```ts
const [isRevealUpdating, setIsRevealUpdating] = useState(false);
```

After `selectedCompetition`, derive:

```ts
const revealMode =
  state.screenState?.mode === "reveal_ranking" ||
  state.screenState?.mode === "show_podium" ||
  state.screenState?.mode === "show_final_winners"
    ? (state.screenState.mode as RevealMode)
    : null;
const revealMaximum = revealMode
  ? revealTotal(revealMode, state.results?.results.length ?? 0)
  : 0;
const revealedCount = clampRevealCount(
  numberPayload(state.screenState, "reveal_upto", 0),
  revealMaximum,
);
const upcomingRank = nextRevealRank(revealMaximum, revealedCount);
```

- [ ] **Step 5: Add the dedicated persisted reveal action**

Place this next to `updateScreenState`:

```ts
async function updateRevealCount(nextCount: number) {
  if (!selectedEventId || !state.screenState || !revealMode) return;
  setIsRevealUpdating(true);
  try {
    const screenState = await api<ScreenStateRead>(
      `/api/events/${selectedEventId}/screen-state`,
      {
        method: "PUT",
        body: JSON.stringify({
          competition_id: selectedCompetitionId || null,
          mode: state.screenState.mode,
          payload_json: {
            ...state.screenState.payload_json,
            reveal_upto: clampRevealCount(nextCount, revealMaximum),
          },
        }),
      },
    );
    setState((current) => ({ ...current, screenState }));
  } finally {
    setIsRevealUpdating(false);
  }
}
```

- [ ] **Step 6: Replace the DOM-query reveal control**

Replace the existing `reveal-controls` block with:

```tsx
{revealMode ? (
  <div className="reveal-controls">
    <p>
      Rivelate {revealedCount} di {revealMaximum}
      {upcomingRank ? ` — prossima: posizione ${upcomingRank}` : " — sequenza completata"}
    </p>
    <div className="button-strip">
      <button
        className="secondary-button"
        type="button"
        disabled={isRevealUpdating || revealedCount === 0}
        onClick={() => run(() => updateRevealCount(0), "Rivelazione azzerata")}
      >
        Azzera
      </button>
      <button
        className="secondary-button"
        type="button"
        disabled={isRevealUpdating || revealedCount === 0}
        onClick={() =>
          run(
            () => updateRevealCount(previousRevealCount(revealedCount, revealMaximum)),
            "Posizione nascosta",
          )
        }
      >
        Indietro
      </button>
      <button
        type="button"
        disabled={isRevealUpdating || revealedCount >= revealMaximum}
        onClick={() => run(() => updateRevealCount(revealedCount + 1), "Posizione rivelata")}
      >
        Rivela prossima
      </button>
    </div>
  </div>
) : null}
```

Delete the old `document.querySelector(".screen-admin form")` implementation.

- [ ] **Step 7: Style the controls without changing the public-stage layout**

Add to `frontend/src/styles.css` near the existing admin screen rules:

```css
.reveal-controls {
  display: grid;
  gap: 0.75rem;
  padding: 1rem;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.04);
}

.reveal-controls p {
  margin: 0;
  font-weight: 700;
}
```

- [ ] **Step 8: Verify tests and TypeScript build**

Run:

```powershell
cd frontend
npm test
npm run build
```

Expected: all Node tests PASS and Vite build completes without TypeScript errors.

- [ ] **Step 9: Commit admin controls**

Review `git diff -- frontend/src/App.tsx frontend/src/styles.css` carefully because these files already contain user changes, then commit only the intended hunks:

```powershell
git add -p frontend/src/App.tsx frontend/src/styles.css
git add frontend/src/screen/reveal.ts frontend/tests/reveal.test.ts
git commit -m "feat: add manual reveal controls"
```

### Task 3: Public ranking and podium visibility

**Files:**
- Modify: `frontend/src/App.tsx:1692-2159`
- Test: `frontend/tests/reveal.test.ts`

- [ ] **Step 1: Add a failing test for immutability**

Add to `frontend/tests/reveal.test.ts`:

```ts
test("non modifica l'array ordinato ricevuto", () => {
  const original = ["primo", "secondo", "terzo"];
  visibleRevealedResults(original, "show_podium", 2);
  assert.deepEqual(original, ["primo", "secondo", "terzo"]);
});
```

- [ ] **Step 2: Run the test and confirm it already passes as a characterization test**

Run `node --test tests/reveal.test.ts` from `frontend`.

Expected: PASS. This records the non-mutating contract before wiring the helper into React; no production change is needed for this already-satisfied property.

- [ ] **Step 3: Derive visible ranking and podium from the persisted counter**

Import `visibleRevealedResults` from `./screen/reveal`. In `ScreenArea`, replace the existing `ranking`, `podium`, and `rearrangedPodium` derivations with:

```ts
const screenRevealMode =
  state.screenState?.mode === "reveal_ranking" ||
  state.screenState?.mode === "show_podium" ||
  state.screenState?.mode === "show_final_winners"
    ? (state.screenState.mode as RevealMode)
    : null;
const screenRevealCount = numberPayload(state.screenState, "reveal_upto", 0);
const ranking =
  screenRevealMode === "reveal_ranking"
    ? visibleRevealedResults(allRanking, screenRevealMode, screenRevealCount)
    : allRanking;
const visiblePodium =
  screenRevealMode === "show_podium" || screenRevealMode === "show_final_winners"
    ? visibleRevealedResults(allRanking, screenRevealMode, screenRevealCount)
    : allRanking.slice(0, 3);
const rearrangedPodium = podiumDisplayOrder(visiblePodium);
```

- [ ] **Step 4: Render explicit waiting states at counter zero**

Inside the ranking mode block, render this before the `<ol>` and render the list only when `ranking.length > 0`:

```tsx
{ranking.length === 0 ? (
  <div className="stage-idle">In attesa della prossima posizione.</div>
) : (
  <ol className="stage-ranking">{/* existing ranking map */}</ol>
)}
```

Inside the podium block, keep the existing `rearrangedPodium.length` condition but change its empty message to:

```tsx
<div className="podium-empty">In attesa della prossima posizione.</div>
```

Ensure runners-up are not rendered in podium modes, since they would disclose unrevealed positions. Remove the existing `allRanking.slice(3, 5)` runners-up block from the podium reveal view.

- [ ] **Step 5: Run all frontend verification**

Run:

```powershell
cd frontend
npm test
npm run build
```

Expected: all tests PASS and the production build succeeds.

- [ ] **Step 6: Manually verify the WebSocket sequence**

With the stack running, open the admin screen tab and public screen for the same live event. Verify:

1. `reveal_ranking` at zero shows no names.
2. Repeated `Rivela prossima` shows ranks `N` through `1` cumulatively without reload.
3. `Indietro` hides only the most recently revealed rank.
4. `Azzera` hides every rank.
5. `show_podium` and `show_final_winners` reveal `3`, then `2`, then `1` in fixed podium positions.
6. Button boundaries and progress text remain correct.

- [ ] **Step 7: Commit public reveal rendering**

Review and stage only the intended `App.tsx` hunks:

```powershell
git add -p frontend/src/App.tsx
git add frontend/tests/reveal.test.ts
git commit -m "feat: reveal ranking and podium sequentially"
```

### Task 4: Final regression verification

**Files:**
- Verify only; no planned production changes

- [ ] **Step 1: Run frontend tests and build from a clean command invocation**

```powershell
npm --prefix frontend test
npm --prefix frontend run build
```

Expected: both commands exit `0`.

- [ ] **Step 2: Run backend screen tests because the feature depends on their contract**

```powershell
uv run --directory backend pytest tests/test_screen_api.py -q
```

Expected: all screen API/WebSocket tests PASS.

- [ ] **Step 3: Inspect final scope**

```powershell
git diff --check
git status --short
```

Expected: no whitespace errors; unrelated pre-existing worktree changes remain untouched and identifiable.
