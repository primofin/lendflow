import { describe, expect, it } from "vitest";

import { checkImportFile, errorReportCsv, IMPORT_MAX_BYTES } from "./importReport";

describe("LF-013 import report", () => {
  it("lists each row number, type and reason", () => {
    const csv = errorReportCsv([
      { row: 3, kind: "invalid", message: "national_id: National ID must be 12 digits" },
      { row: 5, kind: "duplicate", message: "Duplicate of row 2 in this file; skipped" },
    ]);

    expect(csv).toBe(
      [
        "row,type,reason",
        "3,invalid,national_id: National ID must be 12 digits",
        "5,duplicate,Duplicate of row 2 in this file; skipped",
        "",
      ].join("\r\n"),
    );
  });

  it("quotes commas and quotes, and neutralises leading formula characters", () => {
    const csv = errorReportCsv([
      { row: 2, kind: "invalid", message: 'amount: "x", y' },
      { row: 3, kind: "invalid", message: "=HYPERLINK(1)" },
    ]);

    expect(csv).toContain('2,invalid,"amount: ""x"", y"');
    expect(csv).toContain("3,invalid,'=HYPERLINK(1)");
  });

  it("refuses a non-CSV name and a file over 2 MB, and accepts one at the limit", () => {
    expect(checkImportFile({ name: "people.xlsx", size: 10 })).toMatch(/\.csv/);
    expect(checkImportFile({ name: "people.csv", size: IMPORT_MAX_BYTES + 1 })).toMatch(/2 MB/);
    expect(checkImportFile({ name: "PEOPLE.CSV", size: IMPORT_MAX_BYTES })).toBeNull();
  });
});
