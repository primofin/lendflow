"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import type { FormEvent, ReactNode } from "react";

import { apiRequest } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import type { Application, Consent, LoanTerms } from "@/lib/api/types";
import { INCOME_TYPES } from "@/lib/api/types";
import { SERVER_FIELD, toPayload, validate } from "@/lib/loan/applyValidation";
import type { ApplyErrors, ApplyField, ApplyValues } from "@/lib/loan/applyValidation";
import { formatVnd } from "@/lib/loan/money";
import { useLoanTerms } from "@/lib/loan/useLoanTerms";

import { FormError } from "./FormError";
import { buttonClass, FormField, inputClass } from "./FormField";

const EMPTY: ApplyValues = {
  amount: "",
  term: "",
  purpose: "",
  fullName: "",
  dateOfBirth: "",
  nationalId: "",
  address: "",
  incomeType: "",
  monthlyIncome: "",
  existingDebt: "",
  consent: false,
};

const FOCUS_ORDER: ApplyField[] = [
  "amount", "term", "purpose", "fullName", "dateOfBirth", "nationalId", "address",
  "incomeType", "monthlyIncome", "existingDebt", "consent",
];

/** LF-004: the application form. Everything stays in this component's state until the single
 * submit request (D-009: no server drafts). Personal data is never put in the URL or storage. */
export function ApplyForm() {
  const { terms, failed } = useLoanTerms();
  const [consent, setConsent] = useState<Consent | null>(null);
  const [consentFailed, setConsentFailed] = useState(false);

  useEffect(() => {
    let live = true;
    apiRequest<Consent>("/api/consent/current")
      .then((value) => live && setConsent(value))
      .catch(() => live && setConsentFailed(true));
    return () => {
      live = false;
    };
  }, []);

  if (failed || consentFailed) {
    return <FormError message="The application form could not be loaded. Try again." />;
  }
  if (!terms || !consent) return <p>Loading…</p>;
  return <Form terms={terms} consent={consent} onConsentChanged={setConsent} />;
}

