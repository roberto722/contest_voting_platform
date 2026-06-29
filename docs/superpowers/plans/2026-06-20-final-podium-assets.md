# Final Podium Assets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render the final podium with the existing Quasanremo panel and pedestal PNG assets while preserving dynamic competitors, scores, and the 2-1-3 display order.

**Architecture:** Keep result calculation in `ScreenArea` and add one small pure helper that maps podium ranks to existing asset URLs. Replace only the podium markup and its scoped CSS; all other screen modes continue using their current markup and styles.

**Tech Stack:** React 18, TypeScript, CSS, Node built-in test runner, Vite

---

## File map

- `frontend/src/screen/podium.ts`: pure podium ordering, percentage, and asset mapping.
- `frontend/tests/podium.test.ts`: regression checks for podium logic and asset URLs.
- `frontend/src/App.tsx`: dynamic podium markup inside `ScreenArea`.
- `frontend/src/styles.css`: 16:9 podium-only composition and responsive sizing.

### Task 1: Lock down the podium asset mapping

**Files:**
- Modify: `frontend/tests/podium.test.ts`
- Modify: `frontend/src/screen/podium.ts`

- [ ] **Step 1: Write the failing asset-mapping test**

Update the import and append this test:

```ts
import {
  podiumAssets,
  podiumDisplayOrder,
  podiumPercent,
} from "../src/screen/podium.ts";

test("associa a ogni posizione gli asset del pannello e del piedistallo", () => {
  assert.deepEqual(podiumAssets(1), {
    panel: "/quasanremo/schermo/podium_panel_1_gold_clean.png",
    base: "/quasanremo/schermo/podium_base_1_gold.png",
  });
  assert.deepEqual(podiumAssets(2), {
    panel: "/quasanremo/schermo/podium_panel_2_silver_clean.png",
    base: "/quasanremo/schermo/podium_base_2_silver.png",
  });
  assert.deepEqual(podiumAssets(3), {
    panel: "/quasanremo/schermo/podium_panel_3_bronze_clean.png",
    base: "/quasanremo/schermo/podium_base_3_bronze.png",
  });
  assert.throws(() => podiumAssets(4), /Posizione podio non valida: 4/);
});
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```powershell
cd frontend
npm test
```

Expected: FAIL because `podiumAssets` is not exported.

- [ ] **Step 3: Implement the minimal mapping**

Append to `frontend/src/screen/podium.ts`:

```ts
const assetsByRank = {
  1: {
    panel: "/quasanremo/schermo/podium_panel_1_gold_clean.png",
    base: "/quasanremo/schermo/podium_base_1_gold.png",
  },
  2: {
    panel: "/quasanremo/schermo/podium_panel_2_silver_clean.png",
    base: "/quasanremo/schermo/podium_base_2_silver.png",
  },
  3: {
    panel: "/quasanremo/schermo/podium_panel_3_bronze_clean.png",
    base: "/quasanremo/schermo/podium_base_3_bronze.png",
  },
} as const;

export function podiumAssets(rank: number) {
  const assets = assetsByRank[rank as keyof typeof assetsByRank];
  if (!assets) throw new Error(`Posizione podio non valida: ${rank}`);
  return assets;
}
```

- [ ] **Step 4: Run the focused tests**

Run:

```powershell
npm test
```

Expected: all frontend tests PASS.

- [ ] **Step 5: Commit the logic and test**

```powershell
git add frontend/src/screen/podium.ts frontend/tests/podium.test.ts
git commit -m "test: define final podium asset mapping"
```

### Task 2: Render the real panel and pedestal assets

**Files:**
- Modify: `frontend/src/App.tsx:1-6`
- Modify: `frontend/src/App.tsx:2044-2083`

- [ ] **Step 1: Import the tested helper**

Replace the podium import with:

```ts
import {
  podiumAssets,
  podiumDisplayOrder,
  podiumPercent,
} from "./screen/podium";
```

- [ ] **Step 2: Replace only the podium-place markup**

Inside `rearrangedPodium.map`, resolve the assets after `index`:

```ts
const assets = podiumAssets(result.rank);
```

Replace the current `<article>` with:

```tsx
<article className={`podium-place podium-${result.rank}`} key={result.participant_id}>
  <div className="podium-portrait">
    <div
      className="podium-card-artist-bg"
      style={{ backgroundImage: `url(${participantBackdrop(index)})` }}
    />
    <div className="podium-card-shade" />
    <img className="podium-panel-asset" src={assets.panel} alt="" />
    <div className="podium-card-content">
      <strong className="podium-name" title={result.display_name}>
        {result.display_name}
      </strong>
      <span className="podium-score-capsule">
        {podiumPercent(result.final_score, totalFinalScore)}%
      </span>
    </div>
  </div>
  <img className="podium-base-asset" src={assets.base} alt="" />
