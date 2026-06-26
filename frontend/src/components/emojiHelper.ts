export function getPercentage(val: number, min: number, max: number): number {
  if (max <= min) return 0;
  const clamped = Math.max(min, Math.min(max, val));
  return (clamped - min) / (max - min);
}

export function getEmojiIndex(percentage: number): number {
  return Math.round(percentage * 4);
}
