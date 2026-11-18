import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { setAccessToken } from "@/lib/api/client";

import { ScheduleTable } from "./ScheduleTable";

const fetchMock = vi.fn<typeof fetch>();

const schedule = {
  application_id: "a1",
  start_date: "2026-11-18",
  annual_rate_percent: 16,
  term_months: 3,
  monthly_payment_vnd: 3_400_000,
  total_paid_vnd: 10_200_005,
  total_interest_vnd: 200_005,
  instalments: [
    { number: 1, due_date: "2026-12-18", payment_vnd: 3_400_000, principal_vnd: 3_200_000, interest_vnd: 200_000, balance_vnd: 6_800_000 },
    { number: 2, due_date: "2027-01-18", payment_vnd: 3_400_000, principal_vnd: 3_300_000, interest_vnd: 100_000, balance_vnd: 3_500_000 },
    { number: 3, due_date: "2027-02-18", payment_vnd: 3_400_005, principal_vnd: 3_500_000, interest_vnd: -99_995, balance_vnd: 0 },
  ],
};

beforeEach(() => {
  fetchMock.mockReset();
  fetchMock.mockImplementation(async () => Response.json(schedule));
  vi.stubGlobal("fetch", fetchMock);
  setAccessToken("tok");
});

describe("LF-014 ScheduleTable", () => {
  it("lists every instalment with due date, payment, principal, interest and balance", async () => {
    render(<ScheduleTable applicationId="a1" />);

    const table = await screen.findByTestId("schedule-table");
    expect(String(fetchMock.mock.calls[0][0])).toBe("/api/applications/a1/schedule");
    const rows = within(table).getAllByRole("row");
    expect(rows).toHaveLength(4); // header + 3 instalments
    expect(rows[1]).toHaveTextContent("18 Dec 2026");
    expect(rows[1]).toHaveTextContent("3,400,000 VND");
    expect(rows[1]).toHaveTextContent("3,200,000 VND");
    expect(rows[1]).toHaveTextContent("200,000 VND");
    expect(rows[1]).toHaveTextContent("6,800,000 VND");
    expect(rows[3]).toHaveTextContent("0 VND");
  });

  it("summarises the monthly payment, the rate, the total interest and the first due date", async () => {
    render(<ScheduleTable applicationId="a1" />);

    const summary = await screen.findByTestId("schedule-summary");
    expect(summary).toHaveTextContent("3,400,000 VND a month at 16% a year, for 3 months");
    expect(summary).toHaveTextContent("200,005 VND");
    expect(summary).toHaveTextContent("first instalment is due 18 Dec 2026");
  });

  it("says that no payments are recorded", async () => {
    render(<ScheduleTable applicationId="a1" />);

    expect(await screen.findByText(/Payments are not recorded/)).toBeInTheDocument();
  });

  it("shows the server's refusal", async () => {
    fetchMock.mockImplementation(async () =>
      Response.json({ detail: "Only an approved application has a repayment schedule" }, { status: 409 }),
    );
    render(<ScheduleTable applicationId="a1" />);

    expect(await screen.findByText("Only an approved application has a repayment schedule")).toBeInTheDocument();
    expect(screen.queryByTestId("schedule-table")).not.toBeInTheDocument();
  });
});
