import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiRequest, getAccessToken, setAccessToken } from "@/lib/api/client";

import { AuthProvider, useAuth } from "./AuthProvider";

const fetchMock = vi.fn<typeof fetch>();
const officer = { id: "u1", email: "officer@example.com", role: "officer" };

function Probe() {
  const { status, user, sessionEndedMessage, login, logout } = useAuth();
  return (
    <div>
      <p data-testid="status">{status}</p>
      <p data-testid="role">{user?.role ?? "none"}</p>
      <p data-testid="ended">{sessionEndedMessage ?? "no message"}</p>
      <button onClick={() => apiRequest("/api/queue").catch(() => undefined)}>
        call
      </button>
      <button
        onClick={() =>
          login("officer@example.com", "pw").catch(() => undefined)
        }
      >
        login
      </button>
      <button onClick={() => logout()}>logout</button>
    </div>
  );
}

function renderProbe() {
  return render(
    <AuthProvider>
      <Probe />
    </AuthProvider>,
  );
}

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
  setAccessToken(null);
});

describe("AuthProvider", () => {
  it("is anonymous when there is no refresh cookie", async () => {
    fetchMock.mockResolvedValueOnce(
      Response.json({ detail: "Not authenticated" }, { status: 401 }),
    );

    renderProbe();

    await waitFor(() =>
      expect(screen.getByTestId("status")).toHaveTextContent("anonymous"),
    );
    expect(screen.getByTestId("role")).toHaveTextContent("none");
  });

  it("restores the session from the refresh cookie on first load", async () => {
    fetchMock
      .mockResolvedValueOnce(Response.json({ access_token: "a1" }))
      .mockResolvedValueOnce(Response.json(officer));

    renderProbe();

    await waitFor(() =>
      expect(screen.getByTestId("status")).toHaveTextContent("authenticated"),
    );
    expect(screen.getByTestId("role")).toHaveTextContent("officer");
    expect(getAccessToken()).toBe("a1");
  });

  it("logs in, then logs out and forgets the token", async () => {
    fetchMock.mockResolvedValueOnce(
      Response.json({ detail: "x" }, { status: 401 }),
    ); // first load
    renderProbe();
    await waitFor(() =>
      expect(screen.getByTestId("status")).toHaveTextContent("anonymous"),
    );

    fetchMock
      .mockResolvedValueOnce(Response.json({ access_token: "a2" })) // login
      .mockResolvedValueOnce(Response.json(officer)); // /auth/me
    await userEvent.click(screen.getByText("login"));
    await waitFor(() =>
      expect(screen.getByTestId("status")).toHaveTextContent("authenticated"),
    );

    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));
    await userEvent.click(screen.getByText("logout"));
    await waitFor(() =>
      expect(screen.getByTestId("status")).toHaveTextContent("anonymous"),
    );
    expect(getAccessToken()).toBeNull();
  });

  it("stays anonymous when login is refused", async () => {
    fetchMock.mockResolvedValueOnce(
      Response.json({ detail: "x" }, { status: 401 }),
    );
    renderProbe();
    await waitFor(() =>
      expect(screen.getByTestId("status")).toHaveTextContent("anonymous"),
    );

    fetchMock.mockResolvedValueOnce(
      Response.json({ detail: "Incorrect email or password" }, { status: 401 }),
    );
    await userEvent.click(screen.getByText("login"));

    expect(screen.getByTestId("status")).toHaveTextContent("anonymous");
    expect(getAccessToken()).toBeNull();
  });

  it("signs the user out with an explanation when the session can no longer be renewed", async () => {
    fetchMock
      .mockResolvedValueOnce(Response.json({ access_token: "a1" })) // first load
      .mockResolvedValueOnce(Response.json(officer));
    renderProbe();
    await waitFor(() =>
      expect(screen.getByTestId("status")).toHaveTextContent("authenticated"),
    );

    fetchMock
      .mockResolvedValueOnce(
        Response.json({ detail: "Not authenticated" }, { status: 401 }),
      ) // idle
      .mockResolvedValueOnce(
        Response.json({ detail: "Log in again" }, { status: 401 }),
      ); // refresh
    await userEvent.click(screen.getByText("call"));

    await waitFor(() =>
      expect(screen.getByTestId("status")).toHaveTextContent("anonymous"),
    );
    expect(screen.getByTestId("ended")).toHaveTextContent(
      "signed out after being idle",
    );
    expect(screen.getByTestId("role")).toHaveTextContent("none");
  });

  it("clears the idle message at the next login", async () => {
    fetchMock
      .mockResolvedValueOnce(Response.json({ access_token: "a1" }))
      .mockResolvedValueOnce(Response.json(officer));
    renderProbe();
    await waitFor(() =>
      expect(screen.getByTestId("status")).toHaveTextContent("authenticated"),
    );
    fetchMock
      .mockResolvedValueOnce(Response.json({ detail: "x" }, { status: 401 }))
      .mockResolvedValueOnce(Response.json({ detail: "x" }, { status: 401 }));
    await userEvent.click(screen.getByText("call"));
    await waitFor(() =>
      expect(screen.getByTestId("ended")).toHaveTextContent("idle"),
    );

    fetchMock
      .mockResolvedValueOnce(Response.json({ access_token: "a2" }))
      .mockResolvedValueOnce(Response.json(officer));
    await userEvent.click(screen.getByText("login"));

    await waitFor(() =>
      expect(screen.getByTestId("ended")).toHaveTextContent("no message"),
    );
  });
});
