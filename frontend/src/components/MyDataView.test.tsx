import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { setAccessToken } from "@/lib/api/client";
import type { MyData } from "@/lib/api/types";

import { MyDataView } from "./MyDataView";

const fetchMock = vi.fn<typeof fetch>();

function myData(over: Partial<MyData> = {}): MyData {
  return {
    account: { email: "ana@example.com", created_at: "2026-01-01T00:00:00Z" },
    profile: {
      full_name: "Nguyen An",
      date_of_birth: "1990-05-01",
      national_id: "012345678901",
      address: "1 Example Street",
      income_type: "salaried",
      monthly_income_vnd: 30_000_000,
      existing_debt_payment_vnd: 0,
    },
    applications: [
      {
        id: "a1",
        status: "IN_REVIEW",
        amount_vnd: 50_000_000,
        term_months: 12,
        purpose: null,
        submitted_at: "2026-01-02T00:00:00Z",
        documents: [
          { doc_type: "national_id", size_bytes: 200, uploaded_at: "2026-01-02T01:00:00Z", delete_after: null },
        ],
        decisions: [],
      },
    ],
    consents: [{ version: "2026-11-v1", purposes: ["credit_scoring"], given_at: "2026-01-01T00:00:00Z", withdrawn_at: null }],
    purposes: [{ code: "credit_scoring", label: "Credit scoring and assessment of your loan application" }],
    retention_months: 12,
    deletion_request: null,
    ...over,
  };
}

const openRequest = {
  id: "r1",
  status: "open",
  requested_at: "2026-02-01T00:00:00Z",
  due_at: "2026-03-03T00:00:00Z",
  retained: [
    { what: "Application of 50,000,000 VND (in review)", reason: "The application is still being processed." },
    { what: "Audit log entries and recorded decisions", reason: "They are append-only records (BR-14)." },
  ],
};

let data: MyData;

function posts() {
  return fetchMock.mock.calls.filter(([, init]) => init?.method === "POST");
}

beforeEach(() => {
  data = myData();
  fetchMock.mockReset();
  fetchMock.mockImplementation(async (input, init) => {
    const url = String(input);
    if (init?.method === "POST") {
      data = myData({ deletion_request: openRequest });
      return Response.json(openRequest, { status: 201 });
    }
    if (url.endsWith("/export")) return new Response(new Blob(["{}"], { type: "application/json" }));
    return Response.json(data);
  });
  vi.stubGlobal("fetch", fetchMock);
  vi.stubGlobal("URL", Object.assign(URL, { createObjectURL: vi.fn(() => "blob:x"), revokeObjectURL: vi.fn() }));
  setAccessToken("tok");
});

describe("LF-018 MyDataView", () => {
  it("shows the account, personal details, applications, documents and purposes (AC1)", async () => {
    render(<MyDataView />);

    expect(await screen.findByText("Nguyen An")).toBeInTheDocument();
    expect(screen.getByText("ana@example.com")).toBeInTheDocument();
    expect(screen.getByText("012345678901")).toBeInTheDocument();
    expect(screen.getByTestId("applications")).toHaveTextContent("50,000,000 VND over 12 months · IN_REVIEW");
    expect(screen.getByTestId("applications")).toHaveTextContent("National ID, uploaded");
    expect(screen.getByTestId("purposes")).toHaveTextContent("Credit scoring and assessment");
    expect(screen.getByText(/Retention period: 12 months/)).toBeInTheDocument();
    expect(screen.queryByTestId("deletion-request")).not.toBeInTheDocument();
  });

  it("says so when no personal details exist yet", async () => {
    data = myData({ profile: null, applications: [], consents: [] });
    render(<MyDataView />);

    expect(await screen.findByText("You have not given any personal details yet.")).toBeInTheDocument();
    expect(screen.getByText("No applications.")).toBeInTheDocument();
  });

  it("downloads the export through an authorised request (AC2)", async () => {
    render(<MyDataView />);
    await userEvent.click(await screen.findByRole("button", { name: "Download my data (JSON)" }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.some(([url]) => String(url) === "/api/me/data/export")).toBe(true),
    );
  });

  it("asks for confirmation, records the request, then shows the due date and what is retained (AC3, AC4)", async () => {
    render(<MyDataView />);
    await userEvent.click(await screen.findByRole("button", { name: "Request deletion of my data" }));
    expect(posts()).toHaveLength(0); // nothing is sent before the confirmation

    const dialog = await screen.findByRole("dialog");
    await userEvent.click(within(dialog).getByRole("button", { name: "Yes, request deletion" }));

    await waitFor(() => expect(posts()).toHaveLength(1));
    expect(String(posts()[0][0])).toBe("/api/me/data/deletion-request");
    const box = await screen.findByTestId("deletion-request");
    expect(box).toHaveTextContent("We will answer by");
    expect(screen.getByTestId("retained")).toHaveTextContent("The application is still being processed.");
    expect(screen.getByTestId("retained")).toHaveTextContent("Audit log entries");
    expect(screen.queryByRole("button", { name: "Request deletion of my data" })).not.toBeInTheDocument();
  });

  it("cancelling the confirmation sends nothing", async () => {
    render(<MyDataView />);
    await userEvent.click(await screen.findByRole("button", { name: "Request deletion of my data" }));
    await userEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Cancel" }));

    expect(posts()).toHaveLength(0);
  });

  it("shows the server's refusal if a request is already open", async () => {
    fetchMock.mockImplementation(async (_input, init) =>
      init?.method === "POST"
        ? Response.json({ detail: "You already have an open deletion request." }, { status: 409 })
        : Response.json(data),
    );
    render(<MyDataView />);
    await userEvent.click(await screen.findByRole("button", { name: "Request deletion of my data" }));
    await userEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Yes, request deletion" }));

    expect(await screen.findByText("You already have an open deletion request.")).toBeInTheDocument();
  });
});
