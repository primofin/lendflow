"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { apiRequest } from "@/lib/api/client";
import type { Application } from "@/lib/api/types";
import { formatDateTime } from "@/lib/loan/fileCheck";
import { formatVnd } from "@/lib/loan/money";

import { StatusBadge } from "./StatusBadge";

/** F3: the borrower's way back to the tracker after logging in again. */
export function MyApplications() {
  const [applications, setApplications] = useState<Application[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let live = true;
    apiRequest<Application[]>("/api/applications")
      .then((value) => live && setApplications(value))
      .catch(() => live && setFailed(true));
    return () => {
      live = false;
    };
  }, []);

  if (failed) return <p role="alert">Your applications could not be loaded. Try again.</p>;
  if (!applications) return <p>Loading your applications…</p>;
  return (
    <section aria-labelledby="mine-heading" className="mt-6 !border-0 !bg-transparent !p-0 !shadow-none">
      <div className="flex items-center justify-between">
        <h2 id="mine-heading" className="text-lg font-semibold">
          Your applications
        </h2>
      </div>
      {applications.length === 0 ? (
        <p className="mt-3 rounded-2xl bg-surface p-6 shadow-card ring-1 ring-slate-200/70">
          You have no applications yet.{" "}
          <Link href="/apply" className="text-blue-800 underline">
            Apply for a loan
          </Link>
        </p>
      ) : (
        <ul className="mt-3 grid gap-3 sm:grid-cols-2">
          {applications.map((app) => (
            <li key={app.id} className="rounded-2xl bg-surface p-5 shadow-card ring-1 ring-slate-200/70">
              <div className="flex items-start justify-between gap-3">
                <Link href={`/applications/${app.id}`} className="text-xl font-bold tracking-tight text-blue-900">
                  {formatVnd(app.amount_vnd)} over {app.term_months} months
                </Link>
                <StatusBadge status={app.status} />
              </div>
              {app.submitted_at && (
                <p className="mt-2 text-sm text-slate-600">submitted {formatDateTime(app.submitted_at)}</p>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