function Form({
  terms,
  consent,
  onConsentChanged,
}: {
  terms: LoanTerms;
  consent: Consent;
  onConsentChanged: (consent: Consent) => void;
}) {
  const router = useRouter();
  const params = useSearchParams();
  const [values, setValues] = useState<ApplyValues>(() => ({
    ...EMPTY,
    // Only the (non-personal) amount and term can arrive from the calculator link.
    amount: /^\d{1,15}$/.test(params.get("amount") ?? "") ? (params.get("amount") ?? "") : "",
    term: terms.allowed_terms_months.includes(Number(params.get("term")))
      ? (params.get("term") ?? "")
      : "",
  }));
  const [errors, setErrors] = useState<ApplyErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const refs = useRef<Partial<Record<ApplyField, HTMLElement | null>>>({});

  function set<K extends ApplyField>(key: K, value: ApplyValues[K]) {
    setValues((current) => ({ ...current, [key]: value }));
  }

  function focusFirst(found: ApplyErrors) {
    const first = FOCUS_ORDER.find((key) => found[key]);
    if (first) refs.current[first]?.focus();
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    const found = validate(values, terms);
    setErrors(found);
    if (Object.keys(found).length > 0) {
      setTimeout(() => focusFirst(found), 0);
      return;
    }
    setSending(true);
    try {
      const created = await apiRequest<Application>("/api/applications", {
        method: "POST",
        json: toPayload(values, consent.version),
      });
      // The page may stay mounted (hidden) after navigating, so drop the personal data.
      setValues(EMPTY);
      router.push(`/applications/${created.id}`);
    } catch (failure) {
      if (!(failure instanceof ApiError)) {
        setFormError("Something went wrong. Try again.");
      } else {
        const mapped: ApplyErrors = {};
        for (const [path, message] of Object.entries(failure.fields)) {
          const key = SERVER_FIELD[path];
          if (key) mapped[key] = message;
        }
        setErrors(mapped);
        if (Object.keys(mapped).length === 0) setFormError(failure.message);
        else setTimeout(() => focusFirst(mapped), 0);
        if (/consent text has changed/i.test(failure.message)) {
          set("consent", false);
          apiRequest<Consent>("/api/consent/current").then(onConsentChanged, () => undefined);
        }
      }
    } finally {
      setSending(false);
    }
  }

  const field = (
    key: ApplyField,
    label: string,
    render: (props: Record<string, unknown>) => ReactNode,
    hint?: string,
  ) => (
    <FormField id={key} label={label} hint={hint}>
      {(describedBy) => (
        <>
          {render({
            id: key,
            ref: (el: HTMLElement | null) => {
              refs.current[key] = el;
            },
            "aria-invalid": errors[key] ? true : undefined,
            "aria-describedby":
              [describedBy, errors[key] ? `${key}-error` : null].filter(Boolean).join(" ") ||
              undefined,
            className: `${inputClass} ${errors[key] ? "border-red-700" : ""}`,
          })}
          {errors[key] && (
            <p id={`${key}-error`} className="text-sm text-red-700">
              {errors[key]}
            </p>
          )}
        </>
      )}
    </FormField>
  );

  const text = (key: ApplyField, label: string, extra: Record<string, unknown> = {}, hint?: string) =>
    field(
      key,
      label,
      (props) => (
        <input
          {...props}
          {...extra}
          value={values[key] as string}
          onChange={(e) => set(key, e.target.value as never)}
        />
      ),
      hint,
    );

  const purposeRequired = (() => {
    const digits = values.amount.replace(/[\s,.]/g, "");
    return /^\d+$/.test(digits) && Number(digits) >= terms.purpose_required_from_vnd;
  })();

  return (
    <form onSubmit={submit} className="flex max-w-xl flex-col gap-8" noValidate>
      <FormError message={formError} />

      <fieldset className="flex flex-col gap-4">
        <legend className="mb-2 text-lg font-semibold">Loan</legend>
        {text("amount", "Loan amount (VND)", { inputMode: "numeric", autoComplete: "off" })}
        {field("term", "Term", (props) => (
          <select {...props} value={values.term} onChange={(e) => set("term", e.target.value)}>
            <option value="">Choose a term</option>
            {terms.allowed_terms_months.map((months) => (
              <option key={months} value={months}>
                {months} months
              </option>
            ))}
          </select>
        ))}
        {text(
          "purpose",
          purposeRequired ? "Purpose of the loan" : "Purpose of the loan (optional)",
          {},
          `Required for loans of ${formatVnd(terms.purpose_required_from_vnd)} or more.`,
        )}
      </fieldset>

      <fieldset className="flex flex-col gap-4">
        <legend className="mb-2 text-lg font-semibold">About you</legend>
        {text("fullName", "Full name", { autoComplete: "name" })}
        {text("dateOfBirth", "Date of birth", { type: "date", autoComplete: "bday" })}
        {text("nationalId", "National ID", { inputMode: "numeric", autoComplete: "off" }, "12 digits.")}
        {text("address", "Address", { autoComplete: "street-address" })}
        {field("incomeType", "Income type", (props) => (
          <select
            {...props}
            value={values.incomeType}
            onChange={(e) => set("incomeType", e.target.value as ApplyValues["incomeType"])}
          >
            <option value="">Choose an income type</option>
            {INCOME_TYPES.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
        ))}
        {text("monthlyIncome", "Monthly income (VND)", { inputMode: "numeric", autoComplete: "off" })}
        {text(
          "existingDebt",
          "Existing monthly debt payments (VND)",
          { inputMode: "numeric", autoComplete: "off" },
          "Leave blank if none.",
        )}
      </fieldset>

      <fieldset
        className={`flex flex-col gap-3 rounded border p-4 ${errors.consent ? "border-red-700 bg-red-50" : "border-slate-300"}`}
      >
        <legend className="px-1 text-lg font-semibold">Consent</legend>
        <p>{consent.statement}</p>
        <p className="font-medium">We will use your data for:</p>
        <ul className="list-disc pl-6">
          {consent.purposes.map((purpose) => (
            <li key={purpose.code}>{purpose.label}</li>
          ))}
        </ul>
        <p>
          Retention period: we keep your data for {consent.retention_months} months.
        </p>
        <label className="flex items-start gap-2">
          <input
            id="consent"
            type="checkbox"
            ref={(el) => {
              refs.current.consent = el;
            }}
            checked={values.consent}
            onChange={(e) => set("consent", e.target.checked)}
            aria-invalid={errors.consent ? true : undefined}
            aria-describedby={errors.consent ? "consent-error" : undefined}
            className="mt-1 size-5"
          />
          <span>I have read and accept this consent statement.</span>
        </label>
        {errors.consent && (
          <p id="consent-error" className="text-sm font-medium text-red-700">
            {errors.consent}
          </p>
        )}
      </fieldset>

      <button type="submit" disabled={sending} className={`${buttonClass} self-start`}>
        {sending ? "Submitting…" : "Submit application"}
      </button>
    </form>
  );
}
