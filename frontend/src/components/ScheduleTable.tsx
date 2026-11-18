"use client";

import { useEffect, useState } from "react";

import { apiRequest } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import type { Schedule } from "@/lib/api/types";
import { formatDate } from "@/lib/loan/dates";
import { formatVnd } from "@/lib/loan/money";

import { FormError } from "./FormError";

/** LF-014: the repayment plan of an approved loan: when each instalment is due and how much of
 * it is principal and interest. The schedule starts on the approval date (D-032). */
export function ScheduleTable({ applicationId }: { applicationId: string }) {
  const [schedule, setSchedule] = useState<Schedule | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    apiRequest<Schedule>(`/api/applications/${applicationId}/schedule`)
      .then((value) => live && setSchedule(value))
      .catch(
        (failure: unknown) =>
          live && setError(failure instanceof ApiError ? failure.message : "The schedule could not be loaded."),
      );
    return () => {
      live = false;
    };
  }, [applicationId]);

  return (
    <section aria-labelledby="schedule-heading" data-testid="schedule">
      <h2 id="schedule-heading" className="text-lg font-semibold">
        Repayment schedule
      </h2>
      <FormError message={error} />
      {!schedule && !error && <p className="mt-2">Loading…</p>}
      {schedule && (
        <>
          <p className="mt-2 text-sm" data-testid="schedule-summary">
            {formatVnd(schedule.monthly_payment_vnd)} a month at {schedule.annual_rate_percent}% a year, for{" "}
            {schedule.term_months} months. Interest in total: {formatVnd(schedule.total_interest_vnd)}. The first
            instalment is due {formatDate(schedule.instalments[0].due_date)}.
          </p>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[34rem] text-left text-sm" data-testid="schedule-table">
              <caption className="sr-only">Repayment schedule by instalment</caption>
              <thead>
                <tr className="border-b border-slate-300">
                  <th scope="col" className="py-1 pr-3">No.</th>
                  <th scope="col" className="py-1 pr-3">Due date</th>
                  <th scope="col" className="py-1 pr-3 text-right">Payment</th>
                  <th scope="col" className="py-1 pr-3 text-right">Principal</th>
                  <th scope="col" className="py-1 pr-3 text-right">Interest</th>
                  <th scope="col" className="py-1 text-right">Balance after</th>
                </tr>
              </thead>
              <tbody>
                {schedule.instalments.map((row) => (
                  <tr key={row.number} className="border-b border-slate-200">
                    <th scope="row" className="py-1 pr-3 font-normal">{row.number}</th>
                    <td className="py-1 pr-3">{formatDate(row.due_date)}</td>
                    <td className="py-1 pr-3 text-right">{formatVnd(row.payment_vnd)}</td>
                    <td className="py-1 pr-3 text-right">{formatVnd(row.principal_vnd)}</td>
                    <td className="py-1 pr-3 text-right">{formatVnd(row.interest_vnd)}</td>
                    <td className="py-1 text-right">{formatVnd(row.balance_vnd)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-2 text-xs text-slate-600">
            Payments are not recorded in this demo, so every instalment is shown as upcoming. The last
            instalment is adjusted by a few VND for rounding.
          </p>
        </>
      )}
    </section>
  );
}
