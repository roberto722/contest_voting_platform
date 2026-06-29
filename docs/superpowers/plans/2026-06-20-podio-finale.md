# Podio finale Quasanremo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the public final-podium mode as a faithful, dynamic reproduction of the approved Quasanremo black-and-gold reference.

**Architecture:** Keep ranking data and rendering in the existing `ScreenArea`. Add one pure TypeScript helper for deterministic ordering and percentages, one generated 4K theatrical backdrop, and podium-only CSS scoped to `show_podium`/`show_final_winners`. No backend or dependency changes.

**Tech Stack:** React 18, TypeScript, Vite, native CSS, Node test runner, built-in image generation.

---

## File map

- Create `frontend/src/screen/podium.ts`: pure ordering and percentage helpers.
- Create `frontend/tests/podium.test.ts`: edge-case tests for those helpers.
- Create `frontend/public/quasanremo/schermo/podium-stage-4k.png`: generated decorative 16:9 backdrop with empty podium bases.
- Modify `frontend/src/App.tsx:1692-1902`: podium-only markup and full-screen behavior.
- Modify `frontend/src/styles.css:1156-1420`: replace the current podium block with the approved composition.

### Task 1: Lock podium data behavior with tests

**Files:**
- Create: `frontend/tests/podium.test.ts`
- Create: `frontend/src/screen/podium.ts`

- [ ] **Step 1: Write the failing helper tests**

```ts
import assert from "node:assert/strict";
import test from "node:test";

import { podiumDisplayOrder, podiumPercent } from "../src/screen/podium.ts";

test("ordina il podio visivamente come secondo, primo, terzo", () => {
  assert.deepEqual(podiumDisplayOrder(["primo", "secondo", "terzo"]), [
    "secondo",
    "primo",
    "terzo",
  ]);
  assert.deepEqual(podiumDisplayOrder(["primo", "secondo"]), ["secondo", "primo"]);
  assert.deepEqual(podiumDisplayOrder(["primo"]), ["primo"]);
  assert.deepEqual(podiumDisplayOrder([]), []);
});

test("formatta percentuali italiane e gestisce il totale zero", () => {
  assert.equal(podiumPercent(34.72, 100), "34,72");
  assert.equal(podiumPercent(1, 3), "33,33");
  assert.equal(podiumPercent(0, 0), "0,00");
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npm test`

Expected: FAIL because `../src/screen/podium.ts` does not exist.

- [ ] **Step 3: Add the minimal pure helpers**

```ts
export function podiumDisplayOrder<T>(results: readonly T[]): T[] {
  return [results[1], results[0], results[2]].filter(
    (result): result is T => result !== undefined,
  );
}

export function podiumPercent(score: number, total: number): string {
  const percent = total > 0 ? (score / total) * 100 : 0;
  return percent.toFixed(2).replace(".", ",");
}
```

- [ ] **Step 4: Run tests and type checking**

Run: `cd frontend && npm test && npm run build`

Expected: all Node tests PASS and Vite build completes.

- [ ] **Step 5: Commit the behavior**

```bash
git add frontend/src/screen/podium.ts frontend/tests/podium.test.ts
git commit -m "test: define final podium ordering"
```

### Task 2: Generate the theatrical 4K backdrop

**Files:**
- Create: `frontend/public/quasanremo/schermo/podium-stage-4k.png`

- [ ] **Step 1: Generate one project-bound backdrop using the supplied reference**

Use the built-in image generator with `C:\Users\r.scardigno\Desktop\quasanremo_assets\Immagine_reference_schermo_1.png` as a style/composition reference and this prompt:

