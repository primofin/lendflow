"use client";

import { useEffect, useState } from "react";

import { apiRequest } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import type { DisbursementStatus, FaceMatch } from "@/lib/api/types";

import { FormError } from "./FormError";
import { buttonClass } from "./FormField";

function vnd(amount: number): string {
  return `${amount.toLocaleString("en-US")} VND`;
}

/** LF-020: pay out an approved loan. Above the threshold a (simulated) face match comes first;
 * the match is single-use and short-lived, and a failed match blocks the disbursement. */
export function DisbursementPanel({ applicationId }: { applicationId: string }) {
  const [state, setState] = useState<DisbursementStatus | null>(null);
  const [match, setMatch] = useState<FaceMatch | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const base = `/api/applications/${applicationId}`;

  const [reload, setReload] = useState(0);
  useEffect(() => {
    let live = true;
    apiRequest<DisbursementStatus>(`${base}/disbursement`)
      .then((loaded) => live && setState(loaded))
      .catch((failure) => {
        if (live) setError(failure instanceof ApiError ? failure.message : "Disbursement details could not be loaded.");
      });
    return () => {
      live = false;
    };
  }, [base, reload]);

  async function run<T>(action: () => Promise<T>, fallback: string): Promise<T | undefined> {
    setError(null);
    setBusy(true);
    try {
      return await action();
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : fallback);
      return undefined;
    } finally {
      setBusy(false);
    }
  }

  async function simulate(result: "pass" | "fail") {
    const created = await run(
      () => apiRequest<FaceMatch>(`${base}/face-match`, { method: "POST", json: { result } }),
      "The face match could not be recorded.",
    );
    if (created) setMatch(created);
  }

  async function disburse() {
    const done = await run(
      () =>
        apiRequest(`${base}/disbursement`, {
          method: "POST",
          json: { face_match_id: match?.passed ? match.id : null },
        }),
      "The disbursement could not be completed.",
    );
    if (done) {
      setMatch(null);
      setReload((n) => n + 1);
    }
  }

  if (!state) return error ? <FormError message={error} /> : null;
  const paid = state.disbursement;
  const needsMatch = state.face_match_required;
  const ready = !needsMatch || match?.passed === true;

  return (
    <section aria-labelledby="disbursement-heading" data-testid="disbursement-panel">
      <h2 id="disbursement-heading" className="text-lg font-semibold">
        Disbursement
      </h2>
      <FormError message={error} />
      {paid ? (
        <p className="mt-3" role="status" data-testid="disbursed">
          Disbursed {vnd(paid.amount_vnd)} on {new Date(paid.disbursed_at).toLocaleString("en-GB")}.
        </p>
      ) : (
        <div className="mt-3 max-w-lg">
          <p>Amount: {vnd(state.amount_vnd)}</p>
          {needsMatch && (
            <div className="mt-2">
              <p className="text-sm text-slate-700">
                Amounts above {vnd(state.threshold_vnd)} need a face match first (simulated: no image is captured).
              </p>
              {match && (
                <p role="status" data-testid="face-match-result" className="mt-2">
                  {match.passed
                    ? "Face match passed. It can be used once, within a few minutes."
                    : "Face match failed. The disbursement is blocked; try again."}
                </p>
              )}
              <div className="mt-2 flex gap-2">
                <button type="button" disabled={busy} onClick={() => simulate("pass")} className={buttonClass}>
                  Simulate face match: pass
                </button>
                <button type="button" disabled={busy} onClick={() => simulate("fail")} className={buttonClass}>
                  Simulate face match: fail
                </button>
              </div>
            </div>
          )}
          <button type="button" disabled={busy || !ready} onClick={disburse} className={`${buttonClass} mt-3`}>
            Disburse {vnd(state.amount_vnd)}
          </button>
        </div>
      )}
    </section>
  );
}
