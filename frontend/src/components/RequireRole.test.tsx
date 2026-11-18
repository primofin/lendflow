import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { replace, user } from "@/test-utils";

import { RequireRole } from "./RequireRole";

vi.mock("next/navigation", async () =>
  (await import("@/test-utils")).navigationMock(),
);

const auth: { status: string; user: ReturnType<typeof user> | null } = {
  status: "loading",
  user: null,
};
vi.mock("@/lib/auth/AuthProvider", () => ({ useAuth: () => auth }));

beforeEach(() => replace.mockClear());

function renderGuard() {
  return render(
    <RequireRole roles={["supervisor"]}>
      <p>secret admin page</p>
    </RequireRole>,
  );
}

describe("RequireRole", () => {
  it("shows nothing protected while the session is loading", () => {
    auth.status = "loading";
    auth.user = null;
    renderGuard();

    expect(screen.queryByText("secret admin page")).not.toBeInTheDocument();
    expect(replace).not.toHaveBeenCalled();
  });

  it("sends an anonymous visitor to log in", () => {
    auth.status = "anonymous";
    auth.user = null;
    renderGuard();

    expect(replace).toHaveBeenCalledWith("/login");
    expect(screen.queryByText("secret admin page")).not.toBeInTheDocument();
  });

  it.each(["borrower", "officer"] as const)(
    "refuses a %s with a clear message",
    (role) => {
      auth.status = "authenticated";
      auth.user = user(role);
      renderGuard();

      expect(screen.getByRole("alert")).toHaveTextContent(
        "You do not have access to this page.",
      );
      expect(screen.queryByText("secret admin page")).not.toBeInTheDocument();
    },
  );

  it("shows the page to a supervisor", () => {
    auth.status = "authenticated";
    auth.user = user("supervisor");
    renderGuard();

    expect(screen.getByText("secret admin page")).toBeInTheDocument();
  });
});
