import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { setAccessToken } from "@/lib/api/client";

import { RemindersPanel } from "./RemindersPanel";

const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
  setAccessToken("tok");
});

describe("LF-014 RemindersPanel", () => {
  it("queues the due reminders and reports how many", async () => {
    fetchMock.mockResolvedValue(Response.json({ queued: 3 }));
    render(<RemindersPanel />);

    await userEvent.click(screen.getByRole("button", { name: "Send due reminders now" }));

    expect(await screen.findByTestId("reminders-result")).toHaveTextContent("3 reminders queued.");
    expect(String(fetchMock.mock.calls[0][0])).toBe("/api/reminders/run");
    expect(fetchMock.mock.calls[0][1]?.method).toBe("POST");
  });

  it("uses the singular for one and says none when there is nothing due", async () => {
    fetchMock.mockResolvedValueOnce(Response.json({ queued: 1 })).mockResolvedValueOnce(Response.json({ queued: 0 }));
    render(<RemindersPanel />);
    const button = screen.getByRole("button", { name: "Send due reminders now" });

    await userEvent.click(button);
    expect(await screen.findByText("1 reminder queued.")).toBeInTheDocument();
    await userEvent.click(button);
    expect(await screen.findByText("0 reminders queued.")).toBeInTheDocument();
  });

  it("shows the server's refusal", async () => {
    fetchMock.mockResolvedValue(Response.json({ detail: "You do not have permission to perform this action" }, { status: 403 }));
    render(<RemindersPanel />);

    await userEvent.click(screen.getByRole("button", { name: "Send due reminders now" }));

    expect(await screen.findByText("You do not have permission to perform this action")).toBeInTheDocument();
    expect(screen.queryByTestId("reminders-result")).not.toBeInTheDocument();
  });
});
