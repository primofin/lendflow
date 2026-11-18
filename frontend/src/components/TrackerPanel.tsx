import type { Tracker } from "@/lib/api/types";
import { formatDateTime } from "@/lib/loan/fileCheck";

/** LF-012: Received, Under assessment, Awaiting approval, Completed, each with its last update. */
export function TrackerPanel({ tracker }: { tracker: Tracker }) {
  return (
    <section aria-labelledby="tracker-heading">
      <h2 id="tracker-heading" className="text-lg font-semibold">
        Progress
      </h2>
      <ol className="mt-3 grid gap-3 sm:grid-cols-4">
        {tracker.steps.map((step) => {
          const style =
            step.state === "done"
              ? "border-green-700 bg-green-50"
              : step.state === "current"
                ? "border-blue-800 bg-blue-50 font-semibold"
                : "border-slate-300 text-slate-600";
          return (
            <li
              key={step.label}
              aria-current={step.state === "current" ? "step" : undefined}
              data-state={step.state}
              className={`rounded border-2 p-3 ${style}`}
            >
              <span className="block">{step.label}</span>
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
        <div className="mt-4 rounded border border-slate-300 p-3" data-testid="decision">
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
