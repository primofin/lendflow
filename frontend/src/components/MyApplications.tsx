"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { apiRequest } from "@/lib/api/client";
import type { Application } from "@/lib/api/types";
import { formatDateTime } from "@/lib/loan/fileCheck";
import { formatVnd } from "@/lib/loan/money";

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
    <section aria-labelledby="mine-heading" className="mt-6">
      <h2 id="mine-heading" className="text-lg font-semibold">
        Your applications
      </h2>
      {applications.length === 0 ? (
        <p className="mt-2">
          You have no applications yet.{" "}
          <Link href="/apply" className="text-blue-800 underline">
            Apply for a loan
          </Link>
        </p>
      ) : (
        <ul className="mt-2 flex flex-col gap-2">
          {applications.map((app) => (
            <li key={app.id}>
              <Link href={`/applications/${app.id}`} className="text-blue-800 underline">
                {formatVnd(app.amount_vnd)} over {app.term_months} months
              </Link>{" "}
              · {app.status}
              {app.submitted_at && <> · submitted {formatDateTime(app.submitted_at)}</>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
