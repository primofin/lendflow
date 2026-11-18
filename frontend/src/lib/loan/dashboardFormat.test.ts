import { describe, expect, it } from "vitest";

import {
  checkRange,
  formatDuration,
  formatRate,
  presetRange,
  statusLabel,
} from "./dashboardFormat";

describe("LF-019 dashboard formatting", () => {
  it("formats decision time in the unit a person would use", () => {
    expect(formatDuration(null)).toBe("No data");
    expect(formatDuration(0.5)).toBe("30 min");
    expect(formatDuration(3)).toBe("3.0 h");
    expect(formatDuration(47.9)).toBe("47.9 h");
    expect(formatDuration(72)).toBe("3.0 days");
  });

  it("formats the approval rate, and says so when there is none", () => {
    expect(formatRate(null)).toBe("No data");
    expect(formatRate(66.666)).toBe("66.7%");
  });

  it("builds presets that end today and include both ends", () => {
    const today = new Date("2026-11-18T10:00:00Z");

    expect(presetRange(7, today)).toEqual({ from: "2026-11-12", to: "2026-11-18" });
    expect(presetRange(1, today)).toEqual({ from: "2026-11-18", to: "2026-11-18" });
    expect(presetRange(30, today).from).toBe("2026-10-20");
  });

  it("checks a custom range the way the API does", () => {
    expect(checkRange("", "2026-01-01")).toMatch(/both/);
    expect(checkRange("2026-02-01", "2026-01-01")).toMatch(/not be after/);
    expect(checkRange("2024-01-01", "2026-01-01")).toMatch(/366/);
    expect(checkRange("2026-01-01", "2026-01-01")).toBeNull();
  });

  it("labels known statuses and passes unknown ones through", () => {
    expect(statusLabel("NEEDS_INFO")).toBe("Needs information");
    expect(statusLabel("SOMETHING_NEW")).toBe("SOMETHING_NEW");
  });
});
