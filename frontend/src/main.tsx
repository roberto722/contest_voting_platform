import React from "react";
import ReactDOM from "react-dom/client";

import { isPublicVotePath } from "./public-vote/publicVote";

async function bootstrap() {
  const { default: Root } = isPublicVotePath(window.location.pathname)
    ? await import("./public-vote/PublicVotePage")
    : await import("./App");

  ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
    <React.StrictMode>
      <Root />
    </React.StrictMode>,
  );
}

void bootstrap();
