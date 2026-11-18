import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { setAccessToken } from "@/lib/api/client";

import { ReminderSettingsForm } from "./ReminderSettingsForm";

const fetchMock = vi.fn<typeof fetch>();
let on: boolean;

beforeEach(() => {
  on = true;
  fetchMock.mockReset();
  fetchMock.mockImplementation(async (_input, init) => {
    if (init?.method === "PUT") {
      on = JSON.parse(String(init.body)).repayment_reminders;
    }
    return Response.json({ repayment_reminders: on });
  });
  vi.stubGlobal("fetch", fetchMock);
  setAccessToken("tok");
});

describe("LF-014 ReminderSettingsForm", () => {
  it("shows reminders on by default and saves an opt-out and an opt-back-in", async () => {
    render(<ReminderSettingsForm />);
    const box = await screen.findByRole("checkbox", { name: "Email me before each repayment is due" });
    expect(box).toBeChecked();

    await userEvent.click(box);
    await waitFor(() => expect(screen.getByTestId("settings-saved")).toHaveTextContent("Reminders are off."));
    expect(box).not.toBeChecked();
    const put = fetchMock.mock.calls.find(([, init]) => init?.method === "PUT")!;
    expect(String(put[0])).toBe("/api/me/settings");
    expect(JSON.parse(String(put[1]?.body))).toEqual({ repayment_reminders: false });

    await userEvent.click(box);
    await waitFor(() => expect(screen.getByTestId("settings-saved")).toHaveTextContent("Reminders are on."));
  });

  it("says what is sent and that amounts are never in the email", async () => {
    render(<ReminderSettingsForm />);

    expect(await screen.findByText(/7 days and 1 day before/)).toBeInTheDocument();
    expect(screen.getByText(/never amounts/)).toBeInTheDocument();
  });

  it("shows the server's refusal and leaves the box as it was", async () => {
    fetchMock.mockImplementation(async (_input, init) =>
      init?.method === "PUT"
        ? Response.json({ detail: "You do not have permission to perform this action" }, { status: 403 })
        : Response.json({ repayment_reminders: true }),
    );
    render(<ReminderSettingsForm />);
    const box = await screen.findByRole("checkbox");

    await userEvent.click(box);

    expect(await screen.findByText("You do not have permission to perform this action")).toBeInTheDocument();
    expect(box).toBeChecked();
    expect(screen.queryByTestId("settings-saved")).not.toBeInTheDocument();
  });
});
