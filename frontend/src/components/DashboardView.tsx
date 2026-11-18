"use client";

import { useEffect, useState } from "react";

import { apiRequest } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import type { Dashboard } from "@/lib/api/types";
import {
  checkRange,
  formatDuration,
  formatRate,
  presetRange,
  statusLabel,
} from "@/lib/loan/dashboardFormat";

import { FormError } from "./FormError";
import { buttonClass, inputClass } from "./FormField";

const PRESETS = [
  { days: 7, label: "Last 7 days" },
  { days: 30, label: "Last 30 days" },
  { days: 90, label: "Last 90 days" },
];

type Range = { from: string; to: string };

/** LF-019: for supervisors. One date range above everything; every figure below uses it, so the
 * numbers always agree. AI cost is not shown: the AI features are deferred (D-026). */
export function DashboardView() {
  const [range, setRange] = useState<Range>(() => presetRange(30, new Date()));
  const [preset, setPreset] = useState<number | null>(30);
  const [custom, setCustom] = useState<Range>(range);
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rangeError, setRangeError] = useState<string | null>(null);
  const [settled, setSettled] = useState<string | null>(null); // the range last answered
  const [asTable, setAsTable] = useState(false);

  useEffect(() => {
    let live = true;
    const key = `${range.from}|${range.to}`;
    apiRequest<Dashboard>(`/api/dashboard?${new URLSearchParams(range)}`)
      .then((value) => {
        if (!live) return;
        setData(value);
        setError(null);
      })
      .catch(
        (failure: unknown) =>
          live && setError(failure instanceof ApiError ? failure.message : "The dashboard could not be loaded."),
      )
      .finally(() => live && setSettled(key));
    return () => {
      live = false;
    };
  }, [range]);

  const loading = settled !== `${range.from}|${range.to}`;

  function choosePreset(days: number) {
    const next = presetRange(days, new Date());
    setPreset(days);
    setRange(next);
    setCustom(next);
    setRangeError(null);
  }

  function applyCustom() {
    const problem = checkRange(custom.from, custom.to);
    setRangeError(problem);
    if (problem) return;
    setPreset(null);
    setRange(custom);
  }

  return (
    <div className="flex flex-col gap-6">
      <fieldset className="flex flex-wrap items-end gap-3">
        <legend className="mb-2 text-sm font-medium">Date range</legend>
        {PRESETS.map((p) => (
          <button
            key={p.days}
            type="button"
            aria-pressed={preset === p.days}
            onClick={() => choosePreset(p.days)}
            className={`rounded border px-3 py-2 ${
              preset === p.days
                ? "border-blue-800 bg-blue-800 font-medium text-white"
                : "border-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
            }`}
          >
            {p.label}
          </button>
        ))}
        <label className="flex flex-col gap-1 text-sm">
          From
          <input
            type="date"
            value={custom.from}
            onChange={(e) => setCustom({ ...custom, from: e.target.value })}
            className={inputClass}
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          To
          <input
            type="date"
            value={custom.to}
            onChange={(e) => setCustom({ ...custom, to: e.target.value })}
            className={inputClass}
          />
        </label>
        <button type="button" onClick={applyCustom} className={buttonClass}>
          Apply range
        </button>
      </fieldset>
      <FormError message={rangeError} />
      <FormError message={error} />

      {data && (
        // Reloading keeps the previous render at reduced opacity: no skeleton, no layout jump.
        <div
          className={`flex flex-col gap-6 transition-opacity ${loading ? "opacity-60" : ""}`}
          aria-busy={loading}
        >
          <p className="text-sm" data-testid="range-shown">
            Showing {data.date_from} to {data.date_to}.
          </p>

          <section aria-label="Key figures" className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Tile label="Approval rate" value={formatRate(data.approval_rate_percent)} id="approval-rate"
              note={data.decided > 0 ? `${data.approved} of ${data.decided} decided` : "No decisions in range"} />
            <Tile label="Average decision time" value={formatDuration(data.avg_decision_hours)} id="decision-time"
              note="Submission to first decision" />
            <Tile label="Decided" value={String(data.decided)} id="decided"
              note={`${data.approved} approved, ${data.rejected} rejected`} />
            <Tile label="Overdue now" value={String(data.overdue_now)} id="overdue"
              note={data.overdue_now > 0 ? "Needs attention: past the supervisor limit" : "None past the limit"} />
          </section>

          <StatusChart data={data} asTable={asTable} onToggle={() => setAsTable((v) => !v)} />
        </div>
      )}
      {!data && !error && <p>Loading…</p>}
    </div>
  );
}

