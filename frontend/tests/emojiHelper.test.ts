import assert from "node:assert/strict";
import test from "node:test";
import { getPercentage, getEmojiIndex } from "../src/components/emojiHelper.ts";

test("getPercentage clamps and calculates correctly", () => {
  // Standard range 1-5
  assert.equal(getPercentage(1, 1, 5), 0.0);
  assert.equal(getPercentage(3, 1, 5), 0.5);
  assert.equal(getPercentage(5, 1, 5), 1.0);

  // Clamping
  assert.equal(getPercentage(0, 1, 5), 0.0);
  assert.equal(getPercentage(6, 1, 5), 1.0);

  // Edge case: max <= min
  assert.equal(getPercentage(3, 5, 5), 0.0);
});

test("getEmojiIndex returns indices 0 to 4 proportionally", () => {
  assert.equal(getEmojiIndex(0.0), 0);  // Seedling 🌱
  assert.equal(getEmojiIndex(0.2), 1);  // Sparkles ✨
  assert.equal(getEmojiIndex(0.5), 2);  // Star ⭐
  assert.equal(getEmojiIndex(0.8), 3);  // Fire 🔥
  assert.equal(getEmojiIndex(1.0), 4);  // Trophy 🏆
});
