import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CalculatorForm } from "./CalculatorForm";

const fetchMock = vi.fn<typeof fetch>();

const terms = {
  allowed_terms_months: [6, 12, 24, 36, 60],
  amount_min_vnd: 1_000_000,
  amount_max_vnd: 500_000_000,
  purpose_required_from_vnd: 100_000_000,
};
const quote = {
  amount_vnd: 100_000_000,
  term_months: 24,
  method: "reducing balance",
  annual_rate_percent: 16,
  monthly_payment_vnd: 4_896_311,
  total_repaid_vnd: 117_511_465,
  total_interest_vnd: 17_511_465,
  first_month_interest_vnd: 0,
  first_month_principal_vnd: 0,
};

function respond(url: string): Response {
  if (url.includes("/api/loan-terms")) return Response.json(terms);
  if (url.includes("/api/calculator")) return Response.json(quote);
  return new Response(null, { status: 404 });
}

function calculatorCalls() {
  return fetchMock.mock.calls.filter(([url]) => String(url).includes("/api/calculator"));
}

beforeEach(() => {
  fetchMock.mockReset();
  fetchMock.mockImplementation(async (input) => respond(String(input)));
  vi.stubGlobal("fetch", fetchMock);
});

describe("LF-003 CalculatorForm", () => {
  it("shows the worked example, the method and the rate", async () => {
    render(<CalculatorForm />);

    expect(await screen.findByTestId("monthly")).toHaveTextContent("4,896,311 VND");
    expect(screen.getByTestId("total")).toHaveTextContent("117,511,465 VND");
    expect(screen.getByTestId("interest")).toHaveTextContent("17,511,465 VND");
    expect(screen.getByText(/reducing balance method at 16% a year/)).toBeInTheDocument();
    expect(String(calculatorCalls()[0][0])).toContain("amount_vnd=100000000");
    expect(String(calculatorCalls()[0][0])).toContain("term_months=24");
  });

  it("offers only the configured terms", async () => {
    render(<CalculatorForm />);
    await screen.findByTestId("monthly");

    const options = screen.getAllByRole("option").map((o) => o.textContent);
    expect(options).toEqual(["6 months", "12 months", "24 months", "36 months", "60 months"]);
  });

  it("shows a message under the field for non-numeric input and does not call the API", async () => {
    render(<CalculatorForm />);
    await screen.findByTestId("monthly");
    const before = calculatorCalls().length;

    const amount = screen.getByLabelText("Loan amount (VND)");
    await userEvent.clear(amount);
    await userEvent.type(amount, "abc");

    expect(await screen.findByText(/Enter the amount as a number/)).toBeInTheDocument();
    expect(amount).toHaveAttribute("aria-invalid", "true");
    expect(screen.queryByTestId("monthly")).not.toBeInTheDocument();
    await new Promise((r) => setTimeout(r, 450));
    expect(calculatorCalls().length).toBe(before);
  });

  it("refuses an amount outside the configured range without calling the API", async () => {
    render(<CalculatorForm />);
    await screen.findByTestId("monthly");

    const amount = screen.getByLabelText("Loan amount (VND)");
    await userEvent.clear(amount);
    await userEvent.type(amount, "600000000");

    expect(await screen.findByText(/must be between 1,000,000 VND and 500,000,000 VND/)).toBeInTheDocument();
  });

  it("debounces typing into a single request", async () => {
    render(<CalculatorForm />);
    await screen.findByTestId("monthly");
    const before = calculatorCalls().length;

    const amount = screen.getByLabelText("Loan amount (VND)");
    await userEvent.clear(amount);
    await userEvent.type(amount, "5000000");

    await waitFor(() => expect(calculatorCalls().length).toBe(before + 1));
    await new Promise((r) => setTimeout(r, 450));
    expect(calculatorCalls().length).toBe(before + 1);
  });

  it("links to the application with only the amount and term", async () => {
    render(<CalculatorForm />);
    const link = await screen.findByRole("link", { name: "Apply with these terms" });
    expect(link).toHaveAttribute("href", "/apply?amount=100000000&term=24");
  });
});
