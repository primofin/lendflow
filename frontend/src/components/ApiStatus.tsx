"use client";

import { useEffect, useState } from "react";

import { apiRequest } from "@/lib/api/client";

type State = "checking" | "ok" | "down";

/** Shows whether the proxy to the backend works. Handy while the app is being set up. */
export function ApiStatus() {
  const [state, setState] = useState<State>("checking");

  useEffect(() => {
    apiRequest<{ status: string }>("/api/health")
      .then((body) => setState(body.status === "ok" ? "ok" : "down"))
      .catch(() => setState("down"));
  }, []);

  const text = {
    checking: "Checking the service…",
    ok: "Service is running.",
    down: "The service is not reachable. Start the backend and reload.",
  }[state];
  return (
    <p className="mt-8 text-sm text-slate-500" role="status">
      {text}
    </p>
  );
}
