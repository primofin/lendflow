import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { setAccessToken } from "@/lib/api/client";

import { ApplyForm } from "./ApplyForm";

const push = vi.fn();
let search = "";
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(search),
}));

const fetchMock = vi.fn<typeof fetch>();

const terms = {
  allowed_terms_months: [6, 12, 24],
  amount_min_vnd: 1_000_000,
  amount_max_vnd: 500_000_000,
  purpose_required_from_vnd: 100_000_000,
};
const consent = {
  version: "v1",
  statement: "We process your data to assess your loan.",
  purposes: [
    { code: "credit_scoring", label: "Credit scoring" },
    { code: "ai_processing", label: "AI-assisted document processing" },
  ],
  retention_months: 60,
};

function submitCalls() {
  return fetchMock.mock.calls.filter(([, init]) => init?.method === "POST");
}

beforeEach(() => {
  search = "";
  push.mockReset();
  fetchMock.mockReset();
  fetchMock.mockImplementation(async (input, init) => {
    const url = String(input);
    if (url.includes("/api/loan-terms")) return Response.json(terms);
    if (url.includes("/api/consent/current")) return Response.json(consent);
    if (url.endsWith("/api/applications") && init?.method === "POST") {
      return Response.json({ id: "app-1" }, { status: 201 });
    }
    return new Response(null, { status: 404 });
  });
  vi.stubGlobal("fetch", fetchMock);
  setAccessToken("tok");
});

async function fill(small = true) {
  const u = userEvent.setup();
  await screen.findByRole("group", { name: "Consent" });
  await u.type(screen.getByLabelText(/Loan amount/), small ? "50000000" : "150000000");
  await u.selectOptions(screen.getByLabelText("Term"), "12");
  await u.type(screen.getByLabelText("Full name"), "Nguyen Test");
  await u.type(screen.getByLabelText("Date of birth"), "1990-05-01");
  await u.type(screen.getByLabelText("National ID"), "012345678901");
  await u.type(screen.getByLabelText("Address"), "1 Example Street");
  await u.selectOptions(screen.getByLabelText("Income type"), "salaried");
  await u.type(screen.getByLabelText(/Monthly income/), "20000000");
  return u;
}

describe("LF-004 ApplyForm", () => {
  it("lists every consent purpose and the retention period", async () => {
    render(<ApplyForm />);

    expect(await screen.findByText("Credit scoring")).toBeInTheDocument();
    expect(screen.getByText("AI-assisted document processing")).toBeInTheDocument();
    expect(screen.getByText(/we keep your data for 60 months/)).toBeInTheDocument();
  });

  it("blocks submission without consent and highlights the checkbox", async () => {
    render(<ApplyForm />);
    const u = await fill();

    await u.click(screen.getByRole("button", { name: "Submit application" }));

    expect(await screen.findByText(/must accept the consent statement/)).toBeInTheDocument();
    const box = screen.getByRole("checkbox");
    expect(box).toHaveAttribute("aria-invalid", "true");
    await waitFor(() => expect(box).toHaveFocus());
    expect(submitCalls()).toHaveLength(0);
  });

  it("submits a small loan without a purpose and goes to the application", async () => {
    render(<ApplyForm />);
    const u = await fill();
    await u.click(screen.getByRole("checkbox"));

    await u.click(screen.getByRole("button", { name: "Submit application" }));

    await waitFor(() => expect(push).toHaveBeenCalledWith("/applications/app-1"));
    const body = JSON.parse(String(submitCalls()[0][1]?.body));
    expect(body).toMatchObject({
      amount_vnd: 50_000_000,
      term_months: 12,
      purpose: null,
      consent_accepted: true,
      consent_version: "v1",
    });
    expect(body.profile.national_id).toBe("012345678901");
    expect(screen.getByLabelText("National ID")).toHaveValue(""); // personal data cleared
  });

  it("requires a purpose from the configured amount and sends nothing", async () => {
    render(<ApplyForm />);
    const u = await fill(false);
    await u.click(screen.getByRole("checkbox"));

    await u.click(screen.getByRole("button", { name: "Submit application" }));

    expect(await screen.findByText(/A purpose is required for loans of 100,000,000 VND/)).toBeInTheDocument();
    expect(submitCalls()).toHaveLength(0);
  });

  it("shows the server's field message under the field", async () => {
    fetchMock.mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.includes("/api/loan-terms")) return Response.json(terms);
      if (url.includes("/api/consent/current")) return Response.json(consent);
      if (init?.method === "POST") {
        return Response.json(
          { detail: [{ loc: ["body", "profile", "national_id"], msg: "National ID is not valid" }] },
          { status: 422 },
        );
      }
      return new Response(null, { status: 404 });
    });
    render(<ApplyForm />);
    const u = await fill();
    await u.click(screen.getByRole("checkbox"));

    await u.click(screen.getByRole("button", { name: "Submit application" }));

    expect(await screen.findByText("National ID is not valid")).toBeInTheDocument();
    expect(push).not.toHaveBeenCalled();
  });

  it("shows an age rule from the server as a form message and keeps the data", async () => {
    fetchMock.mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.includes("/api/loan-terms")) return Response.json(terms);
      if (url.includes("/api/consent/current")) return Response.json(consent);
      if (init?.method === "POST") {
        return Response.json({ detail: "Applicant must be at least 18 years old" }, { status: 422 });
      }
      return new Response(null, { status: 404 });
    });
    render(<ApplyForm />);
    const u = await fill();
    await u.click(screen.getByRole("checkbox"));

    await u.click(screen.getByRole("button", { name: "Submit application" }));

    expect(await screen.findByText("Applicant must be at least 18 years old")).toBeInTheDocument();
    expect(screen.getByLabelText("Full name")).toHaveValue("Nguyen Test");
  });

  it("pre-fills amount and term from the calculator link, ignoring anything else", async () => {
    search = "amount=75000000&term=24&full_name=Evil";
    render(<ApplyForm />);

    await screen.findByRole("group", { name: "Consent" });
    expect(screen.getByLabelText(/Loan amount/)).toHaveValue("75000000");
    expect(screen.getByLabelText("Term")).toHaveValue("24");
    expect(screen.getByLabelText("Full name")).toHaveValue("");
  });
});
