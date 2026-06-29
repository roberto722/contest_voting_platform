export function countdownResetKey(mode: string | undefined, seconds: number) {
  return mode === "countdown" && seconds > 0 ? `countdown:${seconds}` : "off";
}
