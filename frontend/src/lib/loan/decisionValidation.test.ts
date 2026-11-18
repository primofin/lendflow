import { describe, expect, it } from "vitest";

import { toDecisionPayload, validateDecision } from "./decisionValidation";
import type { DecisionValues } from "./decisionValidation";

const long = "Your income does not cover the monthly payment.";
const base: DecisionValues = { outcome: "", reasonCode: "", explanation: "", conditions: "" };

describe("LF-011 validateDecision (BR-13)", () => {
  it("needs an outcome", () => {
    expect(validateDecision(base).outcome).toBeDefined();
  });

  it("blocks a rejection without reason code, explanation or conditions", () => {
    const errors = validateDecision({ ...base, outcome: "reject" });
    expect(errors.reasonCode).toBeDefined();
    expect(errors.explanation).toBeDefined();
    expect(errors.conditions).toBeDefined();
  });

  it("blocks a rejection whose explanation is under 20 characters, counting trimmed text", () => {
    const values = { ...base, outcome: "reject" as const, reasonCode: "x", conditions: "c" };
    expect(validateDecision({ ...values, explanation: "  too short   " }).explanation).toBeDefined();
    expect(validateDecision({ ...values, explanation: "x".repeat(19) }).explanation).toBeDefined();
    expect(validateDecision({ ...values, explanation: "x".repeat(20) })).toEqual({});
  });

  it("accepts a complete rejection", () => {
    expect(
      validateDecision({ ...base, outcome: "reject", reasonCode: "low_income", explanation: long, conditions: "A co-borrower." }),
    ).toEqual({});
  });

  it("needs a message for a request for information, nothing else", () => {
    expect(validateDecision({ ...base, outcome: "request_info" }).explanation).toBeDefined();
    expect(validateDecision({ ...base, outcome: "request_info", explanation: long })).toEqual({});
  });

  it("approve and refer need nothing more", () => {
    expect(validateDecision({ ...base, outcome: "approve" })).toEqual({});
    expect(validateDecision({ ...base, outcome: "refer" })).toEqual({});
  });
});

describe("LF-011 toDecisionPayload", () => {
  const filled = { outcome: "approve" as const, reasonCode: "low_income", explanation: long, conditions: "c" };

  it("sends only what the outcome carries (the API refuses extras)", () => {
    expect(toDecisionPayload(filled, null)).toEqual({ outcome: "approve" });
    expect(toDecisionPayload({ ...filled, outcome: "refer" }, null)).toEqual({ outcome: "refer" });
    expect(toDecisionPayload({ ...filled, outcome: "request_info" }, null)).toEqual({
      outcome: "request_info",
      explanation: long,
    });
    expect(toDecisionPayload({ ...filled, outcome: "reject" }, null)).toEqual({
      outcome: "reject",
      reason_code: "low_income",
      explanation: long,
      conditions: "c",
    });
  });

  it("carries the id of the decision a correction replaces", () => {
    expect(toDecisionPayload(filled, "d1")).toEqual({ outcome: "approve", supersedes_id: "d1" });
  });
});
