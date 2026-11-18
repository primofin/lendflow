"use client";

import { useEffect, useState } from "react";

import { apiRequest } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import { CIC_FLAG_LABELS } from "@/lib/api/types";
import type { CicCheck } from "@/lib/api/types";

import { FormError } from "./FormError";
import { buttonClass } from "./FormField";

const POLL_MS = 1000;

/** LF-008: start the mock credit-bureau check and watch its progress. The officer can leave the
 * page and come back; progress is kept on the server. */
export function CicPanel({ applicationId, status }: { applicationId: string; status: string }) {
  const [check, setCheck] = useState<CicCheck | null | undefined>(undefined); // undefined: loading
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const url = `/api/applications/${applicationId}/cic-check`;
  const running = check?.status === "running";

  useEffect(() => {
    let live = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    async function refresh() {
      try {
        const latest = await apiRequest<CicCheck | null>(url);
        if (!live) return;
        setCheck(latest);
        setError(null);
        if (latest?.status === "running") timer = setTimeout(refresh, POLL_MS);
      } catch (failure) {
        if (!live) return;
        setError(failure instanceof ApiError ? failure.message : "The credit check could not be loaded.");
        setCheck((current) => current ?? null);
      }
    }
    // Poll only while a check is running; a new start flips `running` and re-runs this effect.
    if (check === undefined || running) void refresh();
    return () => {
      live = false;
      clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- re-run on start/finish, not on every poll result
  }, [url, running, check === undefined]);

  async function start() {
    setError(null);
    setStarting(true);
    try {
      setCheck(await apiRequest<CicCheck>(url, { method: "POST" }));
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : "The credit check could not be started.");
    } finally {
      setStarting(false);
    }
  }

  const canStart = status === "IN_REVIEW" && (check === null || check?.status === "timeout");
  if (check === undefined && !error) return null;
  if (check === null && !canStart && !error) return null;

  return (
    <section aria-labelledby="cic-heading" data-testid="cic-panel">
      <h2 id="cic-heading" className="text-lg font-semibold">
        Credit check (mock bureau)
      </h2>
      <FormError message={error} />

      {check?.status === "running" && (
        <div className="mt-3 max-w-lg">
          <div
            role="progressbar"
            aria-label="Credit check progress"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={check.progress_pct}
            className="h-3 w-full overflow-hidden rounded bg-slate-200"
          >
            <div className="h-full bg-blue-700" style={{ width: `${check.progress_pct}%` }} />
          </div>
          <p className="mt-2" data-testid="cic-remaining">
            {check.seconds_remaining === null
              ? "Waiting for the credit bureau…"
              : `About ${check.seconds_remaining} seconds remaining`}
          </p>
          <p className="mt-1 text-sm text-slate-700" data-testid="cic-message">
            {check.message}
          </p>
        </div>
      )}

      {check?.status === "done" && (
        <dl className="mt-3 grid max-w-lg grid-cols-[1fr_auto] gap-x-4 gap-y-1" data-testid="cic-result">
          <dt>Debt group</dt>
          <dd data-testid="cic-group">{check.debt_group}</dd>
          <dt>Result</dt>
          <dd data-testid="cic-flag">{check.flag ? CIC_FLAG_LABELS[check.flag] : ""}</dd>
          <dt>Summary</dt>
          <dd className="col-span-2 text-sm">{check.summary}</dd>
        </dl>
      )}

      {check?.status === "timeout" && (
        <p className="mt-3" role="status" data-testid="cic-message">
          {check.message}
        </p>
      )}

      {canStart && (
        <button type="button" disabled={starting} onClick={start} className={`${buttonClass} mt-3`}>
          {check?.status === "timeout" ? "Run the credit check again" : "Run credit check"}
        </button>
      )}
    </section>
  );
}
