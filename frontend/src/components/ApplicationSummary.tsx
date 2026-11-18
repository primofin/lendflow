"use client";

import { useEffect, useState } from "react";

import { apiRequest } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import type { Application } from "@/lib/api/types";
import { formatVnd } from "@/lib/loan/money";

import { FormError } from "./FormError";

/** LF-004: confirmation after submitting. The status tracker (LF-012) grows from this page. */
export function ApplicationSummary({ id }: { id: string }) {
  const [application, setApplication] = useState<Application | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    apiRequest<Application>(`/api/applications/${id}`)
      .then((value) => live && setApplication(value))
      .catch(
        (failure: unknown) =>
          live &&
          setError(
            failure instanceof ApiError ? failure.message : "The application could not be loaded.",
          ),
      );
    return () => {
      live = false;
    };
  }, [id]);

  if (error) return <FormError message={error} />;
  if (!application) return <p>Loading…</p>;
  return (
    <section aria-labelledby="summary-heading">
      <h2 id="summary-heading" className="text-lg font-semibold">
        Application submitted
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
  );
}
