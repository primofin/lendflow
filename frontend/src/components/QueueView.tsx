"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { apiRequest } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import { FLAG_LABELS } from "@/lib/api/types";
import type { QueuePage } from "@/lib/api/types";
import { formatVnd } from "@/lib/loan/money";

import { FormError } from "./FormError";
import { buttonClass, inputClass, secondaryButtonClass } from "./FormField";

const PAGE_SIZE = 50;

export function formatAge(hours: number | null): string {
  if (hours === null) return "";
  if (hours < 1) return "under 1 hour";
  if (hours < 48) return `${Math.floor(hours)} h`;
  return `${Math.floor(hours / 24)} days`;
}

/** LF-010: the officer queue. Oldest first by default; filter by status or flag. */
export function QueueView() {
  const [status, setStatus] = useState("IN_REVIEW");
  const [flag, setFlag] = useState("");
  const [sort, setSort] = useState("oldest");
  const [offset, setOffset] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [page, setPage] = useState<QueuePage | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    const query = new URLSearchParams({
      status,
      sort,
      limit: String(PAGE_SIZE),
      offset: String(offset),
    });
    if (flag) query.set("flag", flag);
    apiRequest<QueuePage>(`/api/queue?${query}`)
      .then((value) => {
        if (!live) return;
        setPage(value);
        setError(null);
      })
      .catch(
        (failure: unknown) =>
          live &&
          setError(failure instanceof ApiError ? failure.message : "The queue could not be loaded."),
      );
    return () => {
      live = false;
    };
  }, [status, flag, sort, offset, refresh]);

  function change(apply: () => void) {
    apply();
    setOffset(0);
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end gap-4 rounded-2xl bg-surface p-4 shadow-card ring-1 ring-slate-200/70">
        <label className="flex flex-col gap-1 text-sm font-medium">
          Status
          <select
            value={status}
            onChange={(e) => change(() => setStatus(e.target.value))}
            className={inputClass}
          >
            <option value="IN_REVIEW">In review</option>
            <option value="REFERRED">Referred (waiting for a supervisor)</option>
            <option value="SUBMITTED">Submitted (documents incomplete)</option>
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium">
          Flag
          <select
            value={flag}
            onChange={(e) => change(() => setFlag(e.target.value))}
            className={inputClass}
          >
            <option value="">Any</option>
            {Object.entries(FLAG_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium">
          Order
          <select
            value={sort}
            onChange={(e) => change(() => setSort(e.target.value))}
            className={inputClass}
          >
            <option value="oldest">Oldest first</option>
            <option value="newest">Newest first</option>
          </select>
        </label>
        <button type="button" onClick={() => setRefresh((n) => n + 1)} className={buttonClass}>
          Refresh
        </button>
      </div>

      <FormError message={error} />
      {!page && !error && (
        <div className="flex flex-col gap-2" aria-busy="true">
          <p className="sr-only">Loading…</p>
          {[0, 1, 2].map((n) => (
            <div key={n} className="h-12 animate-pulse rounded-xl bg-surface/70" aria-hidden="true" />
          ))}
        </div>
      )}

      {page && page.items.length === 0 && (
        <p
          data-testid="queue-empty"
          className="rounded-2xl bg-surface p-8 text-center text-slate-600 shadow-card ring-1 ring-slate-200/70"
        >
          {page.message ?? "No applications waiting"}
        </p>
      )}

      {page && page.items.length > 0 && (
        <>
          <div className="overflow-x-auto rounded-2xl bg-surface shadow-card ring-1 ring-slate-200/70">
          <table className="w-full text-left">
            <caption className="sr-only">Applications waiting for review</caption>
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide">
                <th scope="col" className="px-4 py-3">Applicant</th>
                <th scope="col" className="px-4 py-3">Amount</th>
                <th scope="col" className="px-4 py-3">Term</th>
                <th scope="col" className="px-4 py-3">Flags</th>
                <th scope="col" className="px-4 py-3">Waiting</th>
              </tr>
            </thead>
            <tbody>
              {page.items.map((item) => (
                <tr key={item.id} className="border-b border-slate-100 last:border-0 hover:bg-blue-50/50">
                  <td className="px-4 py-3">
                    <Link href={`/review/${item.id}`} className="font-semibold text-blue-800 hover:underline">
                      {item.applicant_name ?? "Unnamed applicant"}
                    </Link>
                  </td>
                  <td className="px-4 py-3">{formatVnd(item.amount_vnd)}</td>
                  <td className="px-4 py-3">{item.term_months} months</td>
                  <td className="px-4 py-3">
                    {item.flags.length === 0
                      ? "None"
                      : item.flags.map((f) => FLAG_LABELS[f] ?? f).join(", ")}
                  </td>
                  <td className="px-4 py-3">{formatAge(item.age_hours)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
          <div className="flex items-center gap-4">
            <button
              type="button"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              className={secondaryButtonClass}
            >
              Previous
            </button>
            <span className="text-sm">
              {offset + 1} to {offset + page.items.length} of {page.total}
            </span>
            <button
              type="button"
              disabled={offset + page.items.length >= page.total}
              onClick={() => setOffset(offset + PAGE_SIZE)}
              className={secondaryButtonClass}
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}
