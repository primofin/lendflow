import { describe, expect, it } from "vitest";

import { formatDate } from "./dates";

describe("formatDate", () => {
  it("shows a calendar date the same way in any time zone", () => {
    expect(formatDate("2026-12-18")).toBe("18 Dec 2026");
    expect(formatDate("2027-01-01")).toBe("1 Jan 2027");
  });
});
