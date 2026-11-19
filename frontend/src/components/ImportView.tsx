"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import type { FormEvent } from "react";

import { apiRequest } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import type { ImportResult } from "@/lib/api/types";
import { checkImportFile, errorReportCsv } from "@/lib/loan/importReport";

import { FormError } from "./FormError";
import { buttonClass, inputClass } from "./FormField";

function save(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

/** LF-013: upload a CSV; valid rows become DRAFT applications. Imported drafts are not processed
 * until the borrower gives consent (BR-21), which this release does not yet offer (D-030). */
export function ImportView() {
  const [result, setResult] = useState<ImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  async function template() {
    setError(null);
    try {
      save(await apiRequest<Blob>("/api/imports/applications/template", { as: "blob" }), "applications-template.csv");
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : "The template could not be downloaded.");
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setResult(null);
    const file = input.current?.files?.[0];
    if (!file) return setError("Choose a CSV file first.");
    const problem = checkImportFile(file);
    if (problem) return setError(problem);
    const form = new FormData();
    form.set("file", file);
    setSending(true);
    try {
      setResult(await apiRequest<ImportResult>("/api/imports/applications", { method: "POST", form }));
      if (input.current) input.current.value = "";
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : "The file could not be imported.");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <section aria-labelledby="how-heading">
        <h2 id="how-heading" className="text-lg font-semibold">
          Before you start
        </h2>
        <ul className="mt-2 list-disc pl-5 text-sm">
          <li>Use the template&apos;s column names. Use synthetic data only.</li>
          <li>Files must be UTF-8 CSV, 2 MB or smaller.</li>
          <li>
            Valid rows become <strong>draft</strong> applications. A draft is not reviewed, checked or
            decided until the borrower has given consent.
          </li>
          <li>Rows for a borrower who already exists, or was already imported, are skipped.</li>
        </ul>
        <button type="button" onClick={template} className={`${buttonClass} mt-3`}>
          Download the template
        </button>
      </section>

      <form onSubmit={submit} className="flex flex-col items-start gap-3 rounded-2xl bg-white p-6 shadow-card ring-1 ring-slate-200/70" aria-label="Import a CSV file">
        <label className="flex flex-col gap-1 text-sm font-medium">
          CSV file
          <input ref={input} type="file" accept=".csv,text/csv" className={inputClass} />
        </label>
        <button type="submit" disabled={sending} className={buttonClass}>
          {sending ? "Importing…" : "Import"}
        </button>
      </form>

      <FormError message={error} />

      {result && (
        <section aria-labelledby="result-heading" data-testid="import-result">
          <h2 id="result-heading" className="text-lg font-semibold">
            Result
          </h2>
          <dl className="mt-3 grid max-w-sm grid-cols-[1fr_auto] gap-x-4 gap-y-1">
            <dt>Rows in the file</dt>
            <dd data-testid="count-total">{result.total_rows}</dd>
            <dt>Imported as drafts</dt>
            <dd data-testid="count-imported">{result.imported}</dd>
            <dt>Skipped as duplicates</dt>
            <dd data-testid="count-duplicates">{result.duplicates}</dd>
            <dt>Rows with errors</dt>
            <dd data-testid="count-invalid">{result.invalid}</dd>
          </dl>

          {result.issues.length > 0 && (
            <div className="mt-4">
              <button
                type="button"
                className={buttonClass}
                onClick={() =>
                  save(new Blob([errorReportCsv(result.issues)], { type: "text/csv" }), "import-report.csv")
                }
              >
                Download the error report
              </button>
              <table className="mt-3 w-full text-left text-sm" data-testid="issues">
                <thead>
                  <tr>
                    <th scope="col">Row</th>
                    <th scope="col">Type</th>
                    <th scope="col">Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {result.issues.map((i) => (
                    <tr key={`${i.row}-${i.kind}`}>
                      <td>{i.row}</td>
                      <td>{i.kind === "duplicate" ? "Skipped" : "Error"}</td>
                      <td>{i.message}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {result.created.length > 0 && (
            <div className="mt-4">
              <h3 className="font-medium">Imported rows</h3>
              <ul className="mt-2 list-disc pl-5 text-sm" data-testid="created">
                {result.created.map((c) => (
                  <li key={c.application_id}>
                    Row {c.row}:{" "}
                    <Link href={`/review/${c.application_id}`} className="text-blue-800 underline">
                      open the draft
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