```text
Use case: stylized-concept
Asset type: 4K background plate for a live-event web UI
Primary request: Recreate the supplied Quasanremo final-podium scene as a premium theatrical black-and-gold empty stage background. Preserve the same visual language, richness, symmetry and distant-screen readability, but remove every person, portrait, card, badge, number, word and logo so dynamic HTML can be overlaid.
Scene/backdrop: deep black concert stage, warm overhead spotlights, subtle gold confetti, fine gold musical staves and notes at the far sides, elegant ornamental flourishes, polished dark floor with restrained gold reflections.
Podium geometry: three empty realistic cylindrical black-and-gold podium bases. Left base centered at 28% canvas width with top surface around 72% canvas height; tallest center base centered at 50% with top surface around 66%; right base centered at 73% with top surface around 74%. Leave clean dark rectangular negative space above each base for dynamic contestant cards. Keep the lower strip clear for two runner-up rows and a footer.
Style/medium: high-end broadcast-event key art, photorealistic polished metal, restrained luxury, crisp 4K detail.
Composition/framing: exact 16:9 landscape, 3840x2160, symmetrical, no cropping of side ornaments.
Lighting/mood: celebratory warm gold spotlights and rim light, dark enough behind future white and gold text.
Constraints: no text, no letters, no numbers, no logos, no humans, no silhouettes, no portraits, no cards, no frames, no badges, no watermark.
```

- [ ] **Step 2: Save the selected generated image into the project**

Save the final selected output exactly as:

`frontend/public/quasanremo/schermo/podium-stage-4k.png`

Expected: a 16:9 PNG with three empty podium bases and no generated text.

- [ ] **Step 3: Validate the asset before wiring it into CSS**

Open the saved file and confirm:

- dimensions are 3840×2160 or the largest native 16:9 output returned by the generator;
- no accidental text, numbers, logos, people or card frames;
- the three pedestal tops remain unobstructed;
- center pedestal is tallest and brightest;
- left/right ornamentation does not overlap the card negative space.

If any check fails, run one targeted regeneration that names only the failed invariant, then replace the same project file.

- [ ] **Step 4: Commit the background**

```bash
git add frontend/public/quasanremo/schermo/podium-stage-4k.png
git commit -m "assets: add final podium stage"
```

### Task 3: Render dynamic podium content

**Files:**
- Modify: `frontend/src/App.tsx:1692-1902`

- [ ] **Step 1: Import the existing backdrop selector and new podium helpers**

Add near the other imports:

```ts
import { participantBackdrop } from "./public-vote/publicVote";
import { podiumDisplayOrder, podiumPercent } from "./screen/podium";
```

- [ ] **Step 2: Derive podium state once**

Replace the local podium/rearrangement calculations with:

```ts
const podiumMode =
  state.screenState?.mode === "show_podium" ||
  state.screenState?.mode === "show_final_winners";
const podium = allRanking.slice(0, 3);
const rearrangedPodium = podiumDisplayOrder(podium);
const totalFinalScore = allRanking.reduce((total, result) => total + result.final_score, 0);
```

Delete the later mutable `rearrangedPodium` block and per-item duplicate total calculations.

- [ ] **Step 3: Hide setup controls after the screen connects and omit podium capsules**

Change the outer section and connection panel rendering to:

```tsx
<section className={`screen-shell ${state.activeEventId ? "screen-shell-connected" : ""}`}>
  {!state.activeEventId ? (
    <Panel title="Connessione schermo">
      <div className="public-access">
        <input
          value={state.eventId}
          onChange={(event) =>
            setState((current) => ({ ...current, eventId: event.target.value }))
          }
          placeholder="ID evento"
        />
        <button type="button" onClick={() => run(connectScreen, "Schermo collegato")}>
          Collega
        </button>
      </div>
    </Panel>
  ) : null}
```

Wrap `StatusCapsules` in `!podiumMode`:

```tsx
{!podiumMode ? (
  <StatusCapsules
    mode={state.screenState?.mode ?? "idle"}
    isFrozen={state.competition?.status === "results_frozen"}
    isOpen={Boolean(openSession)}
    lastUpdated={lastUpdatedTime}
  />
) : null}
```

- [ ] **Step 4: Replace the podium branch with semantic dynamic content**

Use the existing mode condition and replace its body with:

