import { describe, expect, it } from "vitest";

import { ApiError, errorFromResponse, fieldIssues, formatDetail } from "./errors";

describe("formatDetail", () => {
  it("returns a string detail unchanged", () => {
    expect(formatDetail("National ID must be 12 digits", "fallback")).toBe(
      "National ID must be 12 digits",
    );
  });

  it("joins validation issues with their field and drops framework prefixes", () => {
    const detail = [
      { loc: ["body", "profile", "national_id"], msg: "Value error, National ID must be 12 digits" },
      { loc: ["body", "term_months"], msg: "Term must be one of 6, 12" },
    ];
    expect(formatDetail(detail, "fallback")).toBe(
      "profile.national_id: National ID must be 12 digits; term_months: Term must be one of 6, 12",
    );
  });

  it("falls back when there is nothing readable", () => {
    expect(formatDetail(undefined, "fallback")).toBe("fallback");
    expect(formatDetail([{ loc: ["body"] }], "fallback")).toBe("fallback");
    expect(formatDetail("   ", "fallback")).toBe("fallback");
  });
});

describe("errorFromResponse", () => {
  it("uses the backend's message and keeps the status", async () => {
    const response = Response.json({ detail: "Supervisor approval required" }, { status: 403 });
    const error = await errorFromResponse(response);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(403);
    expect(error.message).toBe("Supervisor approval required");
  });

  it("gives an actionable message when the body is not JSON", async () => {
    const error = await errorFromResponse(new Response("<html>Bad gateway</html>", { status: 502 }));
    expect(error.status).toBe(502);
    expect(error.message).toContain("502");
    expect(error.message).toContain("Try again");
  });
});

describe("LF-004 fieldIssues", () => {
  it("keys messages by field path and drops body and query prefixes", () => {
    expect(
      fieldIssues([
        { loc: ["body", "profile", "national_id"], msg: "Value error, bad id" },
        { loc: ["body", "amount_vnd"], msg: "too small" },
        { loc: ["body"], msg: "whole body problem" },
      ]),
    ).toEqual({ "profile.national_id": "bad id", amount_vnd: "too small" });
  });

  it("is empty for a plain string detail", () => {
    expect(fieldIssues("nope")).toEqual({});
  });
});
