"use client";

import { useEffect, useState } from "react";

import { apiRequest } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import { DOC_TYPE_LABELS, docTypeLabel } from "@/lib/api/types";
import type {
  Application,
  Checklist,
  Tracker,
  UploadedDocument,
  UploadNotice,
} from "@/lib/api/types";
import { formatDateTime } from "@/lib/loan/fileCheck";
import { formatVnd } from "@/lib/loan/money";

import { FormError } from "./FormError";
import { buttonClass } from "./FormField";
import { ScheduleTable } from "./ScheduleTable";
import { TrackerPanel } from "./TrackerPanel";
import { UploadControl } from "./UploadControl";

/** Statuses in which the API accepts new documents (document_service.UPLOADABLE_STATUSES). */
const UPLOADABLE = ["SUBMITTED", "IN_REVIEW", "NEEDS_INFO"];

type Data = {
  application: Application;
  tracker: Tracker;
  checklist: Checklist;
  documents: UploadedDocument[];
  notice: UploadNotice;
};

async function loadAll(id: string): Promise<Data> {
  const base = `/api/applications/${id}`;
  const [application, tracker, checklist, documents, notice] = await Promise.all([
    apiRequest<Application>(base),
    apiRequest<Tracker>(`${base}/tracker`),
    apiRequest<Checklist>(`${base}/checklist`),
    apiRequest<UploadedDocument[]>(`${base}/documents`),
    apiRequest<UploadNotice>("/api/documents/notice"),
  ]);
  return { application, tracker, checklist, documents, notice };
}

function describe(failure: unknown): string {
  return failure instanceof ApiError ? failure.message : "The application could not be loaded.";
}

/** LF-012 tracker, LF-007 checklist (borrower view) and LF-005 uploads on one page. */
export function ApplicationDetail({ id }: { id: string }) {
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);
  const [resubmitError, setResubmitError] = useState<string | null>(null);
  const [resubmitting, setResubmitting] = useState(false);

  useEffect(() => {
    let live = true;
    loadAll(id)
      .then((value) => {
        if (!live) return;
        setData(value);
        setError(null);
      })
      .catch((failure: unknown) => live && setError(describe(failure)));
    return () => {
      live = false;
    };
  }, [id, version]);

  const reload = () => setVersion((n) => n + 1);

  async function resubmit() {
    setResubmitError(null);
    setResubmitting(true);
    try {
      await apiRequest(`/api/applications/${id}/resubmit`, { method: "POST" });
      reload();
    } catch (failure) {
      setResubmitError(
        failure instanceof ApiError ? failure.message : "Could not resubmit. Try again.",
      );
    } finally {
      setResubmitting(false);
    }
  }

  if (error && !data) return <FormError message={error} />;
  if (!data) return <p>Loading…</p>;

  const { application, tracker, checklist, documents, notice } = data;
  const canUpload = UPLOADABLE.includes(application.status);
  const knownIds = documents.map((d) => d.id);
  const needsInfo = tracker.needs_info;
  const missing = checklist.requirements.filter((r) => r.state === "missing");

  return (
    <div className="flex flex-col gap-8">
      <FormError message={error} />

      <section aria-labelledby="summary-heading">
        <h2 id="summary-heading" className="text-lg font-semibold">
          Application summary
        </h2>
        <dl className="mt-3 grid max-w-md grid-cols-[1fr_auto] gap-x-4 gap-y-1">
          <dt>Status</dt>
          <dd data-testid="status">{application.status}</dd>
          <dt>Amount</dt>
          <dd>{formatVnd(application.amount_vnd)}</dd>
          <dt>Term</dt>
          <dd>{application.term_months} months</dd>
          {application.purpose && (
            <>
              <dt>Purpose</dt>
              <dd>{application.purpose}</dd>
            </>
          )}
        </dl>
      </section>

      <TrackerPanel tracker={tracker} />

      {application.status === "APPROVED" && <ScheduleTable applicationId={id} />}

      {needsInfo && (
        <section
          aria-labelledby="needs-info-heading"
          className="rounded border-2 border-amber-500 bg-amber-50 p-4"
        >
          <h2 id="needs-info-heading" className="text-lg font-semibold">
            We need more from you
          </h2>
          {needsInfo.message && <p className="mt-2">{needsInfo.message}</p>}
          {needsInfo.missing_documents.length > 0 && (
            <ul className="mt-3 flex flex-col gap-3">
              {needsInfo.missing_documents.map((item) => (
                <li key={item.label}>
                  <span className="font-medium">{item.label}</span>
                  <UploadControl
                    applicationId={id}
                    label={item.label}
                    docTypes={item.accepted_types}
                    notice={notice}
                    knownIds={knownIds}
                    onDone={reload}
                  />
                </li>
              ))}
            </ul>
          )}
          {needsInfo.can_resubmit ? (
            <div className="mt-4">
              <button type="button" onClick={resubmit} disabled={resubmitting} className={buttonClass}>
                {resubmitting ? "Sending…" : "Resubmit for review"}
              </button>
              <FormError message={resubmitError} />
            </div>
          ) : (
            <p className="mt-3 text-sm">
              Upload the items above, then you can send the application back for review.
            </p>
          )}
        </section>
      )}

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
            {checklist.status === "exception"
              ? "Under exception review"
              : `${missing.length} document${missing.length === 1 ? "" : "s"} still needed`}
          </p>
        )}
        <ul className="mt-3 flex flex-col gap-3">
          {checklist.requirements.map((req) => (
            <li key={req.id} data-state={req.state}>
              <span className="font-medium">{req.label}</span>{" "}
              <span className="text-sm text-slate-700">
                ({req.mandatory ? "required" : "optional"}) ·{" "}
                {req.state === "satisfied" && "uploaded"}
                {req.state === "waived" && "not needed"}
                {req.state === "missing" && "not uploaded yet"}
              </span>
              {req.state === "missing" && canUpload && !needsInfo && (
                <UploadControl
                  applicationId={id}
                  label={req.label}
                  docTypes={req.doc_types}
                  notice={notice}
                  knownIds={knownIds}
                  onDone={reload}
                />
              )}
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="documents-heading">
        <h2 id="documents-heading" className="text-lg font-semibold">
          Your documents
        </h2>
        <p className="mt-2 rounded border border-amber-300 bg-amber-50 px-3 py-2 text-sm">
          {notice.notice}
        </p>
        {documents.length === 0 ? (
          <p className="mt-3">No documents uploaded yet.</p>
        ) : (
          <ul className="mt-3 flex flex-col gap-1" data-testid="documents">
            {documents.map((doc) => (
              <li key={doc.id}>
                {docTypeLabel(doc.doc_type)} · uploaded {formatDateTime(doc.uploaded_at)}
              </li>
            ))}
          </ul>
        )}
        {canUpload ? (
          <div className="mt-4">
            <h3 className="font-medium">Add another document</h3>
            <UploadControl
              applicationId={id}
              label="another document"
              docTypes={Object.keys(DOC_TYPE_LABELS)}
              notice={notice}
              knownIds={knownIds}
              onDone={reload}
            />
          </div>
        ) : (
          <p className="mt-3 text-sm">Documents can no longer be added to this application.</p>
        )}
      </section>
    </div>
  );
}