```tsx
<div className="podium-section">
  {rearrangedPodium.length ? (
    <div className="podium">
      {rearrangedPodium.map((result) => {
        const index = allRanking.findIndex(
          (entry) => entry.participant_id === result.participant_id,
        );

        return (
          <article className={`podium-place podium-${result.rank}`} key={result.participant_id}>
            <div className="podium-card">
              <div
                className="podium-card-artist-bg"
                style={{ backgroundImage: `url(${participantBackdrop(index)})` }}
              />
              <div className="podium-card-shine" />
              <WreathBadge rank={result.rank} />
              <div className="podium-card-content">
                <strong className="podium-name" title={result.display_name}>
                  {result.display_name}
                </strong>
                <span className="podium-score-capsule">
                  {podiumPercent(result.final_score, totalFinalScore)}%
                </span>
              </div>
            </div>
            <span className="podium-pedestal-rank">{result.rank}</span>
          </article>
        );
      })}
    </div>
  ) : (
    <div className="podium-empty">Risultati in preparazione</div>
  )}

  {allRanking.length > 3 ? (
    <div className="podium-runners-up">
      {allRanking.slice(3, 5).map((result, index) => (
        <article key={result.participant_id} className="runner-up-item">
          <span className="runner-up-rank">{result.rank}</span>
          <span
            className="runner-up-avatar"
            style={{ backgroundImage: `url(${participantBackdrop(index + 3)})` }}
          />
          <span className="runner-up-name" title={result.display_name}>
            {result.display_name}
          </span>
          <span className="runner-up-score">
            {podiumPercent(result.final_score, totalFinalScore)}%
          </span>
        </article>
      ))}
    </div>
  ) : null}

  <p className="podium-footer">
    ☆ Grazie a tutti i partecipanti e al pubblico che ha reso possibile questa edizione. ☆
  </p>
</div>
```

- [ ] **Step 5: Run tests and build**

Run: `cd frontend && npm test && npm run build`

Expected: all tests PASS; TypeScript and Vite build complete without errors.

- [ ] **Step 6: Commit the dynamic markup**

```bash
git add frontend/src/App.tsx
git commit -m "feat: render dynamic final podium"
```

### Task 4: Apply the approved broadcast composition

**Files:**
- Modify: `frontend/src/styles.css:1156-1420`

- [ ] **Step 1: Replace the current final-podium CSS block**

Keep ranking, QR and live-vote styles unchanged. Replace only the block from `/* Final Podium Layout */` through `.podium-footer` with podium-scoped rules using these fixed anchors:

