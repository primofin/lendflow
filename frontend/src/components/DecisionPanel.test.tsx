import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { setAccessToken } from "@/lib/api/client";
import type { DecisionEntry } from "@/lib/api/types";

import { DecisionPanel } from "./DecisionPanel";

const fetchMock = vi.fn<typeof fetch>();
const onChanged = vi.fn();

const reasons = [
  { code: "low_income", label: "Insufficient income" },
  { code: "incomplete", label: "Incomplete documents" },
];
const LONG = "Your income does not cover the monthly payment.";

let history: DecisionEntry[];
let postResponse: () => Response;

function entry(over: Partial<DecisionEntry>): DecisionEntry {
  return {
    id: "d1",
    application_id: "a1",
    outcome: "reject",
    reason_code: "low_income",
    explanation: LONG,
    conditions: "A co-borrower could change this.",
    supersedes_id: null,
    superseded_by: null,
    decided_by: "other",
    decided_at: "2026-01-05T08:00:00Z",
    ...over,
  };
}

function posts() {
  return fetchMock.mock.calls.filter(([, init]) => init?.method === "POST");
}

function renderPanel(props: Partial<React.ComponentProps<typeof DecisionPanel>> = {}) {
  return render(
    <DecisionPanel
      applicationId="a1"
      status="IN_REVIEW"
      role="officer"
      userId="me"
      onChanged={onChanged}
      {...props}
    />,
  );
}

beforeEach(() => {
  history = [];
  postResponse = () => Response.json({ id: "new" }, { status: 201 });
  onChanged.mockReset();
  fetchMock.mockReset();
  fetchMock.mockImplementation(async (input, init) => {
    const url = String(input);
    if (init?.method === "POST") return postResponse();
    if (url.endsWith("/decisions")) return Response.json(history);
    if (url.endsWith("/reason-codes")) return Response.json(reasons);
    return new Response(null, { status: 404 });
  });
  vi.stubGlobal("fetch", fetchMock);
  setAccessToken("tok");
});

async function chooseOutcome(label: string) {
  await userEvent.selectOptions(await screen.findByLabelText("Your decision"), label);
}

