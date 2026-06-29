export type RevealMode = "reveal_ranking" | "show_podium";

export function revealTotal(mode: RevealMode, resultCount: number): number {
  const safeResultCount = Math.max(0, Math.trunc(resultCount));
  return mode === "reveal_ranking" ? safeResultCount : Math.min(5, safeResultCount);
}

export function clampRevealCount(value: number, total: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.min(Math.max(0, Math.trunc(value)), Math.max(0, total));
}

export function nextRevealRank(
  total: number,
  visibleCount: number,
  mode?: RevealMode | null,
): number | null {
  const safeTotal = Math.max(0, Math.trunc(total));
  const safeVisibleCount = clampRevealCount(visibleCount, safeTotal);
  if (safeVisibleCount >= safeTotal) return null;

  if (!mode || mode === "reveal_ranking") {
    return safeTotal - safeVisibleCount;
  }

  const step = safeVisibleCount + 1;
  if (step <= safeTotal - 2) {
    return safeTotal - (step - 1);
  }
  if (step === safeTotal - 1) {
    return 1;
  }
  return 2;
}

export function previousRevealCount(value: number, total: number): number {
  return Math.max(0, clampRevealCount(value, total) - 1);
}

export function visibleRevealedResults<T>(
  orderedResults: readonly T[],
  mode: RevealMode,
  visibleCount: number,
): T[] {
  const total = revealTotal(mode, orderedResults.length);
  const count = clampRevealCount(visibleCount, total);

  if (mode === "reveal_ranking") {
    return orderedResults.slice(total - count, total);
  }

  const revealedIndices: number[] = [];
  for (let i = total - 1; i >= 2; i--) {
    revealedIndices.push(i);
  }
  if (total >= 1) {
    revealedIndices.push(0);
  }
  if (total >= 2) {
    revealedIndices.push(1);
  }

  const activeIndices = revealedIndices.slice(0, count);
  return orderedResults.filter((_, idx) => activeIndices.includes(idx));
}