```css
.screen-shell-connected {
  max-width: none;
  gap: 0;
}

.stage-show_podium,
.stage-show_final_winners {
  container-type: inline-size;
  width: min(100vw, calc(100vh * 16 / 9));
  min-height: 0;
  aspect-ratio: 16 / 9;
  margin: auto;
  padding: 2.1cqw 4.2cqw 1.5cqw;
  background: #030303 url("/quasanremo/schermo/podium-stage-4k.png") center / 100% 100% no-repeat;
  font-family: Georgia, "Times New Roman", serif;
}

.stage-show_podium::before,
.stage-show_podium::after,
.stage-show_final_winners::before,
.stage-show_final_winners::after,
.stage-show_podium .stage-decor-frame,
.stage-show_final_winners .stage-decor-frame {
  display: none;
}

.stage-show_podium .stage-header,
.stage-show_final_winners .stage-header {
  position: absolute;
  inset: 1.5cqw auto auto 1.8cqw;
  z-index: 4;
  width: auto;
  margin: 0;
  padding: 0;
}

.stage-show_podium .stage-brand-logo,
.stage-show_final_winners .stage-brand-logo {
  height: 6.7cqw;
}

.stage-show_podium .stage-brand-wordmark,
.stage-show_final_winners .stage-brand-wordmark {
  height: 3.2cqw;
}

.stage-show_podium .stage-header-center,
.stage-show_final_winners .stage-header-center {
  display: none;
}

.stage-show_podium .stage-heading,
.stage-show_final_winners .stage-heading {
  z-index: 3;
  display: flex;
  flex-direction: column-reverse;
  margin: 1.3cqw 0 0;
}

.stage-show_podium .stage-heading p,
.stage-show_final_winners .stage-heading p {
  color: #f5ead5;
  font-family: "Outfit", "Segoe UI", sans-serif;
  font-size: 1.15cqw;
  font-weight: 500;
  letter-spacing: .06em;
  text-transform: none;
}

.stage-show_podium .stage-heading h2,
.stage-show_final_winners .stage-heading h2 {
  margin: 0;
  font-family: Georgia, "Times New Roman", serif;
  font-size: 4.2cqw;
  font-weight: 700;
  letter-spacing: -.02em;
  line-height: 1;
  filter: drop-shadow(0 0 .8cqw rgba(226, 164, 64, .45));
}

.stage-show_podium .stage-content,
.stage-show_final_winners .stage-content {
  position: absolute;
  inset: 12.8cqw 0 0;
  max-width: none;
}

.podium-section {
  position: relative;
  width: 100%;
  height: 100%;
}

.podium {
  position: absolute;
  inset: 0;
  display: block;
  width: 100%;
  max-width: none;
  margin: 0;
}

.podium-place {
  position: absolute;
  display: block;
  width: 27cqw;
  animation: risePodium .7s cubic-bezier(.1, .8, .25, 1) both;
}

.podium-place.podium-1 { left: 36.5cqw; top: 1.2cqw; width: 27cqw; }
.podium-place.podium-2 { left: 13.2cqw; top: 8.5cqw; width: 22.5cqw; }
.podium-place.podium-3 { right: 12.7cqw; top: 11cqw; width: 22.5cqw; }

.podium-card {
  position: relative;
  width: 100%;
  height: 24cqw;
  overflow: hidden;
  border: .12cqw solid #e8bc68;
  border-radius: 1.2cqw 1.2cqw .3cqw .3cqw;
  background: #090806;
  box-shadow: 0 0 1.2cqw rgba(221, 157, 54, .7), inset 0 0 1cqw rgba(255, 218, 145, .18);
}

.podium-2 .podium-card { height: 19.5cqw; border-color: #e3e1dc; box-shadow: 0 0 .8cqw rgba(225, 225, 220, .5); }
.podium-3 .podium-card { height: 18cqw; border-color: #bd7134; box-shadow: 0 0 .8cqw rgba(189, 113, 52, .5); }

.podium-card-artist-bg {
  position: absolute;
  inset: 0;
  background-position: center;
  background-size: cover;
}

.podium-card-artist-bg::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, transparent 35%, rgba(3, 3, 3, .97) 90%);
}

.podium-card-shine {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 50% 5%, rgba(255, 216, 132, .32), transparent 45%);
}

.podium-card > .rank-badge-img {
  position: absolute;
  z-index: 2;
  top: 1cqw;
  left: 1cqw;
  width: 5.2cqw;
  height: 5.2cqw;
}

.podium-card-content {
  position: absolute;
  z-index: 2;
  inset: auto 1cqw 1.1cqw;
  display: grid;
  justify-items: center;
  gap: .6cqw;
}

.podium-name {
  width: 100%;
  overflow: hidden;
  color: #fff;
  font-size: clamp(16px, 2.05cqw, 42px);
  font-weight: 700;
  line-height: 1.05;
  text-align: center;
  text-overflow: ellipsis;
  text-shadow: 0 .15cqw .35cqw #000;
  white-space: nowrap;
}

.podium-score-capsule {
  min-width: 12cqw;
  border: .1cqw solid currentColor;
  border-radius: 999px;
  background: rgba(3, 3, 3, .9);
  color: #f3c45f;
  padding: .35cqw 1.1cqw;
  font-size: 1.8cqw;
  line-height: 1;
}

.podium-2 .podium-score-capsule { color: #eee; }
.podium-3 .podium-score-capsule { color: #d98a45; }

.podium-pedestal-rank {
  position: absolute;
  left: 50%;
  top: calc(100% + 2.3cqw);
  z-index: 3;
  translate: -50% 0;
  color: #efbd59;
  font-size: 3.2cqw;
  font-weight: 700;
  text-shadow: 0 0 .6cqw #c47a1c;
}

.podium-2 .podium-pedestal-rank { top: calc(100% + 1.8cqw); color: #e4e1db; }
.podium-3 .podium-pedestal-rank { top: calc(100% + 1.5cqw); color: #d48643; }

.podium-runners-up {
  position: absolute;
  left: 12cqw;
  right: 12cqw;
  bottom: 4.7cqw;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 2cqw;
  margin: 0;
}

.runner-up-item {
  display: grid;
  grid-template-columns: 2.4cqw 4.2cqw minmax(0, 1fr) auto;
  align-items: center;
  gap: .8cqw;
  min-width: 0;
  border: .08cqw solid #a86b24;
  border-radius: .55cqw;
  background: rgba(3, 3, 3, .82);
  padding: .45cqw .9cqw;
}

.runner-up-avatar {
  width: 4.2cqw;
  height: 2.4cqw;
  background-position: center;
  background-size: cover;
}

.runner-up-rank,
.runner-up-name,
.runner-up-score { font-size: 1.35cqw; }
.runner-up-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.podium-footer {
  position: absolute;
  right: 0;
  bottom: 1.5cqw;
  left: 0;
  margin: 0;
  color: #d9b979;
  font-size: 1.05cqw;
  text-align: center;
}

.podium-empty {
  position: absolute;
  inset: 12cqw 0 auto;
  color: #f1d498;
  font-size: 2.4cqw;
  text-align: center;
}
```

