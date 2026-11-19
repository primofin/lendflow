"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { apiRequest } from "@/lib/api/client";
import type { CalculatorQuote } from "@/lib/api/types";
import { formatVnd } from "@/lib/loan/money";
import { useLoanTerms } from "@/lib/loan/useLoanTerms";

import { buttonClass } from "./FormField";

const STEP = 1_000_000;

/** Landing-page estimate: drag the sliders, see the monthly payment. Same API as the calculator. */
export function HeroCalculator() {
  const { terms } = useLoanTerms();
  const [amount, setAmount] = useState(100_000_000);
  const [term, setTerm] = useState(24);
  const [quote, setQuote] = useState<CalculatorQuote | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => {
      const query = new URLSearchParams({ amount_vnd: String(amount), term_months: String(term) });
      apiRequest<CalculatorQuote>(`/api/calculator?${query}`, { signal: controller.signal })
        .then(setQuote)
        .catch(() => undefined);
    }, 200);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [amount, term]);

  if (!terms) return <div className="h-80 animate-pulse rounded-3xl bg-white/60" aria-hidden="true" />;
  const apply = new URLSearchParams({ amount: String(amount), term: String(term) });

  return (
    <div className="rounded-3xl bg-white p-6 shadow-card ring-1 ring-slate-200/70" data-testid="hero-calculator">
      <p className="text-sm font-medium text-slate-500">Quick estimate</p>
      <p className="mt-1 text-4xl font-bold tracking-tight">{formatVnd(amount)}</p>
      <input
        type="range"
        aria-label="Loan amount"
        min={terms.amount_min_vnd}
        max={terms.amount_max_vnd}
        step={STEP}
        value={amount}
        onChange={(e) => setAmount(Number(e.target.value))}
        className="mt-3 w-full accent-blue-700"
      />
      <div className="mt-5 flex flex-wrap gap-2" role="group" aria-label="Term">
        {terms.allowed_terms_months.map((months) => (
          <button
            key={months}
            type="button"
            aria-pressed={term === months}
            onClick={() => setTerm(months)}
            className={`rounded-full px-4 py-1.5 text-sm font-semibold transition ${
              term === months ? "bg-blue-700 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            {months} mo
          </button>
        ))}
      </div>
      <div className="mt-6 rounded-2xl bg-blue-50 p-4">
        <p className="text-sm text-slate-600">You would pay about</p>
        <p className="text-2xl font-bold text-blue-900" data-testid="hero-monthly">
          {quote ? formatVnd(quote.monthly_payment_vnd) : "…"}
          <span className="text-base font-medium text-slate-600"> a month</span>
        </p>
        {quote && (
          <p className="mt-1 text-sm text-slate-600">
            {quote.annual_rate_percent}% a year · {formatVnd(quote.total_interest_vnd)} total interest
          </p>
        )}
      </div>
      <Link href={`/apply?${apply}`} className={`${buttonClass} mt-5 w-full`}>
        Apply with these terms
      </Link>
      <p className="mt-2 text-center text-xs text-slate-500">An estimate, not an offer.</p>
    </div>
  );
}