function Tile({ label, value, note, id }: { label: string; value: string; note: string; id: string }) {
  return (
    <div className="viz-root rounded-lg border border-[var(--viz-grid)] bg-[var(--viz-surface)] p-4" data-testid={`tile-${id}`}>
      <p className="text-sm text-[var(--viz-text-2)]">{label}</p>
      <p className="mt-1 text-3xl font-semibold text-[var(--viz-text)]" data-testid={`value-${id}`}>
        {value}
      </p>
      <p className="mt-1 text-xs text-[var(--viz-text-2)]">{note}</p>
    </div>
  );
}

function StatusChart({ data, asTable, onToggle }: { data: Dashboard; asTable: boolean; onToggle: () => void }) {
  const [hover, setHover] = useState<string | null>(null);
  const max = Math.max(1, ...data.by_status.map((s) => s.count));

  return (
    <section
      aria-labelledby="status-heading"
      className="viz-root rounded-lg border border-[var(--viz-grid)] bg-[var(--viz-surface)] p-4"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h2 id="status-heading" className="text-lg font-semibold text-[var(--viz-text)]">
            Applications by status
          </h2>
          <p className="text-sm text-[var(--viz-text-2)]">
            {data.total_applications} applications created in this range, by their status now.
          </p>
        </div>
        <button type="button" onClick={onToggle} aria-pressed={asTable} className="text-sm text-blue-800 underline dark:text-blue-300">
          {asTable ? "Show as chart" : "Show as table"}
        </button>
      </div>

      {asTable ? (
        <table className="mt-4 w-full text-left text-[var(--viz-text)]" data-testid="status-table">
          <thead>
            <tr className="text-sm text-[var(--viz-text-2)]">
              <th scope="col" className="py-1">Status</th>
              <th scope="col" className="py-1 text-right">Applications</th>
            </tr>
          </thead>
          <tbody>
            {data.by_status.map((s) => (
              <tr key={s.status} className="border-t border-[var(--viz-grid)]">
                <th scope="row" className="py-1 font-normal">{statusLabel(s.status)}</th>
                <td className="py-1 text-right">{s.count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <ul className="mt-4 flex flex-col gap-1" data-testid="status-chart">
          {data.by_status.map((s) => {
            const active = hover === s.status;
            return (
              <li
                key={s.status}
                data-testid={`bar-${s.status}`}
                tabIndex={0}
                onPointerEnter={() => setHover(s.status)}
                onPointerLeave={() => setHover(null)}
                onFocus={() => setHover(s.status)}
                onBlur={() => setHover(null)}
                className="relative grid grid-cols-[8.5rem_1fr_2.5rem] items-center gap-3 rounded py-1.5 outline-offset-2 focus-visible:outline-2 focus-visible:outline-blue-700"
              >
                <span className="text-sm text-[var(--viz-text-2)]">{statusLabel(s.status)}</span>
                <span className="relative block h-3.5">
                  {/* the track is a hairline baseline; the bar is anchored to it with a rounded data end */}
                  <span className="absolute inset-y-0 left-0 w-px bg-[var(--viz-grid)]" aria-hidden />
                  <span
                    className="absolute inset-y-0 left-px rounded-r-[4px] transition-colors"
                    style={{
                      width: `${(s.count / max) * 100}%`,
                      minWidth: s.count > 0 ? "4px" : 0,
                      background: active ? "var(--viz-bar-hover)" : "var(--viz-bar)",
                    }}
                    aria-hidden
                  />
                </span>
                <span className="text-right text-sm font-medium text-[var(--viz-text)]">{s.count}</span>
                {active && (
                  <span
                    role="tooltip"
                    className="pointer-events-none absolute right-12 top-1/2 z-10 -translate-y-1/2 rounded border border-[var(--viz-grid)] bg-[var(--viz-surface)] px-2 py-1 text-xs shadow"
                  >
                    <strong className="text-[var(--viz-text)]">{s.count}</strong>{" "}
                    <span className="text-[var(--viz-text-2)]">{statusLabel(s.status)}</span>
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
