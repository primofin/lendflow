import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { setAccessToken } from "@/lib/api/client";
import type { CicCheck } from "@/lib/api/types";

import { CicPanel } from "./CicPanel";

const fetchMock = vi.fn<typeof fetch>();

function check(over: Partial<CicCheck>): CicCheck {
  return {
    status: "running",
    progress_pct: 25,
    seconds_remaining: 15,
    attempt: 1,
    max_attempts: 2,
    message: "Credit check in progress. You can keep using other screens.",
    debt_group: null,
    flag: null,
    summary: null,
    started_at: "2026-01-01T00:00:00Z",
    finished_at: null,
    ...over,
  };
}

let latest: CicCheck | null;

function posts() {
  return fetchMock.mock.calls.filter(([, init]) => init?.method === "POST");
}

beforeEach(() => {
  latest = null;
  fetchMock.mockReset();
  fetchMock.mockImplementation(async (_input, init) => {
    if (init?.method === "POST") {
      latest = check({ progress_pct: 0, seconds_remaining: 20 }); // the server now holds it
      return Response.json(latest, { status: 201 });
    }
    return Response.json(latest);
  });
  vi.stubGlobal("fetch", fetchMock);
  setAccessToken("tok");
});

afterEach(() => {
  vi.useRealTimers();
});

describe("LF-008 CicPanel", () => {
  it("offers to run the check on a file in review and shows progress once started", async () => {
    render(<CicPanel applicationId="a1" status="IN_REVIEW" />);

    await userEvent.click(await screen.findByRole("button", { name: "Run credit check" }));

    expect(String(posts()[0][0])).toBe("/api/applications/a1/cic-check");
    expect(await screen.findByRole("progressbar")).toHaveAttribute("aria-valuenow", "0");
    expect(screen.getByTestId("cic-remaining")).toHaveTextContent("About 20 seconds remaining");
    expect(screen.queryByRole("button", { name: "Run credit check" })).not.toBeInTheDocument();
  });

  it("shows nothing when no check exists and the file is not in review", async () => {
    render(<CicPanel applicationId="a1" status="SUBMITTED" />);

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(screen.queryByTestId("cic-panel")).not.toBeInTheDocument();
  });

  it("keeps polling a running check and then shows the debt group and summary", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    latest = check({});
    render(<CicPanel applicationId="a1" status="IN_REVIEW" />);
    expect(await screen.findByTestId("cic-remaining")).toHaveTextContent("About 15 seconds remaining");

    latest = check({
      status: "done",
      progress_pct: 100,
      seconds_remaining: 0,
      debt_group: 3,
      flag: "recommend_reject",
      summary: "Group 3: substandard debt (synthetic data).",
      finished_at: "2026-01-01T00:00:20Z",
    });
    await act(() => vi.advanceTimersByTimeAsync(1100));

    expect(await screen.findByTestId("cic-group")).toHaveTextContent("3");
    expect(screen.getByTestId("cic-flag")).toHaveTextContent("Recommend reject (a person decides)");
    expect(screen.getByText(/substandard debt/)).toBeInTheDocument();
    expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
  });

  it("shows the retry message while the bureau is silent", async () => {
    latest = check({
      attempt: 2,
      progress_pct: 0,
      message: "The credit bureau did not respond in time. The file is saved and the check is retrying automatically (attempt 2 of 2). Credit check in progress.",
    });
    render(<CicPanel applicationId="a1" status="IN_REVIEW" />);

    expect(await screen.findByTestId("cic-message")).toHaveTextContent("retrying automatically");
  });

  it("after a final timeout shows the message and lets the officer run it again", async () => {
    latest = check({
      status: "timeout",
      progress_pct: 0,
      seconds_remaining: null,
      message: "The credit bureau did not respond after 2 attempts. The file is saved; start the check again later.",
    });
    render(<CicPanel applicationId="a1" status="IN_REVIEW" />);

    expect(await screen.findByTestId("cic-message")).toHaveTextContent("did not respond after 2 attempts");
    expect(screen.getByRole("button", { name: "Run the credit check again" })).toBeInTheDocument();
  });

  it("shows the server's refusal when the check cannot be started", async () => {
    fetchMock.mockImplementation(async (_input, init) =>
      init?.method === "POST"
        ? Response.json({ detail: "A credit check is already running for this application" }, { status: 409 })
        : Response.json(null),
    );
    render(<CicPanel applicationId="a1" status="IN_REVIEW" />);

    await userEvent.click(await screen.findByRole("button", { name: "Run credit check" }));

    expect(await screen.findByText("A credit check is already running for this application")).toBeInTheDocument();
  });
});
