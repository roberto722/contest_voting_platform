import assert from "node:assert/strict";
import test from "node:test";

import {
  podiumAssets,
  podiumDisplayOrder,
  podiumPercent,
} from "../src/screen/podium.ts";

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

test("associa a ogni posizione gli asset del pannello e del piedistallo", () => {
  assert.deepEqual(podiumAssets(1), {
    panel: "/quasanremo/schermo/card_1.png",
    base: "/quasanremo/schermo/base_1.png",
  });
  assert.deepEqual(podiumAssets(2), {
    panel: "/quasanremo/schermo/card_2.png",
    base: "/quasanremo/schermo/base_2.png",
  });
  assert.deepEqual(podiumAssets(3), {
    panel: "/quasanremo/schermo/card_3.png",
    base: "/quasanremo/schermo/base_3.png",
  });
  assert.throws(() => podiumAssets(4), /Posizione podio non valida: 4/);
});
