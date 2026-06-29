import React from "react";
import ReactDOM from "react-dom/client";

import { isPublicVotePath } from "./public-vote/publicVote";

export function isJudgePath(pathname: string): boolean {
  return pathname === "/judge" || pathname === "/judge/";
}

async function bootstrap() {
  const pathname = window.location.pathname;
  const Root = isPublicVotePath(pathname)
    ? (await import("./public-vote/PublicVotePage")).default
    : isJudgePath(pathname)
      ? (await import("./judge/JudgePage")).default
      : (await import("./App")).default;

  ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
    <React.StrictMode>
      <Root />
    </React.StrictMode>,
  );
}

void bootstrap();