describe("LF-011 decision form", () => {
  it("offers all four outcomes to an officer on an in-review file", async () => {
    renderPanel();
    await chooseOutcome("");
    const options = within(screen.getByLabelText("Your decision")).getAllByRole("option").map((o) => o.textContent);
    expect(options).toEqual(["Choose a decision", "Approve", "Reject", "Request information", "Refer to a supervisor"]);
  });

  it("does not offer a supervisor the referral", async () => {
    renderPanel({ role: "supervisor" });
    await screen.findByLabelText("Your decision");
    expect(screen.queryByRole("option", { name: "Refer to a supervisor" })).not.toBeInTheDocument();
  });

  it("blocks a rejection without reason or explanation and sends nothing", async () => {
    renderPanel();
    await chooseOutcome("reject");

    await userEvent.click(screen.getByRole("button", { name: "Review decision" }));

    expect(await screen.findByText(/Choose a reason code/)).toBeInTheDocument();
    expect(screen.getByText(/at least 20 characters/)).toBeInTheDocument();
    expect(screen.getByText("Say which documents or conditions could change the outcome.")).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(posts()).toHaveLength(0);
  });

  it("asks for confirmation and sends nothing until it is given", async () => {
    renderPanel();
    await chooseOutcome("reject");
    await userEvent.selectOptions(screen.getByLabelText("Reason code"), "low_income");
    await userEvent.type(screen.getByLabelText("Explanation for the borrower"), LONG);
    await userEvent.type(screen.getByLabelText(/could change the outcome/), "A co-borrower.");

    await userEvent.click(screen.getByRole("button", { name: "Review decision" }));

    const dialog = await screen.findByRole("dialog");
    expect(dialog).toHaveTextContent("You are rejecting this application");
    expect(dialog).toHaveTextContent("cannot be deleted");
    expect(posts()).toHaveLength(0);

    await userEvent.click(within(dialog).getByRole("button", { name: "Confirm and record" }));

    await waitFor(() => expect(posts()).toHaveLength(1));
    expect(JSON.parse(String(posts()[0][1]?.body))).toEqual({
      outcome: "reject",
      reason_code: "low_income",
      explanation: LONG,
      conditions: "A co-borrower.",
    });
    await waitFor(() => expect(onChanged).toHaveBeenCalled());
  });

  it("cancelling the confirmation sends nothing", async () => {
    renderPanel();
    await chooseOutcome("approve");
    await userEvent.click(screen.getByRole("button", { name: "Review decision" }));

    const dialog = await screen.findByRole("dialog");
    await userEvent.click(within(dialog).getByRole("button", { name: "Cancel" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(posts()).toHaveLength(0);
  });

  it("shows the server's refusal (for example the approval limit) and keeps the form", async () => {
    postResponse = () => Response.json({ detail: "Supervisor approval required" }, { status: 403 });
    renderPanel();
    await chooseOutcome("approve");
    await userEvent.click(screen.getByRole("button", { name: "Review decision" }));
    await userEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Confirm and record" }));

    expect(await screen.findByText("Supervisor approval required")).toBeInTheDocument();
    expect(screen.getByLabelText("Your decision")).toHaveValue("approve");
    expect(onChanged).not.toHaveBeenCalled();
  });

  it("sends a request for information with just the message", async () => {
    renderPanel();
    await chooseOutcome("request_info");
    await userEvent.type(screen.getByLabelText("What the borrower must add"), LONG);
    await userEvent.click(screen.getByRole("button", { name: "Review decision" }));
    await userEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Confirm and record" }));

    await waitFor(() => expect(posts()).toHaveLength(1));
    expect(JSON.parse(String(posts()[0][1]?.body))).toEqual({ outcome: "request_info", explanation: LONG });
  });

  it("tells an officer a referred file is for supervisors and shows no form", async () => {
    renderPanel({ status: "REFERRED" });

    expect(await screen.findByText(/Only a supervisor can decide it/)).toBeInTheDocument();
    expect(screen.queryByLabelText("Your decision")).not.toBeInTheDocument();
  });

  it("shows no form once the file is decided, for an officer", async () => {
    history = [entry({ outcome: "approve", reason_code: null, explanation: null, conditions: null })];
    renderPanel({ status: "APPROVED" });

    await screen.findByTestId("decision-history");
    expect(screen.queryByLabelText("Your decision")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Correct this decision" })).not.toBeInTheDocument();
  });
});

describe("LF-011 history and corrections", () => {
  it("shows every entry with who, reason, explanation and conditions, oldest first", async () => {
    history = [
      entry({ id: "d1", superseded_by: "d2" }),
      entry({ id: "d2", outcome: "approve", reason_code: null, explanation: null, conditions: null, supersedes_id: "d1", decided_by: "me", decided_at: "2026-01-06T08:00:00Z" }),
    ];
    renderPanel({ status: "APPROVED", role: "supervisor" });

    const items = within(await screen.findByTestId("decision-history")).getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent("Rejected");
    expect(items[0]).toHaveTextContent("Another staff member");
    expect(items[0]).toHaveTextContent("Reason: Insufficient income");
    expect(items[0]).toHaveTextContent(LONG);
    expect(items[0]).toHaveTextContent("A co-borrower could change this.");
    expect(items[0]).toHaveTextContent("Corrected by a later decision");
    expect(items[1]).toHaveTextContent("Approved");
    expect(items[1]).toHaveTextContent("You");
    expect(items[1]).toHaveTextContent("Corrects an earlier decision");
  });

  it("lets a supervisor correct the latest decision, offering only approve or reject, with its id", async () => {
    history = [entry({ id: "d1" })];
    renderPanel({ status: "REJECTED", role: "supervisor" });

    await userEvent.click(await screen.findByRole("button", { name: "Correct this decision" }));
    const options = within(screen.getByLabelText("Your decision")).getAllByRole("option").map((o) => o.textContent);
    expect(options).toEqual(["Choose a decision", "Approve", "Reject"]);
    await chooseOutcome("approve");
    await userEvent.click(screen.getByRole("button", { name: "Review correction" }));
    const dialog = await screen.findByRole("dialog");
    expect(dialog).toHaveTextContent("The original decision stays on record");
    await userEvent.click(within(dialog).getByRole("button", { name: "Confirm and record" }));

    await waitFor(() => expect(posts()).toHaveLength(1));
    expect(JSON.parse(String(posts()[0][1]?.body))).toEqual({ outcome: "approve", supersedes_id: "d1" });
  });

  it("offers no correction for an entry that was already corrected", async () => {
    history = [entry({ id: "d1", superseded_by: "d2" })];
    renderPanel({ status: "REJECTED", role: "supervisor" });

    await screen.findByTestId("decision-history");
    expect(screen.queryByRole("button", { name: "Correct this decision" })).not.toBeInTheDocument();
  });
});