</article>
```

This deliberately removes the separate `WreathBadge`, shine layer, and text pedestal rank because those visuals already exist in the supplied PNG assets.

- [ ] **Step 3: Run TypeScript and bundle verification**

Run:

```powershell
npm run build
```

Expected: `tsc` and `vite build` complete successfully.

- [ ] **Step 4: Commit the markup**

```powershell
git add frontend/src/App.tsx
git commit -m "feat: render podium with supplied assets"
```

### Task 3: Match the reference composition

**Files:**
- Modify: `frontend/src/styles.css:1173-1450`

- [ ] **Step 1: Replace the old generated-card rules**

Keep the existing podium stage, header, heading, runners-up, footer, and empty-state selectors. Replace the rules from `.podium-place` through `.podium-3 .podium-score-capsule` with this asset-based composition:

```css
.podium-place {
  position: absolute;
  display: grid;
  justify-items: center;
  animation: risePodium .7s cubic-bezier(.1, .8, .25, 1) both;
}

.podium-place.podium-1 { left: 37.5cqw; top: .5cqw; width: 25cqw; animation-delay: 200ms; }
.podium-place.podium-2 { left: 14.5cqw; top: 11cqw; width: 23cqw; animation-delay: 100ms; }
.podium-place.podium-3 { right: 14.5cqw; top: 13cqw; width: 23cqw; animation-delay: 300ms; }

.podium-portrait {
  position: relative;
  z-index: 2;
  width: 100%;
  aspect-ratio: 209 / 331;
}

.podium-card-artist-bg,
.podium-card-shade {
  position: absolute;
  inset: 4% 6% 10%;
  border-radius: 8% 8% 2% 2%;
}

.podium-card-artist-bg {
  background-position: center;
  background-size: cover;
}

.podium-card-shade {
  background: linear-gradient(180deg, transparent 42%, rgba(3, 3, 3, .96) 88%);
}

.podium-panel-asset {
  position: absolute;
  z-index: 1;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: fill;
  pointer-events: none;
}

.podium-card-content {
  position: absolute;
  z-index: 3;
  right: 9%;
  bottom: 13%;
  left: 9%;
  display: grid;
  justify-items: center;
  gap: .55cqw;
}

.podium-name {
  width: 100%;
  overflow: hidden;
  color: #fff;
  font-size: 1.65cqw;
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
  font-weight: 700;
  line-height: 1;
  text-align: center;
}

.podium-2 .podium-score-capsule { color: #eee; }
.podium-3 .podium-score-capsule { color: #d98a45; }

.podium-base-asset {
  width: 110%;
  margin-top: -8%;
  object-fit: contain;
  pointer-events: none;
}
```

Remove the obsolete `.podium-card`, `.podium-card-shine`, podium badge positioning, and `.podium-pedestal-rank` rules.

- [ ] **Step 2: Align the fixed stage elements**

Adjust only the podium-scoped values to match the reference:

```css
.stage-show_podium .stage-heading,
.stage-show_final_winners .stage-heading {
  z-index: 3;
  display: flex;
  flex-direction: column-reverse;
  margin: .8cqw 0 0;
}

.stage-show_podium .stage-content,
.stage-show_final_winners .stage-content {
  position: absolute;
  inset: 12cqw 0 0;
  max-width: none;
}

.podium-runners-up {
  position: absolute;
  left: 11.5cqw;
  right: 11.5cqw;
  bottom: 4.2cqw;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 2cqw;
  margin: 0;
}

.podium-footer {
  position: absolute;
  right: 0;
  bottom: 1.1cqw;
  left: 0;
  margin: 0;
  color: #d9b979;
  font-size: 1.05cqw;
  font-weight: 600;
  letter-spacing: .03em;
  text-align: center;
}
```

- [ ] **Step 3: Run all frontend checks**

Run:

```powershell
cd frontend
npm test
npm run build
```

Expected: all tests PASS and Vite reports a successful production build.

- [ ] **Step 4: Perform the 16:9 visual regression check**

Open the existing connected screen in `show_podium` mode at 1672 x 941 and verify:

- the supplied panel and base PNGs are visible for ranks 1, 2, and 3;
- the visual order is 2-1-3;
- names and percentages remain inside each panel;
- fourth and fifth place remain inside the two lower strips;
- no podium rule changes `show_results`, `show_qr`, or voting modes.

Expected: the composition follows `Immagine_reference_schermo_1.png` and has no horizontal or vertical overflow.

- [ ] **Step 5: Commit the final styling**

```powershell
git add frontend/src/styles.css
git commit -m "style: align final podium with reference"
```

### Task 4: Final verification

**Files:**
- Verify only; no planned modifications.

- [ ] **Step 1: Verify the focused diff**

Run:

```powershell
git diff HEAD~3 -- frontend/src/screen/podium.ts frontend/tests/podium.test.ts frontend/src/App.tsx frontend/src/styles.css
git diff --check HEAD~3..HEAD
```

Expected: only podium logic, markup, and scoped styles changed; `git diff --check` emits no errors.

- [ ] **Step 2: Re-run the final checks**

Run:

```powershell
cd frontend
npm test
npm run build
```

Expected: all tests PASS and the production build succeeds.
