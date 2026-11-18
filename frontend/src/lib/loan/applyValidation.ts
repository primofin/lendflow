/** Client-side checks for the application form (LF-004). They only save a round trip: the
 * server stays the authority, and age rules are left to it on purpose. */

import type { ApplicationSubmit, IncomeType, LoanTerms } from "@/lib/api/types";

import { formatVnd, parseVnd } from "./money";

export type ApplyValues = {
  amount: string;
  term: string;
  purpose: string;
  fullName: string;
  dateOfBirth: string;
  nationalId: string;
  address: string;
  incomeType: IncomeType | "";
  monthlyIncome: string;
  existingDebt: string;
  consent: boolean;
};

export type ApplyField = Exclude<keyof ApplyValues, never>;
export type ApplyErrors = Partial<Record<ApplyField, string>>;

/** Server field paths (from a 422) to the form field they belong under. */
export const SERVER_FIELD: Record<string, ApplyField> = {
  amount_vnd: "amount",
  term_months: "term",
  purpose: "purpose",
  consent_accepted: "consent",
  "profile.full_name": "fullName",
  "profile.date_of_birth": "dateOfBirth",
  "profile.national_id": "nationalId",
  "profile.address": "address",
  "profile.income_type": "incomeType",
  "profile.monthly_income_vnd": "monthlyIncome",
  "profile.existing_debt_payment_vnd": "existingDebt",
};

export function validate(values: ApplyValues, terms: LoanTerms): ApplyErrors {
  const errors: ApplyErrors = {};
  const amount = parseVnd(values.amount);
  if (amount === null) {
    errors.amount = "Enter the amount as a number, for example 100,000,000.";
  } else if (amount < terms.amount_min_vnd || amount > terms.amount_max_vnd) {
    errors.amount = `The amount must be between ${formatVnd(terms.amount_min_vnd)} and ${formatVnd(terms.amount_max_vnd)}.`;
  }
  if (!terms.allowed_terms_months.includes(Number(values.term))) {
    errors.term = "Choose one of the available terms.";
  }
  if (
    amount !== null &&
    amount >= terms.purpose_required_from_vnd &&
    !values.purpose.trim()
  ) {
    errors.purpose = `A purpose is required for loans of ${formatVnd(terms.purpose_required_from_vnd)} or more.`;
  }
  if (!values.fullName.trim()) errors.fullName = "Enter your full name.";
  if (!values.dateOfBirth) errors.dateOfBirth = "Enter your date of birth.";
  if (!/^\d{12}$/.test(values.nationalId.trim())) {
    errors.nationalId = "The national ID must be exactly 12 digits.";
  }
  if (!values.address.trim()) errors.address = "Enter your address.";
  if (!values.incomeType) errors.incomeType = "Choose your income type.";
  if (parseVnd(values.monthlyIncome) === null) {
    errors.monthlyIncome = "Enter your monthly income as a number.";
  }
  if (values.existingDebt.trim() && parseVnd(values.existingDebt) === null) {
    errors.existingDebt = "Enter existing monthly debt payments as a number, or leave blank.";
  }
  if (!values.consent) {
    errors.consent = "You must accept the consent statement to submit your application.";
  }
  return errors;
}

/** Only call after validate() returned no errors. */
export function toPayload(values: ApplyValues, consentVersion: string): ApplicationSubmit {
  return {
    amount_vnd: parseVnd(values.amount) ?? 0,
    term_months: Number(values.term),
    purpose: values.purpose.trim() || null,
    profile: {
      full_name: values.fullName.trim(),
      date_of_birth: values.dateOfBirth,
      national_id: values.nationalId.trim(),
      address: values.address.trim(),
      income_type: values.incomeType as IncomeType,
      monthly_income_vnd: parseVnd(values.monthlyIncome) ?? 0,
      existing_debt_payment_vnd: parseVnd(values.existingDebt) ?? 0,
    },
    consent_accepted: values.consent,
    consent_version: consentVersion,
  };
}
