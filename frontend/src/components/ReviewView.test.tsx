import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { setAccessToken } from "@/lib/api/client";
import { user } from "@/test-utils";

import { ReviewView } from "./ReviewView";

const auth: { user: ReturnType<typeof user> } = { user: user("officer") };
vi.mock("@/lib/auth/AuthProvider", () => ({ useAuth: () => auth }));

const fetchMock = vi.fn<typeof fetch>();

let review: Record<string, unknown>;
let checklist: Record<string, unknown>;

function reviewBody() {
  return {
    id: "a1",
    status: "IN_REVIEW",
    amount_vnd: 150_000_000,
    term_months: 24,
    purpose: "Expand shop",
    annual_rate_percent: 16,
    submitted_at: "2026-01-01T00:00:00Z",
    flags: ["exception"],
    assigned_to_me: false,
    assigned: false,
    supervisor_assigned: false,
    applicant: {
      full_name: "Nguyen An",
      date_of_birth: "1990-05-01",
      national_id_masked: "********8901",
      address: "1 Example Street",
      income_type: "freelance",
      monthly_income_vnd: 30_000_000,
      existing_debt_payment_vnd: 0,
    },
  };
}

function checklistBody() {
  return {
    application_id: "a1",
    income_type: "freelance",
    status: "incomplete",
    exception_flag: false,
    supervisor_assigned: false,
    requirements: [
      { id: "r1", label: "Invoices or contracts", mandatory: true, state: "missing", doc_types: ["invoices_contracts"], document_ids: [] },
      { id: "r2", label: "National ID", mandatory: true, state: "satisfied", doc_types: ["national_id"], document_ids: ["d1"] },
    ],
  };
}

function posts() {
  return fetchMock.mock.calls.filter(([, init]) => init?.method === "POST");
}

beforeEach(() => {
  auth.user = user("officer");
  review = reviewBody();
  checklist = checklistBody();
  fetchMock.mockReset();
  fetchMock.mockImplementation(async (input, init) => {
    const url = String(input);
    if (init?.method === "POST") return Response.json({});
    if (url.endsWith("/review")) return Response.json(review);
    if (url.endsWith("/checklist")) return Response.json(checklist);
    if (url.endsWith("/decisions") || url.endsWith("/reason-codes")) return Response.json([]);
    if (url.endsWith("/cic-check")) return Response.json(null);
    if (url.endsWith("/file")) return new Response(new Blob(["%PDF-1.7"], { type: "application/pdf" }));
    if (url.endsWith("/documents"))
      return Response.json([{ id: "d1", doc_type: "national_id", uploaded_at: "2026-01-02T00:00:00Z" }]);
    return new Response(null, { status: 404 });
  });
  vi.stubGlobal("fetch", fetchMock);
  setAccessToken("tok");
});

