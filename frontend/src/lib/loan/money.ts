/** Money is whole VND (integers), never floats. LF-003 / LF-004. */

/** "100,000,000", "100 000 000" and "100.000.000" all mean 100000000. Anything else is null. */
export function parseVnd(text: string): number | null {
  const compact = text.trim().replace(/[\s,.]/g, "");
  if (!/^\d+$/.test(compact) || compact.length > 15) return null;
  return Number(compact);
}

export function formatVnd(value: number): string {
  return `${new Intl.NumberFormat("en-US").format(value)} VND`;
}

/** "50000000" becomes "50,000,000" as the user types; anything that is not a digit is dropped. */
export function groupDigits(text: string): string {
  const digits = text.replace(/\D/g, "").slice(0, 15);
  return digits.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}
