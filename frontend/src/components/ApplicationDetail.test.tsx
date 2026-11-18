import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { setAccessToken } from "@/lib/api/client";

import { ApplicationDetail } from "./ApplicationDetail";

const fetchMock = vi.fn<typeof fetch>();

const scheduleBody = {
  application_id: "a1",
  start_date: "2026-11-18",
  annual_rate_percent: 14,
  term_months: 2,
  monthly_payment_vnd: 510_000,
  total_paid_vnd: 1_020_000,
  total_interest_vnd: 20_000,
  instalments: [
    { number: 1, due_date: "2026-12-18", payment_vnd: 510_000, principal_vnd: 500_000, interest_vnd: 10_000, balance_vnd: 500_000 },
    { number: 2, due_date: "2027-01-18", payment_vnd: 510_000, principal_vnd: 500_000, interest_vnd: 10_000, balance_vnd: 0 },
  ],
};

const notice = {
  notice: "Only synthetic, non-real documents may be used in this demo.",
  allowed_types: ["image/jpeg", "image/png", "application/pdf"],
  max_size_mb: 5,
};

let state: {
  status: string;
  tracker: object;
  checklist: object;
  documents: object[];
};

function steps(current: number) {
  return ["Received", "Under assessment", "Awaiting approval", "Completed"].map((label, i) => ({
    label,
    state: i < current ? "done" : i === current ? "current" : "upcoming",
    updated_at: i <= current ? "2026-01-05T08:30:00Z" : null,
  }));
}

function requirement(label: string, st: "satisfied" | "missing", types = ["payslips"]) {
  return { id: `r-${label}`, label, mandatory: true, state: st, doc_types: types, document_ids: [] };
}

function baseState() {
  return {
    status: "SUBMITTED",
    tracker: { application_id: "a1", current_step: "Received", steps: steps(0) },
    checklist: {
      application_id: "a1",
      income_type: "salaried",
      status: "incomplete",
      requirements: [requirement("Payslips", "missing"), requirement("National ID", "satisfied")],
      exception_flag: false,
      supervisor_assigned: false,
    },
    documents: [],
  };
}

function uploadCalls() {
  return fetchMock.mock.calls.filter(([, init]) => init?.method === "POST");
}

