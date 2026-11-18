/** LF-019 display helpers. Pure, so the rules are tested without a browser. */

export const STATUS_LABELS: Record<string, string> = {
  DRAFT: "Draft",
  SUBMITTED: "Submitted",
  IN_REVIEW: "In review",
  NEEDS_INFO: "Needs information",
  REFERRED: "Referred",
  APPROVED: "Approved",
  REJECTED: "Rejected",
};

export function statusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status;
}

/** Submission to first decision: minutes under an hour, hours under two days, then days. */
export function formatDuration(hours: number | null): string {
  if (hours === null) return "No data";
  if (hours < 1) return `${Math.round(hours * 60)} min`;
  if (hours < 48) return `${hours.toFixed(1)} h`;
  return `${(hours / 24).toFixed(1)} days`;
}

export function formatRate(percent: number | null): string {
  return percent === null ? "No data" : `${percent.toFixed(1)}%`;
}

/** UTC calendar date, the way the API reads from/to. */
export function isoDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

/** The last `days` days ending today, both ends inclusive. */
export function presetRange(days: number, today: Date): { from: string; to: string } {
  const start = new Date(today);
  start.setUTCDate(start.getUTCDate() - (days - 1));
  return { from: isoDate(start), to: isoDate(today) };
}

export const MAX_RANGE_DAYS = 366;

/** A specific message for a custom range the API would refuse, or null when it is fine. */
export function checkRange(from: string, to: string): string | null {
  if (!from || !to) return "Choose both a start and an end date.";
  if (from > to) return "The start date must not be after the end date.";
  const days = (Date.parse(to) - Date.parse(from)) / 86_400_000 + 1;
  if (days > MAX_RANGE_DAYS) return `Choose a range of at most ${MAX_RANGE_DAYS} days.`;
  return null;
}
