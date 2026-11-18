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
