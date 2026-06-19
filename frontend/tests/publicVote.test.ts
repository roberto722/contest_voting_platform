import assert from "node:assert/strict";
import test from "node:test";

import {
  buildPublicVotePayload,
  getVotingState,
  isPublicVotePath,
  participantBackdrop,
  publicVoteHref,
} from "../src/public-vote/publicVote.ts";

test("riconosce soltanto la route pubblica", () => {
  assert.equal(isPublicVotePath("/vote"), true);
  assert.equal(isPublicVotePath("/vote/"), true);
  assert.equal(isPublicVotePath("/"), false);
  assert.equal(isPublicVotePath("/voter"), false);
});

test("costruisce link pubblici codificando l'id", () => {
  assert.equal(publicVoteHref("competition 1"), "/vote?competitionId=competition%201");
});

test("distingue sessione aperta, attesa e chiusa", () => {
  assert.equal(getVotingState([]), "waiting");
  assert.equal(getVotingState([{ status: "closed" }]), "closed");
  assert.equal(getVotingState([{ status: "closed" }, { status: "open" }]), "open");
});

test("costruisce i tre payload di voto", () => {
  assert.deepEqual(
    buildPublicVotePayload("token", "single_choice", {
      participantId: "p1",
      rankedParticipantIds: [],
      ratings: [],
    }),
    { voter_token: "token", method: "single_choice", participant_id: "p1" },
  );
  assert.deepEqual(
    buildPublicVotePayload("token", "ranked_choice", {
      participantId: "",
      rankedParticipantIds: ["p2", "", "p1"],
      ratings: [],
    }),
    { voter_token: "token", method: "ranked_choice", ranked_participant_ids: ["p2", "p1"] },
  );
  assert.deepEqual(
    buildPublicVotePayload("token", "criteria_rating", {
      participantId: "p1",
      rankedParticipantIds: [],
      ratings: [{ criterion_id: "c1", score: 8 }],
    }),
    {
      voter_token: "token",
      method: "criteria_rating",
      ratings: [{ participant_id: "p1", criteria: [{ criterion_id: "c1", score: 8 }] }],
    },
  );
});

test("riusa ciclicamente i cinque fondali generici", () => {
  assert.equal(participantBackdrop(0), "/quasanremo/artists/artist-bg-01.webp");
  assert.equal(participantBackdrop(5), "/quasanremo/artists/artist-bg-01.webp");
});
