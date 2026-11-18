import type { ImportIssue } from "@/lib/api/types";

/** The limit the server enforces (IMPORT_MAX_BYTES); checked here only to save a round trip. */
export const IMPORT_MAX_BYTES = 2 * 1024 * 1024;

export function checkImportFile(file: { name: string; size: number }): string | null {
  if (!file.name.toLowerCase().endsWith(".csv")) return "Choose a .csv file.";
  if (file.size > IMPORT_MAX_BYTES) return "The file is too large. CSV files must be 2 MB or smaller.";
  return null;
}

function cell(value: string | number): string {
  const text = String(value);
  // Quote when needed; a leading = + - @ is neutralised so a spreadsheet never runs it as a formula.
  const safe = /^[=+\-@]/.test(text) ? `'${text}` : text;
  return /[",\r\n]/.test(safe) ? `"${safe.replace(/"/g, '""')}"` : safe;
}

/** LF-013 AC2: the downloadable error report, one line per skipped or invalid row. */
export function errorReportCsv(issues: ImportIssue[]): string {
  const lines = ["row,type,reason", ...issues.map((i) => [i.row, i.kind, i.message].map(cell).join(","))];
  return lines.join("\r\n") + "\r\n";
}
