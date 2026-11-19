import type { Tracker } from "@/lib/api/types";
import { formatDateTime } from "@/lib/loan/fileCheck";

/** LF-012: Received, Under assessment, Awaiting approval, Completed, each with its last update. */
export function TrackerPanel({ tracker }: { tracker: Tracker }) {
  return (
    <section aria-labelledby="tracker-heading">
      <h2 id="tracker-heading" className="text-lg font-semibold">
        Progress
      </h2>
      <ol className="mt-4 grid gap-3 sm:grid-cols-4">
        {tracker.steps.map((step, index) => {
          const done = step.state === "done";
          const current = step.state === "current";
          return (
            <li
              key={step.label}
              aria-current={current ? "step" : undefined}
              data-state={step.state}
              className={`rounded-xl border p-3 ${
                done
                  ? "border-emerald-200 bg-emerald-50"
                  : current
                    ? "border-blue-700 bg-blue-50 ring-2 ring-blue-200"
                    : "border-slate-200 text-slate-500"
              }`}
            >
              <span
                aria-hidden="true"
                className={`mb-2 grid h-6 w-6 place-items-center rounded-full text-xs font-bold ${
                  done ? "bg-emerald-600 text-white" : current ? "bg-blue-700 text-white" : "bg-slate-200 text-slate-600"
                }`}
              >
                {done ? "✓" : index + 1}
              </span>
              <span className={`block ${current ? "font-semibold" : "font-medium"}`}>{step.label}</span>
              <span className="block text-sm font-normal">
                {step.state === "done" && "Done"}
                {step.state === "current" && "In progress"}
                {step.state === "upcoming" && "Not yet"}
                {step.state === "skipped" && "Skipped"}
              </span>
              {step.updated_at && (
                <time dateTime={step.updated_at} className="block text-sm font-normal">
                  {formatDateTime(step.updated_at)}
                </time>
              )}
            </li>
          );
        })}
      </ol>
      {/* A request for information is shown in the needs-info panel instead. */}
      {tracker.decision && tracker.decision.outcome !== "request_info" && (
        <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4" data-testid="decision">
          <p className="font-medium">
            {tracker.decision.outcome === "approve" ? "Approved" : "Not approved"}
          </p>
          {tracker.decision.reason_label && <p>Reason: {tracker.decision.reason_label}</p>}
          {tracker.decision.explanation && <p>{tracker.decision.explanation}</p>}
          {tracker.decision.conditions && (
            <p>What could change the result: {tracker.decision.conditions}</p>
          )}
        </div>
      )}
    </section>
  );
}
