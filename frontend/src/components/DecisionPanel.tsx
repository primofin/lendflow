"use client";

import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { apiRequest } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import { OUTCOME_LABELS, OUTCOME_RESULT } from "@/lib/api/types";
import type {
  DecisionEntry,
  DecisionOutcome,
  ReasonCode,
  Role,
} from "@/lib/api/types";
import { formatDateTime } from "@/lib/loan/fileCheck";
import {
  CONFIRMATION,
  toDecisionPayload,
  validateDecision,
} from "@/lib/loan/decisionValidation";
import type { DecisionErrors, DecisionValues } from "@/lib/loan/decisionValidation";

import { ConfirmDialog } from "./ConfirmDialog";
import { FormError } from "./FormError";
import { buttonClass, FormField, inputClass } from "./FormField";

type Props = {
  applicationId: string;
  status: string;
  role: Role;
  userId: string;
  onChanged: () => void;
};

const DECIDABLE = ["IN_REVIEW", "REFERRED"];
const FINAL = ["approve", "reject"];
const EMPTY: DecisionValues = { outcome: "", reasonCode: "", explanation: "", conditions: "" };

/** LF-011: decision history, the decision form and supervisor corrections. */
export function DecisionPanel({ applicationId, status, role, userId, onChanged }: Props) {
  const [entries, setEntries] = useState<DecisionEntry[] | null>(null);
  const [reasons, setReasons] = useState<ReasonCode[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);
  const [values, setValues] = useState<DecisionValues>(EMPTY);
  const [errors, setErrors] = useState<DecisionErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [sending, setSending] = useState(false);
  const [correcting, setCorrecting] = useState<string | null>(null); // id of the entry replaced

  useEffect(() => {
    let live = true;
    Promise.all([
      apiRequest<DecisionEntry[]>(`/api/applications/${applicationId}/decisions`),
      apiRequest<ReasonCode[]>("/api/reason-codes"),
    ])
      .then(([history, codes]) => {
        if (!live) return;
        setEntries(history);
        setReasons(codes);
        setLoadError(null);
      })
      .catch(
        (failure: unknown) =>
          live &&
          setLoadError(
            failure instanceof ApiError ? failure.message : "The decisions could not be loaded.",
          ),
      );
    return () => {
      live = false;
    };
  }, [applicationId, version]);

  const latest = entries?.at(-1) ?? null;
  const canCorrect =
    role === "supervisor" &&
    ["APPROVED", "REJECTED"].includes(status) &&
    latest !== null &&
    FINAL.includes(latest.outcome) &&
    latest.superseded_by === null;
  const decidable = DECIDABLE.includes(status);
  const officerBlocked = decidable && status === "REFERRED" && role !== "supervisor";
  const showForm = (decidable && !officerBlocked) || correcting !== null;

  const options: DecisionOutcome[] = correcting
    ? ["approve", "reject"]
    : role === "officer" && status === "IN_REVIEW"
      ? ["approve", "reject", "request_info", "refer"]
      : ["approve", "reject", "request_info"];

  function set<K extends keyof DecisionValues>(key: K, value: DecisionValues[K]) {
    setValues((current) => ({ ...current, [key]: value }));
  }

  function review(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    const found = validateDecision(values);
    setErrors(found);
    if (Object.keys(found).length === 0) setConfirming(true);
  }

  async function confirm() {
    setSending(true);
    try {
      await apiRequest(`/api/applications/${applicationId}/decision`, {
        method: "POST",
        json: toDecisionPayload(values, correcting),
      });
      setValues(EMPTY);
      setCorrecting(null);
      setConfirming(false);
      setVersion((n) => n + 1);
      onChanged();
    } catch (failure) {
      setConfirming(false);
      setFormError(
        failure instanceof ApiError ? failure.message : "The decision could not be saved. Try again.",
      );
    } finally {
      setSending(false);
    }
  }

  const reasonLabel = (code: string | null) =>
    code === null ? null : (reasons.find((r) => r.code === code)?.label ?? code);

  return (
    <section aria-labelledby="decision-heading" className="flex flex-col gap-4">
      <h2 id="decision-heading" className="text-lg font-semibold">
        Decision
      </h2>
      <FormError message={loadError} />

      {entries && entries.length === 0 && <p>No decision has been recorded yet.</p>}
      {entries && entries.length > 0 && (
        <ol className="flex flex-col gap-3" data-testid="decision-history">
          {entries.map((entry) => (
            <li
              key={entry.id}
              data-outcome={entry.outcome}
              className={`rounded border p-3 ${entry.superseded_by ? "border-slate-300 bg-slate-50 text-slate-700" : "border-slate-400"}`}
            >
              <p className="font-medium">
                {OUTCOME_RESULT[entry.outcome]} ·{" "}
                <time dateTime={entry.decided_at}>{formatDateTime(entry.decided_at)}</time> ·{" "}
                {entry.decided_by === userId ? "You" : "Another staff member"}
              </p>
              {entry.supersedes_id && <p className="text-sm">Corrects an earlier decision.</p>}
              {entry.superseded_by && (
                <p className="text-sm font-medium">Corrected by a later decision.</p>
              )}
              {entry.reason_code && <p>Reason: {reasonLabel(entry.reason_code)}</p>}
              {entry.explanation && <p>{entry.explanation}</p>}
              {entry.conditions && <p>What could change the result: {entry.conditions}</p>}
            </li>
          ))}
        </ol>
      )}

      <FormError message={formError} />

      {officerBlocked && (
        <p>This file was referred to a supervisor. Only a supervisor can decide it.</p>
      )}

      {canCorrect && correcting === null && latest && (
        <div>
          <button
            type="button"
            onClick={() => {
              setCorrecting(latest.id);
              setValues(EMPTY);
              setErrors({});
              setFormError(null);
            }}
            className={buttonClass}
          >
            Correct this decision
          </button>
          <p className="mt-1 text-sm text-slate-700">
            A correction is recorded as a new entry. The original stays on record.
          </p>
        </div>
      )}

      {showForm && (
        <form onSubmit={review} className="flex max-w-xl flex-col gap-4" noValidate>
          <h3 className="font-medium">
            {correcting ? "Correct the decision" : "Record a decision"}
          </h3>
          <FormField id="outcome" label="Your decision">
            {() => (
              <select
                id="outcome"
                value={values.outcome}
                onChange={(e) => set("outcome", e.target.value as DecisionValues["outcome"])}
                aria-invalid={errors.outcome ? true : undefined}
                className={inputClass}
              >
                <option value="">Choose a decision</option>
                {options.map((option) => (
                  <option key={option} value={option}>
                    {OUTCOME_LABELS[option]}
                  </option>
                ))}
              </select>
            )}
          </FormField>
          {errors.outcome && <p className="text-sm text-red-700">{errors.outcome}</p>}

          {values.outcome === "reject" && (
            <FormField id="reasonCode" label="Reason code">
              {() => (
                <>
                  <select
                    id="reasonCode"
                    value={values.reasonCode}
                    onChange={(e) => set("reasonCode", e.target.value)}
                    aria-invalid={errors.reasonCode ? true : undefined}
                    className={inputClass}
                  >
                    <option value="">Choose a reason</option>
                    {reasons.map((reason) => (
                      <option key={reason.code} value={reason.code}>
                        {reason.label}
                      </option>
                    ))}
                  </select>
                  {errors.reasonCode && (
                    <p className="text-sm text-red-700">{errors.reasonCode}</p>
                  )}
                </>
              )}
            </FormField>
          )}

          {(values.outcome === "reject" || values.outcome === "request_info") && (
            <FormField
              id="explanation"
              label={
                values.outcome === "reject"
                  ? "Explanation for the borrower"
                  : "What the borrower must add"
              }
              hint="The borrower reads this in your words. Plain language, no internal notes."
            >
              {(describedBy) => (
                <>
                  <textarea
                    id="explanation"
                    rows={4}
                    value={values.explanation}
                    onChange={(e) => set("explanation", e.target.value)}
                    aria-describedby={describedBy}
                    aria-invalid={errors.explanation ? true : undefined}
                    className={inputClass}
                  />
                  {errors.explanation && (
                    <p className="text-sm text-red-700">{errors.explanation}</p>
                  )}
                </>
              )}
            </FormField>
          )}

          {values.outcome === "reject" && (
            <FormField
              id="conditions"
              label="Documents or conditions that could change the outcome"
            >
              {() => (
                <>
                  <textarea
                    id="conditions"
                    rows={3}
                    value={values.conditions}
                    onChange={(e) => set("conditions", e.target.value)}
                    aria-invalid={errors.conditions ? true : undefined}
                    className={inputClass}
                  />
                  {errors.conditions && (
                    <p className="text-sm text-red-700">{errors.conditions}</p>
                  )}
                </>
              )}
            </FormField>
          )}

          <div className="flex gap-3">
            <button type="submit" className={buttonClass}>
              {correcting ? "Review correction" : "Review decision"}
            </button>
            {correcting && (
              <button
                type="button"
                onClick={() => {
                  setCorrecting(null);
                  setValues(EMPTY);
                  setErrors({});
                }}
                className="rounded border border-slate-400 px-4 py-2 font-medium"
              >
                Cancel correction
              </button>
            )}
          </div>
        </form>
      )}

      <ConfirmDialog
        open={confirming}
        title={correcting ? "Confirm correction" : "Confirm decision"}
        confirmLabel="Confirm and record"
        busy={sending}
        onConfirm={confirm}
        onCancel={() => setConfirming(false)}
      >
        <p>
          {values.outcome ? CONFIRMATION[values.outcome] : ""}
          {correcting && " The original decision stays on record."}
        </p>
        <p className="mt-2 text-sm">This is recorded and cannot be deleted.</p>
      </ConfirmDialog>
    </section>
  );
}