- [ ] **Step 2: Prevent the mobile rule from collapsing the podium artboard**

In the existing `@media (max-width: 720px)` rule, remove `.podium` from the shared `grid-template-columns: 1fr` selector. Add:

```css
@media (max-width: 720px) {
  .stage-show_podium,
  .stage-show_final_winners {
    width: 100vw;
    min-height: 0;
    padding: 2.1cqw 4.2cqw 1.5cqw;
  }
}
```

- [ ] **Step 3: Run automated verification**

Run: `cd frontend && npm test && npm run build`

Expected: all tests PASS and build completes without TypeScript or CSS errors.

- [ ] **Step 4: Verify the artboard at target sizes**

Run: `cd frontend && npm run dev`

Open the screen route with a connected event and verify at:

- 1920×1080: artboard fills the viewport, no scroll, no capsule, 2–1–3 alignment matches the reference;
- 1366×768: all names, percentages, 4°/5° and footer remain readable;
- 1440×900: centered 16:9 letterboxing, no stretching;
- datasets containing 0, 1, 2, 3 and at least 5 results: empty state and conditional places remain coherent;
- `show_results`, `reveal_ranking`, `show_qr`, `voting_open` and `countdown`: no visual regression.

- [ ] **Step 5: Commit the visual implementation**

```bash
git add frontend/src/styles.css
git commit -m "feat: restyle final podium screen"
```

### Task 5: Final integrated verification

**Files:**
- No production files expected.

- [ ] **Step 1: Run the complete frontend checks from a clean command**

Run: `cd frontend && npm test && npm run build`

Expected: all tests PASS and the Vite production bundle builds.

- [ ] **Step 2: Inspect the scoped diff**

Run:

```bash
git diff HEAD~4 -- frontend/src/screen/podium.ts frontend/tests/podium.test.ts frontend/src/App.tsx frontend/src/styles.css frontend/public/quasanremo/schermo/podium-stage-4k.png
```

Expected: no backend changes, no dependency changes, no modifications outside the planned podium files.

- [ ] **Step 3: Record visual evidence**

Capture one 1920×1080 screenshot of `show_podium` with at least five results and compare it side-by-side with `Immagine_reference_schermo_1.png`. Reject completion if the main hierarchy, black/gold richness, podium heights, title prominence or distant readability is materially weaker than the reference.
