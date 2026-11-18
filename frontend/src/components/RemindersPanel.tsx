"use client";

import { useState } from "react";

import { apiRequest } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";

import { FormError } from "./FormError";
import { buttonClass } from "./FormField";

/** LF-014: a supervisor queues the repayment reminders that are due now. Each one is queued once,
 * so pressing it again is harmless. (`scripts/send_reminders.py` does the same on a schedule.) */
export function RemindersPanel() {
  const [queued, setQueued] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run() {
    setError(null);
    setBusy(true);
    try {
      const result = await apiRequest<{ queued: number }>("/api/reminders/run", { method: "POST" });
      setQueued(result.queued);
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : "The reminders could not be sent.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="send-reminders-heading">
      <h2 id="send-reminders-heading" className="text-lg font-semibold">
        Repayment reminders
      </h2>
      <p className="mt-1 text-sm">
        Queue the emails due 7 days and 1 day before an instalment. Borrowers who opted out are skipped.
      </p>
      <button type="button" disabled={busy} onClick={run} className={`${buttonClass} mt-3`}>
        Send due reminders now
      </button>
      <FormError message={error} />
      {queued !== null && (
        <p role="status" className="mt-2 text-sm" data-testid="reminders-result">
          {queued === 1 ? "1 reminder queued." : `${queued} reminders queued.`}
        </p>
      )}
    </section>
  );
}
