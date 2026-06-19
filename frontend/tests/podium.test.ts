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
