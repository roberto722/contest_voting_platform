import assert from "node:assert/strict";
import test from "node:test";

import {
  clampRevealCount,
  nextRevealRank,
  previousRevealCount,
  revealTotal,
  visibleRevealedResults,
} from "../src/screen/reveal.ts";

const ranking = ["primo", "secondo", "terzo", "quarto"];

test("rivela la classifica cumulativamente dall'ultima posizione alla prima", () => {
  assert.deepEqual(visibleRevealedResults(ranking, "reveal_ranking", 0), []);
  assert.deepEqual(visibleRevealedResults(ranking, "reveal_ranking", 1), ["quarto"]);
  assert.deepEqual(visibleRevealedResults(ranking, "reveal_ranking", 2), ["terzo", "quarto"]);
  assert.deepEqual(visibleRevealedResults(ranking, "reveal_ranking", 4), ranking);
});

test("torna indietro e azzera senza superare i limiti", () => {
  assert.equal(previousRevealCount(3, 5), 2);
  assert.equal(previousRevealCount(0, 5), 0);
  assert.equal(previousRevealCount(9, 5), 4);
  assert.equal(previousRevealCount(-1, 5), 0);
});

test("rivela il podio nel flusso terzo, secondo, primo", () => {
  assert.deepEqual(visibleRevealedResults(ranking.slice(0, 3), "show_podium", 0), []);
  assert.deepEqual(visibleRevealedResults(ranking.slice(0, 3), "show_podium", 1), ["terzo"]);
  assert.deepEqual(visibleRevealedResults(ranking.slice(0, 3), "show_podium", 2), ["secondo", "terzo"]);
  assert.deepEqual(visibleRevealedResults(ranking.slice(0, 3), "show_podium", 3), ["primo", "secondo", "terzo"]);
  assert.deepEqual(visibleRevealedResults(["primo", "secondo"], "show_final_winners", 1), ["secondo"]);
});

test("limita contatori invalidi e calcola la prossima posizione", () => {
  assert.equal(revealTotal("reveal_ranking", 7), 7);
  assert.equal(revealTotal("show_podium", 7), 5);
  assert.equal(revealTotal("show_final_winners", 2), 2);
  assert.equal(clampRevealCount(-3, 4), 0);
  assert.equal(clampRevealCount(8, 4), 4);
  assert.equal(nextRevealRank(4, 0), 4);
  assert.equal(nextRevealRank(4, 3), 1);
  assert.equal(nextRevealRank(4, 4), null);

  // Test podium reveal sequence for 5 places
  assert.equal(nextRevealRank(5, 0, "show_podium"), 5);
  assert.equal(nextRevealRank(5, 1, "show_podium"), 4);
  assert.equal(nextRevealRank(5, 2, "show_podium"), 3);
  assert.equal(nextRevealRank(5, 3, "show_podium"), 2);
  assert.equal(nextRevealRank(5, 4, "show_podium"), 1);
});

test("non modifica l'array ordinato ricevuto", () => {
  const original = ["primo", "secondo", "terzo"];
  visibleRevealedResults(original, "show_podium", 2);
  assert.deepEqual(original, ["primo", "secondo", "terzo"]);
});