describe("F4 ReviewView", () => {
  it("shows the loan, flags and the applicant with a masked national ID", async () => {
    render(<ReviewView id="a1" />);

    expect(await screen.findByText("Nguyen An")).toBeInTheDocument();
    expect(screen.getByText("********8901")).toBeInTheDocument();
    expect(screen.getByTestId("flags")).toHaveTextContent("Exception");
    expect(screen.getByTestId("holder")).toHaveTextContent("Nobody yet");
    expect(screen.getByText("150,000,000 VND")).toBeInTheDocument();
  });

  it("shows an overdue flag on the file (LF-017)", async () => {
    review = { ...reviewBody(), flags: ["overdue"] };
    render(<ReviewView id="a1" />);

    expect(await screen.findByTestId("flags")).toHaveTextContent("Overdue");
  });

  it("lets an officer claim an unassigned file and reloads", async () => {
    render(<ReviewView id="a1" />);
    await userEvent.click(await screen.findByRole("button", { name: "Claim this file" }));

    await waitFor(() => expect(posts()).toHaveLength(1));
    expect(String(posts()[0][0])).toBe("/api/applications/a1/claim");
  });

  it("offers no claim when the file is held, is not in review, or the viewer is a supervisor", async () => {
    review = { ...reviewBody(), assigned: true };
    const first = render(<ReviewView id="a1" />);
    await screen.findByText("Nguyen An");
    expect(screen.queryByRole("button", { name: "Claim this file" })).not.toBeInTheDocument();
    expect(screen.getByTestId("holder")).toHaveTextContent("Another officer");
    first.unmount();

    review = { ...reviewBody(), status: "SUBMITTED" };
    const second = render(<ReviewView id="a1" />);
    await screen.findByText("Nguyen An");
    expect(screen.queryByRole("button", { name: "Claim this file" })).not.toBeInTheDocument();
    second.unmount();

    auth.user = user("supervisor");
    review = reviewBody();
    render(<ReviewView id="a1" />);
    await screen.findByText("Nguyen An");
    expect(screen.queryByRole("button", { name: "Claim this file" })).not.toBeInTheDocument();
  });

  it("shows the server's refusal when the claim fails", async () => {
    fetchMock.mockImplementation(async (input, init) => {
      const url = String(input);
      if (init?.method === "POST") return Response.json({ detail: "This file was already taken" }, { status: 409 });
      if (url.endsWith("/review")) return Response.json(review);
      if (url.endsWith("/checklist")) return Response.json(checklist);
      return Response.json([]);
    });
    render(<ReviewView id="a1" />);
    await userEvent.click(await screen.findByRole("button", { name: "Claim this file" }));

    expect(await screen.findByText("This file was already taken")).toBeInTheDocument();
  });

  it("lets an officer declare a missing mandatory document unavailable", async () => {
    render(<ReviewView id="a1" />);
    await userEvent.click(
      await screen.findByRole("button", { name: "No Invoices or contracts available" }),
    );

    await waitFor(() => expect(posts()).toHaveLength(1));
    expect(String(posts()[0][0])).toBe("/api/applications/a1/exceptions");
    expect(JSON.parse(String(posts()[0][1]?.body))).toEqual({ requirement_id: "r1" });
  });

  it("gives supervisors no exception button and shows Complete in green when nothing is missing", async () => {
    auth.user = user("supervisor");
    const { unmount } = render(<ReviewView id="a1" />);
    await screen.findByText("Nguyen An");
    expect(screen.queryByRole("button", { name: /available/ })).not.toBeInTheDocument();
    unmount();

    auth.user = user("officer");
    checklist = {
      ...checklistBody(),
      status: "complete",
      requirements: [(checklistBody().requirements as object[])[1]],
    };
    render(<ReviewView id="a1" />);
    const status = await screen.findByTestId("checklist-status");
    expect(status).toHaveTextContent("Complete");
    expect(status.className).toMatch(/green/);
    expect(screen.queryByRole("button", { name: /available/ })).not.toBeInTheDocument();
  });

  it("opens a document through an authorised request, not a plain link", async () => {
    const tab = { location: { href: "" }, opener: {}, close: vi.fn() };
    const open = vi.fn(() => tab);
    vi.stubGlobal("open", open);
    URL.createObjectURL = vi.fn(() => "blob:doc");
    URL.revokeObjectURL = vi.fn();
    render(<ReviewView id="a1" />);

    await userEvent.click(await screen.findByRole("button", { name: "Open National ID" }));

    await waitFor(() => expect(tab.location.href).toBe("blob:doc"));
    expect(open).toHaveBeenCalledWith("", "_blank");
    expect(tab.opener).toBeNull();
    const call = fetchMock.mock.calls.find(([u]) => String(u).endsWith("/file"))!;
    expect((call[1]?.headers as Record<string, string>).Authorization).toBe("Bearer tok");
  });

  it("shows the server's message when the file cannot be opened by this officer", async () => {
    fetchMock.mockImplementation(async () =>
      Response.json({ detail: "You do not have permission to perform this action" }, { status: 403 }),
    );
    render(<ReviewView id="a1" />);

    expect(await screen.findByRole("alert")).toHaveTextContent("You do not have permission");
  });

  it("closes the pre-opened tab and says why when the document cannot be fetched", async () => {
    const tab = { location: { href: "" }, opener: {}, close: vi.fn() };
    vi.stubGlobal("open", vi.fn(() => tab));
    fetchMock.mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/file")) return Response.json({ detail: "The stored file is missing. Contact support." }, { status: 404 });
      if (url.endsWith("/review")) return Response.json(review);
      if (url.endsWith("/checklist")) return Response.json(checklist);
      return Response.json([{ id: "d1", doc_type: "national_id", uploaded_at: "2026-01-02T00:00:00Z" }]);
    });
    render(<ReviewView id="a1" />);

    await userEvent.click(await screen.findByRole("button", { name: "Open National ID" }));

    expect(await screen.findByText("The stored file is missing. Contact support.")).toBeInTheDocument();
    expect(tab.close).toHaveBeenCalled();
  });
});
