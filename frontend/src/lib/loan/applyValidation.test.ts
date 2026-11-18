import { describe, expect, it } from "vitest";

import type { LoanTerms } from "@/lib/api/types";

import { toPayload, validate } from "./applyValidation";
import type { ApplyValues } from "./applyValidation";

const terms: LoanTerms = {
  allowed_terms_months: [6, 12, 24],
  amount_min_vnd: 1_000_000,
  amount_max_vnd: 500_000_000,
  purpose_required_from_vnd: 100_000_000,
};

const good: ApplyValues = {
  amount: "50,000,000",
  term: "12",
  purpose: "",
  fullName: "Nguyen Test",
  dateOfBirth: "1990-05-01",
  nationalId: "012345678901",
  address: "1 Example Street",
  incomeType: "salaried",
  monthlyIncome: "20,000,000",
  existingDebt: "",
  consent: true,
};

describe("LF-004 validate", () => {
  it("accepts a complete small loan with no purpose", () => {
    expect(validate(good, terms)).toEqual({});
  });

  it("requires a purpose from the configured threshold", () => {
    expect(validate({ ...good, amount: "100,000,000" }, terms).purpose).toMatch(/required/);
    expect(validate({ ...good, amount: "99,999,999" }, terms).purpose).toBeUndefined();
  });

  it("refuses amounts outside the range", () => {
    expect(validate({ ...good, amount: "999,999" }, terms).amount).toBeDefined();
    expect(validate({ ...good, amount: "500,000,001" }, terms).amount).toBeDefined();
    expect(validate({ ...good, amount: "abc" }, terms).amount).toBeDefined();
  });

  it("refuses a term that is not offered", () => {
    expect(validate({ ...good, term: "7" }, terms).term).toBeDefined();
  });

  it("requires a 12 digit national id", () => {
    for (const id of ["", "12345", "01234567890a", "0123456789012"]) {
      expect(validate({ ...good, nationalId: id }, terms).nationalId).toBeDefined();
    }
  });

  it("blocks submission without consent", () => {
    expect(validate({ ...good, consent: false }, terms).consent).toMatch(/must accept/);
  });
});

describe("LF-004 toPayload", () => {
  it("sends integers, a null purpose and the consent version", () => {
    const payload = toPayload(good, "v1");
    expect(payload).toMatchObject({
      amount_vnd: 50_000_000,
      term_months: 12,
      purpose: null,
      consent_accepted: true,
      consent_version: "v1",
    });
    expect(payload.profile.monthly_income_vnd).toBe(20_000_000);
    expect(payload.profile.existing_debt_payment_vnd).toBe(0);
  });
});
