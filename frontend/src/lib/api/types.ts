/** Friendly names for generated API types (src/lib/api/schema.d.ts, from the backend OpenAPI). */

import type { components } from "./schema";

type Schemas = components["schemas"];

export type User = Schemas["UserOut"];
export type Role = User["role"];
export type AdminUser = Schemas["UserAdminOut"];
export type UserCreate = Schemas["UserCreateIn"];

export const ROLES: Role[] = ["borrower", "officer", "supervisor"];

export type LoanTerms = Schemas["LoanTermsOut"];
export type CalculatorQuote = Schemas["CalculatorQuoteOut"];
export type Consent = Schemas["ConsentOut"];
export type ApplicationSubmit = Schemas["ApplicationSubmitIn"];
export type Application = Schemas["ApplicationOut"];
export type IncomeType = Schemas["IncomeType"];

export const INCOME_TYPES: { value: IncomeType; label: string }[] = [
  { value: "salaried", label: "Salaried" },
  { value: "freelance", label: "Freelance" },
  { value: "self_employed", label: "Self-employed" },
  { value: "rental", label: "Rental income" },
  { value: "other", label: "Other" },
];

export type Tracker = Schemas["TrackerOut"];
export type Checklist = Schemas["ChecklistOut"];
export type ChecklistRequirement = Schemas["ChecklistRequirementOut"];
export type UploadedDocument = Schemas["DocumentOut"];
export type UploadNotice = Schemas["UploadNoticeOut"];
export type DocType = Schemas["DocType"];

export const DOC_TYPE_LABELS: Record<DocType, string> = {
  national_id: "National ID",
  labour_contract: "Labour contract",
  employer_confirmation: "Employer confirmation",
  payslips: "Payslips",
  bank_statements: "Bank statements",
  tax_return: "Tax return",
  invoices_contracts: "Invoices or contracts",
  business_licence: "Business licence",
  rental_contract: "Rental contract",
  proof_of_ownership: "Proof of ownership",
  other: "Other document",
};

export function docTypeLabel(type: string): string {
  return DOC_TYPE_LABELS[type as DocType] ?? type;
}

export type QueuePage = Schemas["QueuePageOut"];
export type QueueItem = Schemas["QueueItemOut"];
export type Review = Schemas["ReviewOut"];

export const FLAG_LABELS: Record<string, string> = {
  exception: "Exception",
  high_dti: "High DTI",
  fast_track: "Fast-track",
};

export type DecisionOutcome = Schemas["DecisionIn"]["outcome"];
export type DecisionEntry = Schemas["DecisionOut"];
export type DecisionSubmit = Schemas["DecisionIn"];
export type ReasonCode = Schemas["ReasonCodeOut"];

export const OUTCOME_LABELS: Record<DecisionOutcome, string> = {
  approve: "Approve",
  reject: "Reject",
  request_info: "Request information",
  refer: "Refer to a supervisor",
};

export const OUTCOME_RESULT: Record<DecisionOutcome, string> = {
  approve: "Approved",
  reject: "Rejected",
  request_info: "Information requested",
  refer: "Referred to a supervisor",
};

export type CicCheck = Schemas["CicCheckOut"];

export const CIC_FLAG_LABELS: Record<NonNullable<CicCheck["flag"]>, string> = {
  pass: "Passes",
  attention: "Needs attention",
  recommend_reject: "Recommend reject (a person decides)",
};
