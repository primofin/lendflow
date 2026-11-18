/** Errors from the API. The backend sends `{detail: string}` or, for invalid input,
 * `{detail: [{loc, msg}]}`; both become one readable sentence for the user. */

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    /** Per-field messages from a validation failure, keyed by the field path ("profile.national_id"). */
    public readonly fields: Record<string, string> = {},
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type FieldIssue = { loc?: unknown; msg?: unknown };

function describeIssue(issue: FieldIssue): string | null {
  if (typeof issue.msg !== "string") return null;
  const msg = issue.msg.replace(/^Value error, /, "");
  const path = Array.isArray(issue.loc)
    ? issue.loc.filter((part) => part !== "body" && part !== "query").join(".")
    : "";
  return path ? `${path}: ${msg}` : msg;
}

/** Field path to message for each issue that names a field, so forms can show it under the input. */
export function fieldIssues(detail: unknown): Record<string, string> {
  const out: Record<string, string> = {};
  if (!Array.isArray(detail)) return out;
  for (const item of detail as FieldIssue[]) {
    if (typeof item.msg !== "string" || !Array.isArray(item.loc)) continue;
    const path = item.loc
      .filter((part) => part !== "body" && part !== "query")
      .join(".");
    if (path && !(path in out)) out[path] = item.msg.replace(/^Value error, /, "");
  }
  return out;
}

export function formatDetail(detail: unknown, fallback: string): string {
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const lines = detail
      .map((item) => describeIssue(item as FieldIssue))
      .filter((line): line is string => line !== null);
    if (lines.length > 0) return lines.join("; ");
  }
  return fallback;
}

export async function errorFromResponse(response: Response): Promise<ApiError> {
  const fallback = `The request failed (${response.status}). Try again.`;
  try {
    const body: unknown = await response.json();
    const detail = (body as { detail?: unknown }).detail;
    return new ApiError(
      response.status,
      formatDetail(detail, fallback),
      fieldIssues(detail),
    );
  } catch {
    return new ApiError(response.status, fallback);
  }
}
