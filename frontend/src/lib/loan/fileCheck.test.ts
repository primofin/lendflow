import { describe, expect, it } from "vitest";

import type { UploadNotice } from "@/lib/api/types";

import { checkFile } from "./fileCheck";

const notice: UploadNotice = {
  notice: "demo",
  allowed_types: ["image/jpeg", "image/png", "application/pdf"],
  max_size_mb: 5,
};

function file(type: string, size: number, name = "doc") {
  const f = new File(["x"], name, { type });
  Object.defineProperty(f, "size", { value: size });
  return f;
}

describe("LF-005 checkFile", () => {
  it("accepts JPG, PNG and PDF up to the limit, including exactly 5 MB", () => {
    for (const type of notice.allowed_types) {
      expect(checkFile(file(type, 5 * 1024 * 1024), notice)).toBeNull();
    }
  });

  it("names the problem and the fix for an oversized file", () => {
    const message = checkFile(file("image/png", 5 * 1024 * 1024 + 1, "scan.png"), notice);
    expect(message).toMatch(/"scan.png" is 5.0 MB, over the 5 MB limit/);
    expect(message).toMatch(/Choose a smaller file/);
  });

  it("refuses unsupported types and empty files", () => {
    expect(checkFile(file("application/zip", 10, "a.zip"), notice)).toMatch(/not a JPG, PNG or PDF/);
    expect(checkFile(file("image/gif", 10), notice)).toMatch(/not a JPG, PNG or PDF/);
    expect(checkFile(file("image/png", 0), notice)).toMatch(/empty/);
  });
});