beforeEach(() => {
  fetchMock.mockReset();
  state = baseState();
  fetchMock.mockImplementation(async (input, init) => {
    const url = String(input);
    if (init?.method === "POST" && url.endsWith("/documents")) {
      return Response.json({ id: "d-new", doc_type: "payslips", uploaded_at: "2026-01-05T09:00:00Z" }, { status: 201 });
    }
    if (url.endsWith("/resubmit")) return Response.json({});
    if (url.endsWith("/tracker")) return Response.json(state.tracker);
    if (url.endsWith("/checklist")) return Response.json(state.checklist);
    if (url.endsWith("/documents")) return Response.json(state.documents);
    if (url.endsWith("/documents/notice")) return Response.json(notice);
    if (url.endsWith("/schedule")) return Response.json(scheduleBody);
    return Response.json({
      id: "a1",
      status: state.status,
      amount_vnd: 50_000_000,
      term_months: 12,
      purpose: null,
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  setAccessToken("tok");
});

function pdf(name = "a.pdf", size?: number) {
  const f = new File(["%PDF-1.7"], name, { type: "application/pdf" });
  if (size !== undefined) Object.defineProperty(f, "size", { value: size });
  return f;
}

describe("LF-012 tracker", () => {
  it("shows the four steps with the current one marked and last-update times", async () => {
    state.tracker = { application_id: "a1", current_step: "Under assessment", steps: steps(1) };
    render(<ApplicationDetail id="a1" />);

    const progress = (await screen.findByRole("heading", { name: "Progress" })).closest("section")!;
    const items = within(progress).getAllByRole("listitem");
    expect(items.map((i) => i.getAttribute("data-state"))).toEqual(["done", "current", "upcoming", "upcoming"]);
    expect(items[1]).toHaveAttribute("aria-current", "step");
    expect(items[0].querySelector("time")).not.toBeNull();
    expect(items[3].querySelector("time")).toBeNull();
  });

  it("shows a rejection's reason and what could change it", async () => {
    state.status = "REJECTED";
    state.tracker = {
      application_id: "a1",
      current_step: "Completed",
      steps: steps(3),
      decision: {
        outcome: "reject",
        reason_label: "Insufficient income",
        explanation: "Your income does not cover the payment.",
        conditions: "A co-borrower with income could change this.",
        decided_at: "2026-01-06T00:00:00Z",
      },
    };
    render(<ApplicationDetail id="a1" />);

    const box = await screen.findByTestId("decision");
    expect(box).toHaveTextContent("Not approved");
    expect(box).toHaveTextContent("Insufficient income");
    expect(box).toHaveTextContent("A co-borrower with income could change this.");
  });

  it("lists the exact missing items with upload buttons and resubmit once complete", async () => {
    state.status = "NEEDS_INFO";
    state.tracker = {
      application_id: "a1",
      current_step: "Under assessment",
      steps: steps(1),
      needs_info: {
        message: "Please add a clearer payslip.",
        missing_documents: [{ label: "Payslips", accepted_types: ["payslips"] }],
        upload_url: "/x",
        can_resubmit: false,
      },
    };
    const { rerender } = render(<ApplicationDetail id="a1" />);

    expect(await screen.findByText("Please add a clearer payslip.")).toBeInTheDocument();
    expect(screen.getByLabelText("File for Payslips")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Resubmit for review" })).not.toBeInTheDocument();

    state.tracker = {
      ...(state.tracker as object),
      needs_info: { message: "Please add a clearer payslip.", missing_documents: [], upload_url: "/x", can_resubmit: true },
    };
    rerender(<ApplicationDetail id="a2" />);
    const button = await screen.findByRole("button", { name: "Resubmit for review" });
    await userEvent.click(button);

    await waitFor(() =>
      expect(fetchMock.mock.calls.some(([u]) => String(u).endsWith("/resubmit"))).toBe(true),
    );
  });
});

describe("LF-007 checklist (borrower view)", () => {
  it("shows what is missing, then Complete in green", async () => {
    const { rerender } = render(<ApplicationDetail id="a1" />);
    expect(await screen.findByTestId("checklist-status")).toHaveTextContent("1 document still needed");

    state.checklist = { ...(state.checklist as object), status: "complete", requirements: [requirement("Payslips", "satisfied")] };
    rerender(<ApplicationDetail id="a3" />);

    await waitFor(() => expect(screen.getByTestId("checklist-status")).toHaveTextContent("Complete"));
    expect(screen.getByTestId("checklist-status").className).toMatch(/green/);
  });
});

describe("LF-005 upload", () => {
  it("shows the synthetic-documents notice", async () => {
    render(<ApplicationDetail id="a1" />);
    expect(await screen.findByText(notice.notice)).toBeInTheDocument();
  });

  it("uploads a PDF for a missing item with the right document type", async () => {
    render(<ApplicationDetail id="a1" />);
    const input = await screen.findByLabelText("File for Payslips");

    await userEvent.upload(input, pdf());
    await userEvent.click(screen.getByRole("button", { name: /Upload Payslips/ }));

    await waitFor(() => expect(uploadCalls()).toHaveLength(1));
    const form = uploadCalls()[0][1]?.body as FormData;
    expect(form.get("doc_type")).toBe("payslips");
    expect((form.get("file") as File).name).toBe("a.pdf");
  });

  it("refuses an oversized file and a wrong type before sending anything", async () => {
    render(<ApplicationDetail id="a1" />);
    const input = await screen.findByLabelText("File for Payslips");
    const send = screen.getByRole("button", { name: /Upload Payslips/ });

    await userEvent.upload(input, pdf("big.pdf", 6 * 1024 * 1024));
    await userEvent.click(send);
    expect(await screen.findByText(/over the 5 MB limit/)).toBeInTheDocument();

    await userEvent.upload(input, new File(["x"], "a.txt", { type: "text/plain" }), { applyAccept: false });
    await userEvent.click(send);
    expect(await screen.findByText(/not a JPG, PNG or PDF/)).toBeInTheDocument();
    expect(uploadCalls()).toHaveLength(0);
  });

  it("says so when the same file was already stored", async () => {
    state.documents = [{ id: "d-new", doc_type: "payslips", uploaded_at: "2026-01-05T09:00:00Z" }];
    render(<ApplicationDetail id="a1" />);
    const input = await screen.findByLabelText("File for Payslips");

    await userEvent.upload(input, pdf());
    await userEvent.click(screen.getByRole("button", { name: /Upload Payslips/ }));

    expect(await screen.findByText(/already uploaded, so nothing was added/)).toBeInTheDocument();
  });

  it("shows the server's message and invites a retry when the upload fails", async () => {
    fetchMock.mockImplementation(async (input, init) => {
      const url = String(input);
      if (init?.method === "POST") throw new TypeError("network down");
      if (url.endsWith("/tracker")) return Response.json(state.tracker);
      if (url.endsWith("/checklist")) return Response.json(state.checklist);
      if (url.endsWith("/documents")) return Response.json([]);
      if (url.endsWith("/documents/notice")) return Response.json(notice);
      return Response.json({ id: "a1", status: "SUBMITTED", amount_vnd: 1, term_months: 6, purpose: null });
    });
    render(<ApplicationDetail id="a1" />);
    const input = await screen.findByLabelText("File for Payslips");

    await userEvent.upload(input, pdf());
    await userEvent.click(screen.getByRole("button", { name: /Upload Payslips/ }));

    expect(await screen.findByText(/will not create a duplicate/)).toBeInTheDocument();
  });

  it("offers no upload once the application is decided", async () => {
    state.status = "APPROVED";
    render(<ApplicationDetail id="a1" />);

    expect(await screen.findByText(/can no longer be added/)).toBeInTheDocument();
    expect(screen.queryByLabelText("File for Payslips")).not.toBeInTheDocument();
  });

  it("shows the repayment schedule only once the application is approved (LF-014)", async () => {
    state.status = "APPROVED";
    const approved = render(<ApplicationDetail id="a1" />);
    expect(await screen.findByTestId("schedule-table")).toBeInTheDocument();
    approved.unmount();

    state.status = "IN_REVIEW";
    render(<ApplicationDetail id="a1" />);
    await screen.findByTestId("status");
    expect(screen.queryByTestId("schedule")).not.toBeInTheDocument();
  });
});
