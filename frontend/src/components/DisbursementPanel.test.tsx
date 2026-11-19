import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { setAccessToken } from "@/lib/api/client";
import type { DisbursementStatus } from "@/lib/api/types";

import { DisbursementPanel } from "./DisbursementPanel";

const fetchMock = vi.fn<typeof fetch>();

function state(over: Partial<DisbursementStatus>): DisbursementStatus {
  return { disbursement: null, amount_vnd: 12_000_000, face_match_required: true, threshold_vnd: 10_000_000, ...over };
}

function posts() {
  return fetchMock.mock.calls.filter(([, init]) => init?.method === "POST");
}

let current: DisbursementStatus;

beforeEach(() => {
  current = state({});
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
  setAccessToken("tok");
});

describe("LF-020 DisbursementPanel", () => {
  it("keeps Disburse disabled until a face match has passed, then sends its id", async () => {
    fetchMock.mockImplementation(async (input, init) => {
      if (init?.method === "POST" && String(input).endsWith("/face-match"))
        return Response.json({ id: "fm1", passed: true, expires_at: "2026-01-01T00:05:00Z" }, { status: 201 });
      if (init?.method === "POST") {
        current = state({
          disbursement: {
            id: "d1", application_id: "a1", amount_vnd: 12_000_000, face_match_id: "fm1",
            disbursed_by: "u1", disbursed_at: "2026-01-01T00:01:00Z",
          },
        });
        return Response.json(current, { status: 201 });
      }
      return Response.json(current);
    });
    render(<DisbursementPanel applicationId="a1" />);
    const disburse = await screen.findByRole("button", { name: /^Disburse/ });
    expect(disburse).toBeDisabled();

    await userEvent.click(screen.getByRole("button", { name: "Simulate face match: pass" }));
    expect(await screen.findByTestId("face-match-result")).toHaveTextContent("passed");
    await userEvent.click(screen.getByRole("button", { name: /^Disburse/ }));

    expect(JSON.parse(String(posts()[1][1]?.body))).toEqual({ face_match_id: "fm1" });
    expect(await screen.findByTestId("disbursed")).toHaveTextContent("Disbursed 12,000,000 VND");
  });

  it("a failed face match blocks the Disburse button and says so", async () => {
    fetchMock.mockImplementation(async (_input, init) =>
      init?.method === "POST"
        ? Response.json({ id: "fm1", passed: false, expires_at: "2026-01-01T00:05:00Z" }, { status: 201 })
        : Response.json(current),
    );
    render(<DisbursementPanel applicationId="a1" />);

    await userEvent.click(await screen.findByRole("button", { name: "Simulate face match: fail" }));

    expect(await screen.findByTestId("face-match-result")).toHaveTextContent("blocked");
    expect(screen.getByRole("button", { name: /^Disburse/ })).toBeDisabled();
  });

  it("a small amount shows no face-match step and can be disbursed directly", async () => {
    current = state({ amount_vnd: 5_000_000, face_match_required: false });
    fetchMock.mockImplementation(async () => Response.json(current));
    render(<DisbursementPanel applicationId="a1" />);

    const disburse = await screen.findByRole("button", { name: "Disburse 5,000,000 VND" });
    expect(disburse).toBeEnabled();
    expect(screen.queryByRole("button", { name: /Simulate face match/ })).not.toBeInTheDocument();
  });

  it("shows the server's refusal", async () => {
    current = state({ amount_vnd: 5_000_000, face_match_required: false });
    fetchMock.mockImplementation(async (_input, init) =>
      init?.method === "POST"
        ? Response.json({ detail: "This loan has already been disbursed" }, { status: 409 })
        : Response.json(current),
    );
    render(<DisbursementPanel applicationId="a1" />);

    await userEvent.click(await screen.findByRole("button", { name: /^Disburse/ }));

    expect(await screen.findByText("This loan has already been disbursed")).toBeInTheDocument();
  });
});
