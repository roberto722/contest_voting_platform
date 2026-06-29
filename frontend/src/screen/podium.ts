export function podiumDisplayOrder<T>(results: readonly T[]): T[] {
  return [results[1], results[0], results[2]].filter(
    (result): result is T => result !== undefined,
  );
}

export function podiumPercent(score: number, total: number): string {
  const percent = total > 0 ? (score / total) * 100 : 0;
  return percent.toFixed(2).replace(".", ",");
}

const assetsByRank = {
  1: {
    panel: "/quasanremo/schermo/card_1.png",
    base: "/quasanremo/schermo/base_1.png",
  },
  2: {
    panel: "/quasanremo/schermo/card_2.png",
    base: "/quasanremo/schermo/base_2.png",
  },
  3: {
    panel: "/quasanremo/schermo/card_3.png",
    base: "/quasanremo/schermo/base_3.png",
  },
} as const;

export function podiumAssets(rank: number) {
  const assets = assetsByRank[rank as keyof typeof assetsByRank];
  if (!assets) throw new Error(`Posizione podio non valida: ${rank}`);
  return assets;
}
