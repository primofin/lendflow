"use client";

import { useEffect, useState } from "react";

import { apiRequest } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import { docTypeLabel, FLAG_LABELS } from "@/lib/api/types";
import type { Checklist, Review, UploadedDocument } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { formatDateTime } from "@/lib/loan/fileCheck";
import { formatVnd } from "@/lib/loan/money";

import { CicPanel } from "./CicPanel";
import { DisbursementPanel } from "./DisbursementPanel";
import { StatusBadge } from "./StatusBadge";
import { DecisionPanel } from "./DecisionPanel";
import { FormError } from "./FormError";
import { buttonClass } from "./FormField";

type Data = { review: Review; checklist: Checklist; documents: UploadedDocument[] };

async function loadAll(id: string): Promise<Data> {
  const base = `/api/applications/${id}`;
  const [review, checklist, documents] = await Promise.all([
    apiRequest<Review>(`${base}/review`),
    apiRequest<Checklist>(`${base}/checklist`),
    apiRequest<UploadedDocument[]>(`${base}/documents`),
  ]);
  return { review, checklist, documents };
}

function message(failure: unknown, fallback: string): string {
  return failure instanceof ApiError ? failure.message : fallback;
}

/** F4a: the staff file view: applicant, flags, claim, checklist with exceptions, documents. */
export function ReviewView({ id }: { id: string }) {
  const { user } = useAuth();
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let live = true;
    loadAll(id)
      .then((value) => {
        if (!live) return;
        setData(value);
        setError(null);
      })
      .catch((failure: unknown) => live && setError(message(failure, "The file could not be loaded.")));
    return () => {
      live = false;
    };
  }, [id, version]);

  async function act(run: () => Promise<unknown>, fallback: string) {
    setActionError(null);
    setBusy(true);
    try {
      await run();
      setVersion((n) => n + 1);
    } catch (failure) {
      setActionError(message(failure, fallback));
    } finally {
      setBusy(false);
    }
  }

  async function download(doc: UploadedDocument) {
    setActionError(null);
    // Open the tab now, inside the click, so a pop-up blocker allows it; fill it once the
    // authorised request returns. (A plain link cannot send the login header.)
    const tab = window.open("", "_blank");
    if (tab) tab.opener = null;
    try {
      const blob = await apiRequest<Blob>(`/api/applications/${id}/documents/${doc.id}/file`, {
        as: "blob",
      });
      const url = URL.createObjectURL(blob);
      if (tab) tab.location.href = url;
      else window.open(url, "_blank");
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (failure) {
      tab?.close();
      setActionError(message(failure, "The document could not be opened."));
    }
  }

  if (error && !data) return <FormError message={error} />;
  if (!data) return <p>Loading…</p>;

  const { review, checklist, documents } = data;
  const a = review.applicant;
  const isOfficer = user?.role === "officer";
  const canClaim = isOfficer && !review.assigned && review.status === "IN_REVIEW";
  const canDeclare = isOfficer && ["SUBMITTED", "IN_REVIEW"].includes(review.status);

  return (
    <div className="flex flex-col gap-6">
      <FormError message={error} />
      <FormError message={actionError} />

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_24rem]">
      <div className="flex flex-col gap-6">
      <section aria-labelledby="loan-heading">
        <h2 id="loan-heading" className="text-lg font-semibold">
          Loan
        </h2>
        <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 [&>dt]:text-slate-500 [&>dd]:text-right">
          <dt>Status</dt>
          <dd>
            <StatusBadge status={review.status} testId="status" />
          </dd>
          <dt>Amount</dt>
          <dd>{formatVnd(review.amount_vnd)}</dd>
          <dt>Term</dt>
          <dd>{review.term_months} months</dd>
          {review.annual_rate_percent !== null && (
            <>
              <dt>Rate</dt>
              <dd>{review.annual_rate_percent}% a year</dd>
            </>
          )}
          {review.purpose && (
            <>
              <dt>Purpose</dt>
              <dd>{review.purpose}</dd>
            </>
          )}
          <dt>Flags</dt>
          <dd data-testid="flags">
            {review.flags.map((f) => FLAG_LABELS[f] ?? f).join(", ") || "None"}
          </dd>
          <dt>Held by</dt>
          <dd data-testid="holder">
            {review.assigned_to_me ? "You" : review.assigned ? "Another officer" : "Nobody yet"}
            {review.supervisor_assigned && " (supervisor assigned)"}
          </dd>
        </dl>
        {canClaim && (
          <button
            type="button"
            disabled={busy}
            onClick={() =>
              act(() => apiRequest(`/api/applications/${id}/claim`, { method: "POST" }), "Could not claim the file.")
            }
            className={`${buttonClass} mt-3`}
          >
            Claim this file
          </button>
        )}
      </section>

      <section aria-labelledby="applicant-heading">
        <h2 id="applicant-heading" className="text-lg font-semibold">
          Applicant
        </h2>
        <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 [&>dt]:text-slate-500 [&>dd]:text-right">
          <dt>Name</dt>
          <dd>{a.full_name}</dd>
          <dt>Date of birth</dt>
          <dd>{a.date_of_birth}</dd>
          <dt>National ID</dt>
          <dd>{a.national_id_masked}</dd>
          <dt>Address</dt>
          <dd>{a.address}</dd>
          <dt>Income type</dt>
          <dd>{a.income_type}</dd>
          <dt>Monthly income</dt>
          <dd>{a.monthly_income_vnd !== null && formatVnd(a.monthly_income_vnd)}</dd>
          <dt>Existing debt payments</dt>
          <dd>{a.existing_debt_payment_vnd !== null && formatVnd(a.existing_debt_payment_vnd)}</dd>
        </dl>
      </section>

      <section aria-labelledby="checklist-heading">
        <h2 id="checklist-heading" className="text-lg font-semibold">
          Required documents
        </h2>
        {checklist.status === "complete" ? (
          <p
            data-testid="checklist-status"
            className="mt-2 inline-block rounded bg-green-100 px-3 py-1 font-semibold text-green-900"
          >
            Complete
          </p>
        ) : (
          <p data-testid="checklist-status" className="mt-2 font-medium">
            {checklist.status === "exception" ? "Exception declared" : "Incomplete"}
          </p>
        )}
        <ul className="mt-3 flex flex-col gap-3">
          {checklist.requirements.map((req) => (
            <li key={req.id} data-state={req.state}>
              <span className="font-medium">{req.label}</span>{" "}
              <span className="text-sm text-slate-700">
                ({req.mandatory ? "mandatory" : "optional"}) ·{" "}
                {req.state === "satisfied" && "uploaded"}
                {req.state === "waived" && "not available (exception)"}
                {req.state === "missing" && "missing"}
              </span>
              {req.state === "missing" && req.mandatory && canDeclare && (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() =>
                    act(
                      () =>
                        apiRequest(`/api/applications/${id}/exceptions`, {
                          method: "POST",
                          json: { requirement_id: req.id },
                        }),
                      "Could not record the exception.",
                    )
                  }
                  className={`${buttonClass} ml-3`}
                >
                  No {req.label} available
                </button>
              )}
            </li>
          ))}
        </ul>
        {checklist.exception_flag && (
          <p className="mt-3 text-sm">
            This file is flagged as an exception and needs a supervisor
            {checklist.supervisor_assigned ? " (assigned)." : "."}
          </p>
        )}
      </section>

      <section aria-labelledby="documents-heading">
        <h2 id="documents-heading" className="text-lg font-semibold">
          Documents
        </h2>
        {documents.length === 0 ? (
          <p className="mt-2">No documents uploaded.</p>
        ) : (
          <ul className="mt-3 flex flex-col gap-2" data-testid="documents">
            {documents.map((doc) => (
              <li key={doc.id} className="flex flex-wrap items-center gap-3">
                <span>
                  {docTypeLabel(doc.doc_type)} · uploaded {formatDateTime(doc.uploaded_at)}
                </span>
                <button
                  type="button"
                  onClick={() => download(doc)}
                  aria-label={`Open ${docTypeLabel(doc.doc_type)}`}
                  className="text-blue-800 underline"
                >
                  Open
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      </div>
      <aside className="flex flex-col gap-6 lg:sticky lg:top-20" aria-label="Actions">
      {user && <CicPanel applicationId={id} status={review.status} />}

      {user && review.status === "APPROVED" && <DisbursementPanel applicationId={id} />}

      {user && (
        <DecisionPanel
          applicationId={id}
          status={review.status}
          role={user.role}
          userId={user.id}
          onChanged={() => setVersion((n) => n + 1)}
        />
      )}
      </aside>
      </div>
    </div>
  );
}
