import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { setAccessToken } from "@/lib/api/client";

import { DataRequestsAdmin } from "./DataRequestsAdmin";

const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
  setAccessToken("tok");
});

describe("LF-018 DataRequestsAdmin", () => {
  it("lists requests with their due dates and flags overdue ones (AC3)", async () => {
    fetchMock.mockResolvedValue(
      Response.json([
        { id: "r1", user_id: "u1", email: "ana@example.com", status: "open", requested_at: "2026-01-01T00:00:00Z", due_at: "2026-01-31T00:00:00Z", overdue: true },
        { id: "r2", user_id: "u2", email: "binh@example.com", status: "open", requested_at: "2026-02-01T00:00:00Z", due_at: "2099-03-03T00:00:00Z", overdue: false },
      ]),
    );
    render(<DataRequestsAdmin />);

    const table = await screen.findByTestId("data-requests");
    expect(table).toHaveTextContent("ana@example.com");
    expect(table).toHaveTextContent("Open, overdue");
    expect(table).toHaveTextContent("binh@example.com");
  });

  it("says so when there are none", async () => {
    fetchMock.mockResolvedValue(Response.json([]));
    render(<DataRequestsAdmin />);

    expect(await screen.findByText("No deletion requests.")).toBeInTheDocument();
  });

  it("shows the server's refusal", async () => {
    fetchMock.mockResolvedValue(
      Response.json({ detail: "You do not have permission to perform this action" }, { status: 403 }),
    );
    render(<DataRequestsAdmin />);

    expect(await screen.findByText("You do not have permission to perform this action")).toBeInTheDocument();
  });
});
