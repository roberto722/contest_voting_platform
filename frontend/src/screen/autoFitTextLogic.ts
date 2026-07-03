export type AutoFitMode = {
  fontSize: number;
  singleLine: boolean;
};

type ChooseAutoFitModeOptions = {
  minFont: number;
  maxFont: number;
  wrapperHeight: number;
  hasMultilineCandidate?: boolean;
  fitsSingleLine: (size: number) => boolean;
  fitsMultiLine: (size: number) => boolean;
};

export function findBestFontSize(
  minFont: number,
  maxFont: number,
  fits: (size: number) => boolean,
): number {
  let low = minFont;
  let high = maxFont;
  let best = minFont;

  while (low <= high) {
    const mid = Math.floor((low + high) / 2);

    if (fits(mid)) {
      best = mid;
      low = mid + 1;
    } else {
      high = mid - 1;
    }
  }

  return best;
}

export function buildLineCandidates(text: string, maxLines = 4): string[][] {
  const words = text.trim().split(/\s+/).filter(Boolean);
  const limit = Math.min(words.length, maxLines);
  const candidates: string[][] = [];

  function walk(start: number, lines: string[]) {
    const remainingWords = words.length - start;
    const remainingLines = limit - lines.length;

    if (remainingWords === 0) {
      if (lines.length > 1) candidates.push(lines);
      return;
    }

    if (remainingLines <= 0) return;

    for (let end = start + 1; end <= words.length; end += 1) {
      if (words.length - end > remainingLines - 1) continue;
      walk(end, [...lines, words.slice(start, end).join(" ")]);
    }
  }

  walk(0, []);
  return candidates;
}

export function chooseAutoFitMode({
  minFont,
  maxFont,
  wrapperHeight,
  hasMultilineCandidate = false,
  fitsSingleLine,
  fitsMultiLine,
}: ChooseAutoFitModeOptions): AutoFitMode {
  const bestSingleLine = findBestFontSize(minFont, maxFont, fitsSingleLine);
  const bestMultiLine = findBestFontSize(minFont, maxFont, fitsMultiLine);
  const minimumReadableSingleLine = Math.min(42, Math.floor(wrapperHeight * 0.22));
  const multilineIsCompetitive = hasMultilineCandidate && bestMultiLine >= bestSingleLine * 0.9;

  if (
    fitsSingleLine(bestSingleLine) &&
    bestSingleLine >= minimumReadableSingleLine &&
    (!hasMultilineCandidate || (!multilineIsCompetitive && bestSingleLine > bestMultiLine))
  ) {
    return { fontSize: bestSingleLine, singleLine: true };
  }

  return {
    fontSize: bestMultiLine,
    singleLine: false,
  };
}
