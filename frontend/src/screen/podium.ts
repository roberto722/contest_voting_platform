export function podiumDisplayOrder<T>(results: readonly T[]): T[] {
  return [results[1], results[0], results[2]].filter(
    (result): result is T => result !== undefined,
  );
}

export function podiumPercent(score: number, total: number): string {
  const percent = total > 0 ? (score / total) * 100 : 0;
  return percent.toFixed(2).replace(".", ",");
}
