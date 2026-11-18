import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { setAccessToken } from "@/lib/api/client";
import type { Dashboard } from "@/lib/api/types";

import { DashboardView } from "./DashboardView";

const fetchMock = vi.fn<typeof fetch>();

function dashboard(over: Partial<Dashboard> = {}): Dashboard {
  return {
    date_from: "2026-10-20",
    date_to: "2026-11-18",
    total_applications: 7,
    by_status: [
      { status: "DRAFT", count: 0 },
      { status: "SUBMITTED", count: 1 },
      { status: "IN_REVIEW", count: 4 },
      { status: "NEEDS_INFO", count: 0 },
      { status: "REFERRED", count: 0 },
      { status: "APPROVED", count: 1 },
      { status: "REJECTED", count: 1 },
    ],
    decided: 2,
    approved: 1,
    rejected: 1,
    approval_rate_percent: 50,
    avg_decision_hours: 3,
    overdue_now: 2,
    ...over,
  };
}

function lastQuery(): URLSearchParams {
  return new URLSearchParams(String(fetchMock.mock.calls.at(-1)?.[0]).split("?")[1]);
}

beforeEach(() => {
  fetchMock.mockReset();
  fetchMock.mockImplementation(async () => Response.json(dashboard()));
  vi.stubGlobal("fetch", fetchMock);
  setAccessToken("tok");
});

describe("LF-019 DashboardView", () => {
  it("shows the key figures and the status chart for the default 30 days", async () => {
    render(<DashboardView />);

    expect(await screen.findByTestId("value-approval-rate")).toHaveTextContent("50.0%");
    expect(screen.getByTestId("tile-approval-rate")).toHaveTextContent("1 of 2 decided");
    expect(screen.getByTestId("value-decision-time")).toHaveTextContent("3.0 h");
    expect(screen.getByTestId("value-decided")).toHaveTextContent("2");
    expect(screen.getByTestId("value-overdue")).toHaveTextContent("2");
    expect(screen.getByTestId("tile-overdue")).toHaveTextContent("Needs attention");
    expect(screen.getByTestId("range-shown")).toHaveTextContent("2026-10-20 to 2026-11-18");
    const chart = screen.getByTestId("status-chart");
    expect(within(chart).getAllByRole("listitem")).toHaveLength(7); // zeros are kept
    expect(screen.getByTestId("bar-IN_REVIEW")).toHaveTextContent("In review");
    expect(screen.getByTestId("bar-IN_REVIEW")).toHaveTextContent("4");
    const query = lastQuery();
    expect(query.get("from")).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(query.get("to")).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it("says 'No data' rather than 0 when nothing was decided", async () => {
    fetchMock.mockImplementation(async () =>
      Response.json(dashboard({ decided: 0, approved: 0, rejected: 0, approval_rate_percent: null, avg_decision_hours: null, overdue_now: 0 })),
    );
    render(<DashboardView />);

    expect(await screen.findByTestId("value-approval-rate")).toHaveTextContent("No data");
    expect(screen.getByTestId("value-decision-time")).toHaveTextContent("No data");
    expect(screen.getByTestId("tile-approval-rate")).toHaveTextContent("No decisions in range");
    expect(screen.getByTestId("tile-overdue")).toHaveTextContent("None past the limit");
  });

  it("re-queries every figure when a preset is chosen", async () => {
    render(<DashboardView />);
    await screen.findByTestId("value-approval-rate");

    await userEvent.click(screen.getByRole("button", { name: "Last 7 days" }));

    await waitFor(() => {
      const q = lastQuery();
      const days = (Date.parse(q.get("to")!) - Date.parse(q.get("from")!)) / 86_400_000 + 1;
      expect(days).toBe(7);
    });
    expect(screen.getByRole("button", { name: "Last 7 days" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Last 30 days" })).toHaveAttribute("aria-pressed", "false");
  });

  it("applies a custom range, and refuses a bad one without sending it", async () => {
    render(<DashboardView />);
    await screen.findByTestId("value-approval-rate");
    const calls = fetchMock.mock.calls.length;

    const from = screen.getByLabelText("From");
    const to = screen.getByLabelText("To");
    await userEvent.clear(from);
    await userEvent.type(from, "2026-03-01");
    await userEvent.clear(to);
    await userEvent.type(to, "2026-02-01");
    await userEvent.click(screen.getByRole("button", { name: "Apply range" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("must not be after");
    expect(fetchMock.mock.calls.length).toBe(calls);

    await userEvent.clear(to);
    await userEvent.type(to, "2026-03-31");
    await userEvent.click(screen.getByRole("button", { name: "Apply range" }));
    await waitFor(() => expect(lastQuery().get("from")).toBe("2026-03-01"));
    expect(lastQuery().get("to")).toBe("2026-03-31");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("offers the same numbers as a table", async () => {
    render(<DashboardView />);
    await screen.findByTestId("status-chart");

    await userEvent.click(screen.getByRole("button", { name: "Show as table" }));

    const table = screen.getByTestId("status-table");
    expect(within(table).getByRole("row", { name: /In review 4/ })).toBeInTheDocument();
    expect(within(table).getByRole("row", { name: /Draft 0/ })).toBeInTheDocument();
    expect(screen.queryByTestId("status-chart")).not.toBeInTheDocument();
  });

  it("shows a tooltip with the value on hover and on keyboard focus", async () => {
    render(<DashboardView />);
    const bar = await screen.findByTestId("bar-IN_REVIEW");

    await userEvent.hover(bar);
    expect(within(bar).getByRole("tooltip")).toHaveTextContent("4 In review");
    await userEvent.unhover(bar);
    expect(within(bar).queryByRole("tooltip")).not.toBeInTheDocument();

    bar.focus();
    expect(await within(bar).findByRole("tooltip")).toHaveTextContent("4 In review");
  });

  it("shows the server's refusal", async () => {
    fetchMock.mockImplementation(async () =>
      Response.json({ detail: "You do not have permission to perform this action" }, { status: 403 }),
    );
    render(<DashboardView />);

    expect(await screen.findByText("You do not have permission to perform this action")).toBeInTheDocument();
  });
});
