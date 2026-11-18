import { describe, expect, it } from "vitest";

import { formatVnd, parseVnd } from "./money";

describe("LF-003 parseVnd", () => {
  it("reads whole numbers with common separators", () => {
    expect(parseVnd("100000000")).toBe(100_000_000);
    expect(parseVnd("100,000,000")).toBe(100_000_000);
    expect(parseVnd(" 100 000 000 ")).toBe(100_000_000);
    expect(parseVnd("100.000.000")).toBe(100_000_000);
  });

  it("rejects text, signs, decimals with letters and empty input", () => {
    for (const bad of ["", "   ", "abc", "10M", "-5", "1e6", "12x4", "$100"]) {
      expect(parseVnd(bad)).toBeNull();
    }
  });

  it("rejects absurdly long input rather than losing precision", () => {
    expect(parseVnd("9".repeat(20))).toBeNull();
  });
});

describe("formatVnd", () => {
  it("groups thousands", () => {
    expect(formatVnd(4_896_311)).toBe("4,896,311 VND");
  });
});
