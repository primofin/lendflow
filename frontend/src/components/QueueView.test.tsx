import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { setAccessToken } from "@/lib/api/client";

import { formatAge, QueueView } from "./QueueView";

const fetchMock = vi.fn<typeof fetch>();

function item(id: string, name: string, flags: string[] = []) {
  return {
    id,
    status: "IN_REVIEW",
    applicant_name: name,
    amount_vnd: 50_000_000,
    term_months: 12,
    flags,
    submitted_at: "2026-01-01T00:00:00Z",
    age_hours: 30,
  };
}

function lastQuery(): URLSearchParams {
  const url = String(fetchMock.mock.calls.at(-1)?.[0]);
  return new URLSearchParams(url.split("?")[1]);
}

beforeEach(() => {
  fetchMock.mockReset();
  fetchMock.mockImplementation(async () =>
    Response.json({
      items: [item("a1", "Nguyen An", ["exception"]), item("a2", "Tran Binh")],
      total: 2,
      limit: 50,
      offset: 0,
      message: null,
    }),
  );
  vi.stubGlobal("fetch", fetchMock);
  setAccessToken("tok");
});

describe("LF-010 QueueView", () => {
  it("lists applicant, amount, term, flags and age with a link to each file", async () => {
    render(<QueueView />);

    const link = await screen.findByRole("link", { name: "Nguyen An" });
    expect(link).toHaveAttribute("href", "/review/a1");
    const row = link.closest("tr")!;
    expect(row).toHaveTextContent("50,000,000 VND");
    expect(row).toHaveTextContent("12 months");
    expect(row).toHaveTextContent("Exception");
    expect(row).toHaveTextContent("30 h");
    expect(screen.getByRole("link", { name: "Tran Binh" }).closest("tr")).toHaveTextContent("None");
  });

  it("asks for oldest first and in-review files by default", async () => {
    render(<QueueView />);
    await screen.findByRole("link", { name: "Nguyen An" });

    expect(lastQuery().get("status")).toBe("IN_REVIEW");
    expect(lastQuery().get("sort")).toBe("oldest");
    expect(lastQuery().has("flag")).toBe(false);
  });

  it("sends the chosen flag and status filters", async () => {
    render(<QueueView />);
    await screen.findByRole("link", { name: "Nguyen An" });

    await userEvent.selectOptions(screen.getByLabelText("Flag"), "high_dti");
    await waitFor(() => expect(lastQuery().get("flag")).toBe("high_dti"));
    await userEvent.selectOptions(screen.getByLabelText("Status"), "SUBMITTED");
    await waitFor(() => expect(lastQuery().get("status")).toBe("SUBMITTED"));
    await userEvent.selectOptions(screen.getByLabelText("Order"), "newest");
    await waitFor(() => expect(lastQuery().get("sort")).toBe("newest"));
  });

  it("says No applications waiting when the queue is empty", async () => {
    fetchMock.mockImplementation(async () =>
      Response.json({ items: [], total: 0, limit: 50, offset: 0, message: "No applications waiting" }),
    );
    render(<QueueView />);

    expect(await screen.findByTestId("queue-empty")).toHaveTextContent("No applications waiting");
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("pages forward and back using the offset", async () => {
    fetchMock.mockImplementation(async () =>
      Response.json({ items: [item("a1", "Nguyen An")], total: 120, limit: 50, offset: 0, message: null }),
    );
    render(<QueueView />);
    await screen.findByRole("link", { name: "Nguyen An" });
    expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();

    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    await waitFor(() => expect(lastQuery().get("offset")).toBe("50"));
    await userEvent.click(screen.getByRole("button", { name: "Previous" }));
    await waitFor(() => expect(lastQuery().get("offset")).toBe("0"));
  });

  it("shows the server's message when the queue cannot be read", async () => {
    fetchMock.mockImplementation(async () =>
      Response.json({ detail: "You do not have permission to perform this action" }, { status: 403 }),
    );
    render(<QueueView />);

    expect(await screen.findByRole("alert")).toHaveTextContent("You do not have permission");
  });
});

describe("formatAge", () => {
  it("uses hours then days", () => {
    expect(formatAge(0.2)).toBe("under 1 hour");
    expect(formatAge(5.9)).toBe("5 h");
    expect(formatAge(72)).toBe("3 days");
    expect(formatAge(null)).toBe("");
  });
});

describe("LF-017 overdue files", () => {
  it("shows the Overdue flag and can filter to overdue and to referred files", async () => {
    fetchMock.mockImplementation(async () =>
      Response.json({
        items: [item("a1", "Nguyen An", ["exception", "overdue"])],
        total: 1,
        limit: 50,
        offset: 0,
        message: null,
      }),
    );
    render(<QueueView />);

    const row = (await screen.findByRole("link", { name: "Nguyen An" })).closest("tr")!;
    expect(row).toHaveTextContent("Exception, Overdue");

    await userEvent.selectOptions(screen.getByLabelText("Flag"), "overdue");
    await waitFor(() => expect(lastQuery().get("flag")).toBe("overdue"));

    await userEvent.selectOptions(screen.getByLabelText("Status"), "REFERRED");
    await waitFor(() => expect(lastQuery().get("status")).toBe("REFERRED"));
  });
});
