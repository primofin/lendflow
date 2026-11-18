import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { replace, user } from "@/test-utils";

import { SiteHeader } from "./SiteHeader";

vi.mock("next/navigation", async () =>
  (await import("@/test-utils")).navigationMock(),
);

const logout = vi.fn();
const auth: {
  status: string;
  user: ReturnType<typeof user> | null;
  logout: typeof logout;
} = {
  status: "anonymous",
  user: null,
  logout,
};
vi.mock("@/lib/auth/AuthProvider", () => ({ useAuth: () => auth }));

beforeEach(() => {
  replace.mockClear();
  logout.mockReset().mockResolvedValue(undefined);
});

describe("SiteHeader (LF-002 AC3: only supervisors see user management)", () => {
  it("offers log in and register to anonymous visitors", () => {
    auth.status = "anonymous";
    auth.user = null;
    render(<SiteHeader />);

    expect(screen.getByRole("link", { name: "Log in" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Register" })).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Users" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Log out" }),
    ).not.toBeInTheDocument();
  });

  it.each(["borrower", "officer"] as const)(
    "hides the Users menu from a %s",
    (role) => {
      auth.status = "authenticated";
      auth.user = user(role);
      render(<SiteHeader />);

      expect(
        screen.queryByRole("link", { name: "Users" }),
      ).not.toBeInTheDocument();
      expect(
        screen.getByText(`${role}@example.com (${role})`),
      ).toBeInTheDocument();
    },
  );

  it("shows the Users menu to a supervisor", () => {
    auth.status = "authenticated";
    auth.user = user("supervisor");
    render(<SiteHeader />);

    expect(screen.getByRole("link", { name: "Users" })).toHaveAttribute(
      "href",
      "/admin/users",
    );
  });

  it("logs out and returns to the login page", async () => {
    auth.status = "authenticated";
    auth.user = user("officer");
    render(<SiteHeader />);

    await userEvent.click(screen.getByRole("button", { name: "Log out" }));

    expect(logout).toHaveBeenCalled();
    expect(replace).toHaveBeenCalledWith("/login");
  });
});
