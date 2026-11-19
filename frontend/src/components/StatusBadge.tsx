const STYLES: Record<string, string> = {
  DRAFT: "bg-slate-100 text-slate-700",
  SUBMITTED: "bg-blue-50 text-blue-800",
  IN_REVIEW: "bg-blue-50 text-blue-800",
  NEEDS_INFO: "bg-amber-100 text-amber-900",
  REFERRED: "bg-violet-100 text-violet-800",
  APPROVED: "bg-emerald-100 text-emerald-800",
  REJECTED: "bg-rose-100 text-rose-800",
};

/** The status as a coloured pill. The text stays the raw status so tests and screen readers match. */
export function StatusBadge({ status, testId }: { status: string; testId?: string }) {
  return (
    <span
      data-testid={testId}
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold tracking-wide ${STYLES[status] ?? "bg-slate-100 text-slate-700"}`}
    >
      {status}
    </span>
  );
}
