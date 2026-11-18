import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/errors";
import { replace } from "@/test-utils";

import { CredentialsForm } from "./CredentialsForm";

vi.mock("next/navigation", async () =>
  (await import("@/test-utils")).navigationMock(),
);

const auth = {
  status: "anonymous" as "anonymous" | "authenticated",
  user: null,
  sessionEndedMessage: null as string | null,
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
};
vi.mock("@/lib/auth/AuthProvider", () => ({ useAuth: () => auth }));

beforeEach(() => {
  replace.mockClear();
  auth.status = "anonymous";
  auth.sessionEndedMessage = null;
  auth.login.mockReset();
  auth.register.mockReset();
});

async function fill(email: string, password: string) {
  await userEvent.type(screen.getByLabelText("Email"), email);
  await userEvent.type(screen.getByLabelText("Password"), password);
}

describe("login form", () => {
  it("logs in with a trimmed email and goes home", async () => {
    auth.login.mockResolvedValue(undefined);
    render(<CredentialsForm mode="login" />);

    await fill("  ana@example.com ", "secret-password");
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));

    expect(auth.login).toHaveBeenCalledWith(
      "ana@example.com",
      "secret-password",
    );
    expect(replace).toHaveBeenCalledWith("/");
  });

  it("empties the password field after a successful login", async () => {
    auth.login.mockResolvedValue(undefined);
    render(<CredentialsForm mode="login" />);

    await fill("ana@example.com", "secret-password");
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));

    expect(replace).toHaveBeenCalledWith("/");
    expect(screen.getByLabelText("Password")).toHaveValue("");
  });

  it("shows the API's message and stays on the page when login fails", async () => {
    auth.login.mockRejectedValue(
      new ApiError(401, "Incorrect email or password"),
    );
    render(<CredentialsForm mode="login" />);

    await fill("ana@example.com", "wrong-password");
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Incorrect email or password",
    );
    expect(replace).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Log in" })).toBeEnabled();
  });

  it("shows the lockout message as written by the backend", async () => {
    auth.login.mockRejectedValue(
      new ApiError(
        423,
        "Too many failed attempts. The account is locked for 15 minutes; try again later.",
      ),
    );
    render(<CredentialsForm mode="login" />);

    await fill("ana@example.com", "wrong-password");
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "locked for 15 minutes",
    );
  });

  it("falls back to a plain message for an unexpected failure", async () => {
    auth.login.mockRejectedValue(new TypeError("network"));
    render(<CredentialsForm mode="login" />);

    await fill("ana@example.com", "pw");
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Something went wrong. Try again.",
    );
  });

  it("disables the button while the request is in flight", async () => {
    let finish: () => void = () => undefined;
    auth.login.mockReturnValue(
      new Promise<void>((resolve) => (finish = resolve)),
    );
    render(<CredentialsForm mode="login" />);

    await fill("ana@example.com", "pw");
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));

    expect(screen.getByRole("button", { name: "Please wait…" })).toBeDisabled();
    finish();
  });

  it("explains an idle sign-out", () => {
    auth.sessionEndedMessage =
      "You were signed out after being idle. Log in again to continue.";
    render(<CredentialsForm mode="login" />);

    expect(screen.getByRole("status")).toHaveTextContent(
      "signed out after being idle",
    );
  });

  it("sends a user who is already logged in home", () => {
    auth.status = "authenticated";
    render(<CredentialsForm mode="login" />);

    expect(replace).toHaveBeenCalledWith("/");
  });
});

describe("register form", () => {
  it("states the password policy and registers", async () => {
    auth.register.mockResolvedValue(undefined);
    render(<CredentialsForm mode="register" />);

    expect(screen.getByLabelText("Password")).toHaveAccessibleDescription(
      "At least 10 characters.",
    );
    await fill("new@example.com", "long-enough-pw");
    await userEvent.click(
      screen.getByRole("button", { name: "Create account" }),
    );

    expect(auth.register).toHaveBeenCalledWith(
      "new@example.com",
      "long-enough-pw",
    );
    expect(auth.login).not.toHaveBeenCalled();
    expect(replace).toHaveBeenCalledWith("/");
  });

  it("shows 'This email is already registered' and creates nothing locally", async () => {
    auth.register.mockRejectedValue(
      new ApiError(409, "This email is already registered"),
    );
    render(<CredentialsForm mode="register" />);

    await fill("taken@example.com", "long-enough-pw");
    await userEvent.click(
      screen.getByRole("button", { name: "Create account" }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "This email is already registered",
    );
    expect(replace).not.toHaveBeenCalled();
  });

  it("shows the policy message when the password is too short", async () => {
    auth.register.mockRejectedValue(
      new ApiError(422, "password: Password must be at least 10 characters"),
    );
    render(<CredentialsForm mode="register" />);

    await fill("new@example.com", "short");
    await userEvent.click(
      screen.getByRole("button", { name: "Create account" }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "at least 10 characters",
    );
  });

  it("does not show the idle message on the register page", () => {
    auth.sessionEndedMessage =
      "You were signed out after being idle. Log in again to continue.";
    render(<CredentialsForm mode="register" />);

    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});
