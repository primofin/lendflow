"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { apiRequest } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import type { CalculatorQuote, LoanTerms } from "@/lib/api/types";
import { formatVnd, parseVnd } from "@/lib/loan/money";
import { useLoanTerms } from "@/lib/loan/useLoanTerms";

import { FormError } from "./FormError";
import { buttonClass, FormField, inputClass } from "./FormField";

const DEBOUNCE_MS = 300;

/** The message under the amount field, or null when the amount can be sent to the API. */
export function amountProblem(text: string, terms: LoanTerms): string | null {
  const amount = parseVnd(text);
  if (amount === null) return "Enter the amount as a number, for example 100,000,000.";
  if (amount < terms.amount_min_vnd || amount > terms.amount_max_vnd) {
    return `The amount must be between ${formatVnd(terms.amount_min_vnd)} and ${formatVnd(terms.amount_max_vnd)}.`;
  }
  return null;
}

/** LF-003: public calculator. Recalculates as the user types; the button does the same on demand. */
export function CalculatorForm() {
  const { terms, failed } = useLoanTerms();
  const [amountText, setAmountText] = useState("100,000,000");
  const [term, setTerm] = useState<number | null>(null);
  const [requested, setRequested] = useState(0); // bumped by the button to force a refresh
  const [quote, setQuote] = useState<CalculatorQuote | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);

  const chosenTerm =
    term ?? (terms?.allowed_terms_months.includes(24) ? 24 : (terms?.allowed_terms_months[0] ?? null));
  const problem = terms ? amountProblem(amountText, terms) : null;
  const amount = parseVnd(amountText);
  const ready = terms !== null && problem === null && amount !== null && chosenTerm !== null;

  useEffect(() => {
    if (!ready) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      const query = new URLSearchParams({
        amount_vnd: String(amount),
        term_months: String(chosenTerm),
      });
      apiRequest<CalculatorQuote>(`/api/calculator?${query}`, {
        signal: controller.signal,
      })
        .then((result) => {
          setQuote(result);
          setApiError(null);
        })
        .catch((failure: unknown) => {
          if (controller.signal.aborted) return; // a newer request replaced this one
          setQuote(null);
          setApiError(
            failure instanceof ApiError
              ? failure.message
              : "The calculator is unavailable. Try again.",
          );
        });
    }, DEBOUNCE_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [ready, amount, chosenTerm, requested]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setRequested((n) => n + 1);
  }

  if (failed) return <FormError message="The loan options could not be loaded. Try again." />;
  if (!terms) return <p>Loading…</p>;

  const shown = ready ? quote : null;
  const applyQuery = new URLSearchParams({
    amount: String(amount ?? ""),
    term: String(chosenTerm ?? ""),
  });

  return (
    <div className="flex flex-col gap-6">
      <form onSubmit={submit} className="flex max-w-sm flex-col gap-4" noValidate>
        <FormField id="amount" label="Loan amount (VND)">
          {(describedBy) => (
            <>
              <input
                id="amount"
                inputMode="numeric"
                autoComplete="off"
                value={amountText}
                onChange={(e) => setAmountText(e.target.value)}
                aria-invalid={problem !== null}
                aria-describedby={[describedBy, problem ? "amount-error" : null]
                  .filter(Boolean)
                  .join(" ") || undefined}
                className={`${inputClass} ${problem ? "border-red-700" : ""}`}
              />
              {problem && (
                <p id="amount-error" role="alert" className="text-sm text-red-700">
                  {problem}
                </p>
              )}
            </>
          )}
        </FormField>
        <FormField id="term" label="Term">
          {() => (
            <select
              id="term"
              value={chosenTerm ?? ""}
              onChange={(e) => setTerm(Number(e.target.value))}
              className={inputClass}
            >
              {terms.allowed_terms_months.map((months) => (
                <option key={months} value={months}>
                  {months} months
                </option>
              ))}
            </select>
          )}
        </FormField>
        <button type="submit" className={buttonClass}>
          Calculate
        </button>
      </form>

      <FormError message={apiError} />

      {shown && (
        <section
          aria-live="polite"
          aria-labelledby="result-heading"
          className="max-w-md rounded border border-slate-300 bg-slate-50 p-4"
        >
          <h2 id="result-heading" className="text-lg font-semibold">
            Your estimate
          </h2>
          <dl className="mt-3 grid grid-cols-[1fr_auto] gap-x-4 gap-y-1">
            <dt>Monthly payment</dt>
            <dd data-testid="monthly">{formatVnd(shown.monthly_payment_vnd)}</dd>
            <dt>Total repaid</dt>
            <dd data-testid="total">{formatVnd(shown.total_repaid_vnd)}</dd>
            <dt>Total interest</dt>
            <dd data-testid="interest">{formatVnd(shown.total_interest_vnd)}</dd>
          </dl>
          <p className="mt-3 text-sm text-slate-700">
            Calculated with the {shown.method} method at {shown.annual_rate_percent}% a year. This is an
            estimate, not an offer.
          </p>
          <Link
            href={`/apply?${applyQuery}`}
            className="mt-3 inline-block text-blue-800 underline"
          >
            Apply with these terms
          </Link>
        </section>
      )}
    </div>
  );
}
