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
