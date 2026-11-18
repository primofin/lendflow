"use client";

import { useEffect, useState } from "react";

import { apiRequest } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import { docTypeLabel } from "@/lib/api/types";
import type { DeletionRequest, MyData } from "@/lib/api/types";
import { formatDateTime } from "@/lib/loan/fileCheck";
import { formatVnd } from "@/lib/loan/money";

import { ConfirmDialog } from "./ConfirmDialog";
import { FormError } from "./FormError";
import { buttonClass } from "./FormField";

function message(failure: unknown, fallback: string): string {
  return failure instanceof ApiError ? failure.message : fallback;
}

/** LF-018: the borrower's own data, an export, and a deletion request. Nothing is deleted here:
 * a request is recorded for a person to answer by its due date. */
export function MyDataView() {
  const [data, setData] = useState<MyData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let live = true;
    apiRequest<MyData>("/api/me/data")
      .then((value) => {
        if (!live) return;
        setData(value);
        setError(null);
      })
      .catch((failure: unknown) => live && setError(message(failure, "Your data could not be loaded.")));
    return () => {
      live = false;
    };
  }, [version]);

  async function download() {
    setActionError(null);
    setBusy(true);
    try {
      const blob = await apiRequest<Blob>("/api/me/data/export", { as: "blob" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "my-lendflow-data.json";
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (failure) {
      setActionError(message(failure, "The export could not be created."));
    } finally {
      setBusy(false);
    }
  }

  async function requestDeletion() {
    setActionError(null);
    setBusy(true);
    try {
      await apiRequest<DeletionRequest>("/api/me/data/deletion-request", { method: "POST" });
      setConfirming(false);
      setVersion((n) => n + 1);
    } catch (failure) {
      setConfirming(false);
      setActionError(message(failure, "The deletion request could not be recorded."));
    } finally {
      setBusy(false);
    }
  }

  if (error && !data) return <FormError message={error} />;
  if (!data) return <p>Loading…</p>;

  const profile = data.profile;
  const request = data.deletion_request;
  const open = request?.status === "open";

  return (
    <div className="flex flex-col gap-8">
      <FormError message={error} />
      <FormError message={actionError} />

      <section aria-labelledby="account-heading">
        <h2 id="account-heading" className="text-lg font-semibold">
          Account
        </h2>
        <dl className="mt-3 grid max-w-lg grid-cols-[1fr_auto] gap-x-4 gap-y-1">
          <dt>Email</dt>
          <dd>{data.account.email}</dd>
          <dt>Created</dt>
          <dd>{formatDateTime(data.account.created_at)}</dd>
        </dl>
      </section>

      <section aria-labelledby="profile-heading">
        <h2 id="profile-heading" className="text-lg font-semibold">
          Personal details
        </h2>
        {profile === null ? (
          <p className="mt-2">You have not given any personal details yet.</p>
        ) : (
          <dl className="mt-3 grid max-w-lg grid-cols-[1fr_auto] gap-x-4 gap-y-1" data-testid="profile">
            <dt>Name</dt>
            <dd>{profile.full_name}</dd>
            <dt>Date of birth</dt>
            <dd>{profile.date_of_birth}</dd>
            <dt>National ID</dt>
            <dd>{profile.national_id}</dd>
            <dt>Address</dt>
            <dd>{profile.address}</dd>
            <dt>Income type</dt>
            <dd>{profile.income_type}</dd>
            <dt>Monthly income</dt>
            <dd>{profile.monthly_income_vnd !== null && formatVnd(profile.monthly_income_vnd)}</dd>
            <dt>Existing debt payments</dt>
            <dd>
              {profile.existing_debt_payment_vnd !== null && formatVnd(profile.existing_debt_payment_vnd)}
            </dd>
          </dl>
        )}
      </section>

      <section aria-labelledby="apps-heading">
        <h2 id="apps-heading" className="text-lg font-semibold">
          Applications and documents
        </h2>
        {data.applications.length === 0 ? (
          <p className="mt-2">No applications.</p>
        ) : (
          <ul className="mt-3 flex flex-col gap-4" data-testid="applications">
            {data.applications.map((a) => (
              <li key={a.id}>
                <p className="font-medium">
                  {formatVnd(a.amount_vnd)} over {a.term_months} months · {a.status}
                </p>
                <ul className="ml-4 list-disc text-sm">
                  {a.documents.map((d, i) => (
                    <li key={i}>
                      {docTypeLabel(d.doc_type)}, uploaded {formatDateTime(d.uploaded_at)}
                      {d.delete_after && `, kept until ${formatDateTime(d.delete_after)}`}
                    </li>
                  ))}
                  {a.decisions.map((d, i) => (
                    <li key={`d${i}`}>
                      Decision: {d.outcome} on {formatDateTime(d.decided_at)}
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="purposes-heading">
        <h2 id="purposes-heading" className="text-lg font-semibold">
          Why we hold it
        </h2>
        <ul className="mt-3 list-disc pl-5" data-testid="purposes">
          {data.purposes.map((p) => (
            <li key={p.code}>{p.label}</li>
          ))}
        </ul>
        <p className="mt-2 text-sm">Retention period: {data.retention_months} months.</p>
        {data.consents.map((c) => (
          <p key={c.version} className="text-sm">
            Consent version {c.version} given {formatDateTime(c.given_at)}
            {c.withdrawn_at && `, withdrawn ${formatDateTime(c.withdrawn_at)}`}.
          </p>
        ))}
      </section>

      <section aria-labelledby="rights-heading">
        <h2 id="rights-heading" className="text-lg font-semibold">
          Your rights
        </h2>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <button type="button" disabled={busy} onClick={download} className={buttonClass}>
            Download my data (JSON)
          </button>
          {!open && (
            <button type="button" disabled={busy} onClick={() => setConfirming(true)} className={buttonClass}>
              Request deletion of my data
            </button>
          )}
        </div>
        {request && open && (
          <div className="mt-4 max-w-lg" data-testid="deletion-request">
            <p className="font-medium">
              Deletion requested {formatDateTime(request.requested_at)}. We will answer by{" "}
              {formatDateTime(request.due_at)}.
            </p>
            <p className="mt-2 text-sm">What we must keep for now, and why:</p>
            <ul className="ml-4 list-disc text-sm" data-testid="retained">
              {request.retained.map((r, i) => (
                <li key={i}>
                  {r.what}: {r.reason}
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>

      <ConfirmDialog
        open={confirming}
        title="Request deletion of your data?"
        confirmLabel="Yes, request deletion"
        busy={busy}
        onConfirm={requestDeletion}
        onCancel={() => setConfirming(false)}
      >
        <p>
          We will record your request and answer it within the due date shown afterwards. Nothing is deleted
          right now. Applications still being processed, and the audit log, must be kept.
        </p>
      </ConfirmDialog>
    </div>
  );
}
