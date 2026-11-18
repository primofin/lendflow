"use client";

import { useEffect, useState } from "react";

import { apiRequest } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import type { ReminderSettings } from "@/lib/api/types";

import { FormError } from "./FormError";

/** LF-014: opt out of (or back into) the emails sent 7 days and 1 day before each instalment. */
export function ReminderSettingsForm() {
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let live = true;
    apiRequest<ReminderSettings>("/api/me/settings")
      .then((value) => live && setEnabled(value.repayment_reminders))
      .catch(
        (failure: unknown) =>
          live && setError(failure instanceof ApiError ? failure.message : "Your settings could not be loaded."),
      );
    return () => {
      live = false;
    };
  }, []);

  async function change(next: boolean) {
    setError(null);
    setSaved(false);
    setSaving(true);
    setEnabled(next); // show the choice at once; put it back if the save fails
    try {
      const stored = await apiRequest<ReminderSettings>("/api/me/settings", {
        method: "PUT",
        json: { repayment_reminders: next },
      });
      setEnabled(stored.repayment_reminders);
      setSaved(true);
    } catch (failure) {
      setEnabled(!next);
      setError(failure instanceof ApiError ? failure.message : "Your settings could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  if (enabled === null && !error) return <p>Loading…</p>;

  return (
    <section aria-labelledby="reminders-heading" className="max-w-lg">
      <h2 id="reminders-heading" className="text-lg font-semibold">
        Repayment reminders
      </h2>
      <p className="mt-2 text-sm">
        We email you 7 days and 1 day before each instalment on an approved loan is due. The email names the
        instalment and the date, never amounts.
      </p>
      <FormError message={error} />
      {enabled !== null && (
        <label className="mt-3 flex items-center gap-3">
          <input
            type="checkbox"
            checked={enabled}
            disabled={saving}
            onChange={(e) => change(e.target.checked)}
            className="h-5 w-5"
          />
          Email me before each repayment is due
        </label>
      )}
      {saved && (
        <p role="status" className="mt-2 text-sm" data-testid="settings-saved">
          {enabled ? "Reminders are on." : "Reminders are off."}
        </p>
      )}
    </section>
  );
}
