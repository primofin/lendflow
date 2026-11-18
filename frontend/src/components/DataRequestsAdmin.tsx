"use client";

import { useEffect, useState } from "react";

import { apiRequest } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import type { DeletionRequestAdmin } from "@/lib/api/types";
import { formatDateTime } from "@/lib/loan/fileCheck";

import { FormError } from "./FormError";

/** LF-018 AC3: a supervisor sees deletion requests with their due dates. The API refuses others. */
export function DataRequestsAdmin() {
  const [requests, setRequests] = useState<DeletionRequestAdmin[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    apiRequest<DeletionRequestAdmin[]>("/api/data-requests")
      .then((value) => live && setRequests(value))
      .catch(
        (failure: unknown) =>
          live && setError(failure instanceof ApiError ? failure.message : "The requests could not be loaded."),
      );
    return () => {
      live = false;
    };
  }, []);

  if (error) return <FormError message={error} />;
  if (!requests) return <p>Loading…</p>;
  if (requests.length === 0) return <p>No deletion requests.</p>;

  return (
    <table className="w-full text-left" data-testid="data-requests">
      <thead>
        <tr>
          <th scope="col">Borrower</th>
          <th scope="col">Requested</th>
          <th scope="col">Due</th>
          <th scope="col">Status</th>
        </tr>
      </thead>
      <tbody>
        {requests.map((r) => (
          <tr key={r.id}>
            <td>{r.email}</td>
            <td>{formatDateTime(r.requested_at)}</td>
            <td>{formatDateTime(r.due_at)}</td>
            <td>{r.overdue ? "Open, overdue" : r.status === "open" ? "Open" : "Resolved"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
