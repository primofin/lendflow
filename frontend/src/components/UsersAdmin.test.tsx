import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { setAccessToken } from "@/lib/api/client";

import { UsersAdmin } from "./UsersAdmin";

const fetchMock = vi.fn<typeof fetch>();

const users = [
  {
    id: "u1",
    email: "boss@example.com",
    role: "supervisor",
    is_active: true,
    created_at: "",
  },
  {
    id: "u2",
    email: "ana@example.com",
    role: "officer",
    is_active: true,
    created_at: "",
  },
];

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
  setAccessToken("tok");
});

function calls(method: string) {
  return fetchMock.mock.calls.filter(
    ([, init]) => (init?.method ?? "GET") === method,
  );
}

describe("UsersAdmin", () => {
  it("lists users with their roles", async () => {
    fetchMock.mockResolvedValueOnce(Response.json(users));
    render(<UsersAdmin />);

    expect(await screen.findByText("ana@example.com")).toBeInTheDocument();
    expect(screen.getByLabelText("Role for ana@example.com")).toHaveValue(
      "officer",
    );
  });

  it("creates a user with the chosen role, then reloads the list", async () => {
    fetchMock
      .mockResolvedValueOnce(Response.json(users))
      .mockResolvedValueOnce(
        Response.json(
          { ...users[1], id: "u3", email: "new@example.com" },
          { status: 201 },
        ),
      )
      .mockResolvedValueOnce(Response.json(users));
    render(<UsersAdmin />);
    await screen.findByText("ana@example.com");

    await userEvent.type(screen.getByLabelText("Email"), "new@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "long-enough-pw");
    await userEvent.selectOptions(screen.getByLabelText("Role"), "officer");
    await userEvent.click(screen.getByRole("button", { name: "Create user" }));

    expect(await screen.findByRole("status")).toHaveTextContent(
      "Created new@example.com as officer.",
    );
    const [path, init] = calls("POST")[0];
    expect(path).toBe("/api/users");
    expect(JSON.parse(init?.body as string)).toEqual({
      email: "new@example.com",
      password: "long-enough-pw",
      role: "officer",
    });
    expect(screen.getByLabelText("Email")).toHaveValue("");
  });

  it("shows the API's message when creation is refused", async () => {
    fetchMock
      .mockResolvedValueOnce(Response.json(users))
      .mockResolvedValueOnce(
        Response.json(
          { detail: "This email is already registered" },
          { status: 409 },
        ),
      );
    render(<UsersAdmin />);
    await screen.findByText("ana@example.com");

    await userEvent.type(screen.getByLabelText("Email"), "ana@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "long-enough-pw");
    await userEvent.click(screen.getByRole("button", { name: "Create user" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "This email is already registered",
    );
  });

  it("changes a role through the API", async () => {
    fetchMock
      .mockResolvedValueOnce(Response.json(users))
      .mockResolvedValueOnce(Response.json({ ...users[1], role: "supervisor" }))
      .mockResolvedValueOnce(
        Response.json([users[0], { ...users[1], role: "supervisor" }]),
      );
    render(<UsersAdmin />);
    await userEvent.selectOptions(
      await screen.findByLabelText("Role for ana@example.com"),
      "supervisor",
    );

    expect(await screen.findByRole("status")).toHaveTextContent(
      "ana@example.com is now supervisor.",
    );
    expect(calls("PATCH")[0][0]).toBe("/api/users/u2/role");
    expect(JSON.parse(calls("PATCH")[0][1]?.body as string)).toEqual({
      role: "supervisor",
    });
  });

  it("shows a refused role change and puts the select back to what the server holds", async () => {
    fetchMock
      .mockResolvedValueOnce(Response.json(users))
      .mockResolvedValueOnce(
        Response.json(
          { detail: "You cannot change your own role" },
          { status: 409 },
        ),
      )
      .mockResolvedValueOnce(Response.json(users));
    render(<UsersAdmin />);
    const select = await screen.findByLabelText("Role for boss@example.com");

    await userEvent.selectOptions(select, "officer");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "You cannot change your own role",
    );
    await waitFor(() =>
      expect(screen.getByLabelText("Role for boss@example.com")).toHaveValue(
        "supervisor",
      ),
    );
    const row = screen.getByText("boss@example.com").closest("tr");
    expect(row && within(row).getByRole("combobox")).toHaveValue("supervisor");
  });

  it("explains a refusal to load (for example a non-supervisor reaching the page)", async () => {
    fetchMock.mockResolvedValueOnce(
      Response.json(
        { detail: "You do not have permission to perform this action" },
        { status: 403 },
      ),
    );
    render(<UsersAdmin />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "do not have permission",
    );
  });
});
