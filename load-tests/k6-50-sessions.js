import http from "k6/http";
import { check, fail, sleep } from "k6";

const backendUrl = requiredEnv("BACKEND_URL").replace(/\/$/, "");
const frontendUrl = (__ENV.FRONTEND_URL || "").replace(/\/$/, "");
const eventId = requiredEnv("EVENT_ID");
const competitionId = requiredEnv("COMPETITION_ID");
const voteMethod = __ENV.VOTE_METHOD || "single_choice";
const accessCodes = (__ENV.LOAD_TEST_ACCESS_CODES || "")
  .split(/\r?\n/)
  .map((line) => line.trim())
  .filter(Boolean);
const judgeCredentials = (__ENV.JUDGE_ACCESS_CODES || "")
  .split(/\r?\n/)
  .map((line) => line.trim())
  .filter(Boolean)
  .map((line) => {
    const [judgeId, accessCode] = line.split(/:(.*)/s);
    return { judgeId, accessCode };
  })
  .filter((item) => item.judgeId && item.accessCode);

export const options = {
  scenarios: {
    internet_50_sessions: {
      executor: "per-vu-iterations",
      vus: 50,
      iterations: 1,
      maxDuration: "3m",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<1500"],
  },
};

export function setup() {
  if (accessCodes.length < 40) {
    fail(`Expected at least 40 access codes, got ${accessCodes.length}`);
  }

  const participants = getJson(
    `${backendUrl}/api/competitions/${competitionId}/participants`,
    "participants"
  );
  const activeParticipants = asList(participants)
    .filter((p) => p.active !== false)
    .map((p) => p.id)
    .filter(Boolean);

  if (!activeParticipants.length) {
    fail("No active participants returned by backend");
  }

  return { activeParticipants };
}

export default function (data) {
  sleep(Math.random() * 2);

  if (__VU <= accessCodes.length) {
    voteAsUser(accessCodes[__VU - 1], data.activeParticipants);
    return;
  }

  const judgeIndex = __VU - accessCodes.length - 1;
  if (judgeIndex >= 0 && judgeIndex < judgeCredentials.length) {
    actAsJudge(judgeCredentials[judgeIndex]);
    return;
  }

  spectate();
}

function voteAsUser(accessCode, participantIds) {
  const access = getJson(
    `${backendUrl}/api/vote/access?event_id=${encodeURIComponent(eventId)}&access_code=${encodeURIComponent(accessCode)}`,
    "voter_access"
  );
  const voterAccountId = access.voter_account_id || access.id;
  const accessToken = access.access_token;

  check(access, {
    "access returns voter credentials": () => Boolean(voterAccountId && accessToken),
  });

  const participantId = participantIds[(__VU - 1) % participantIds.length];
  const res = http.post(
    `${backendUrl}/api/competitions/${competitionId}/public-votes`,
    JSON.stringify(buildVotePayload(participantId, participantIds)),
    {
      headers: {
        "Content-Type": "application/json",
        "x-voter-account-id": voterAccountId,
        "x-voter-access-token": accessToken,
      },
      tags: { flow: "public_vote" },
    }
  );

  check(res, {
    "vote accepted or already handled": (r) => [200, 201, 409].includes(r.status),
  });

  getJson(`${backendUrl}/api/competitions/${competitionId}/public-votes/summary`, "summary");
}

function spectate() {
  if (frontendUrl) {
    check(
      http.get(`${frontendUrl}/vote?competitionId=${encodeURIComponent(competitionId)}`, {
        tags: { flow: "frontend_vote_page" },
      }),
      {
        "vote page reachable": (r) => r.status < 500,
      }
    );
  }

  getJson(`${backendUrl}/api/competitions/${competitionId}/public-votes/summary`, "summary");
  getJson(`${backendUrl}/api/competitions/${competitionId}/participants`, "participants");
}

function actAsJudge({ judgeId, accessCode }) {
  const access = postJson(
    `${backendUrl}/api/judge-access`,
    { judge_id: judgeId, access_code: accessCode },
    "judge_access"
  );

  check(access, {
    "judge access returns assigned competitions": () => Array.isArray(access.competitions),
  });

  getJson(
    `${backendUrl}/api/competitions/${competitionId}/judge-votes/status?judge_id=${encodeURIComponent(judgeId)}&access_code=${encodeURIComponent(accessCode)}`,
    "judge_status"
  );
}

function buildVotePayload(participantId, participantIds) {
  if (voteMethod === "ranked_choice") {
    return {
      method: voteMethod,
      ranked_participant_ids: participantIds.slice(0, Math.min(3, participantIds.length)),
    };
  }

  return {
    method: voteMethod,
    participant_id: participantId,
  };
}

function getJson(url, label) {
  const res = http.get(url, { tags: { flow: label } });
  check(res, { [`${label} status ok`]: (r) => r.status >= 200 && r.status < 300 });
  if (res.status < 200 || res.status >= 300) {
    fail(`${label} failed with ${res.status}: ${res.body}`);
  }
  return res.json();
}

function postJson(url, payload, label) {
  const res = http.post(url, JSON.stringify(payload), {
    headers: { "Content-Type": "application/json" },
    tags: { flow: label },
  });
  check(res, { [`${label} status ok`]: (r) => r.status >= 200 && r.status < 300 });
  if (res.status < 200 || res.status >= 300) {
    fail(`${label} failed with ${res.status}: ${res.body}`);
  }
  return res.json();
}

function asList(value) {
  if (Array.isArray(value)) return value;
  if (Array.isArray(value.items)) return value.items;
  if (Array.isArray(value.participants)) return value.participants;
  return [];
}

function requiredEnv(name) {
  if (!__ENV[name]) {
    fail(`${name} env var is required`);
  }
  return __ENV[name];
}
