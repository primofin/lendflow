/** A calendar date from the API ("2026-12-18") shown the same way for everyone, in UTC. */
export function formatDate(iso: string): string {
  return new Date(`${iso}T00:00:00Z`).toLocaleDateString("en-GB", { dateStyle: "medium", timeZone: "UTC" });
}
