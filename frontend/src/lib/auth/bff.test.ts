// @vitest-environment node
import { beforeEach, describe, expect, it, vi } from "vitest";

import { POST as login } from "@/app/api/auth/login/route";
import { POST as logout } from "@/app/api/auth/logout/route";
import { POST as refresh } from "@/app/api/auth/refresh/route";
import { POST as register } from "@/app/api/auth/register/route";

const fetchMock = vi.fn<typeof fetch>();
const pair = { access_token: "access-1", refresh_token: "refresh-1", token_type: "bearer" };

function post(url: string, body?: unknown, headers: Record<string, string> = {}): Request {
  return new Request(`http://localhost:3000${url}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});

describe("login", () => {
  it("puts the refresh token in an httpOnly cookie and keeps it out of the body", async () => {
    fetchMock.mockResolvedValueOnce(Response.json(pair));

    const response = await login(post("/api/auth/login", { email: "a@example.com", password: "x" }));

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ access_token: "access-1" });
    const cookie = response.headers.get("set-cookie") ?? "";
    expect(cookie).toContain("lf_refresh=refresh-1");
    expect(cookie).toContain("HttpOnly");
    expect(cookie).toContain("SameSite=Strict");
    expect(cookie).toContain("Path=/api/auth");
    expect(fetchMock.mock.calls[0][0]).toBe("http://localhost:8000/auth/login");
  });

  it("forwards the backend's error and sets no session cookie", async () => {
    fetchMock.mockResolvedValueOnce(
      Response.json({ detail: "Incorrect email or password" }, { status: 401 }),
    );

    const response = await login(post("/api/auth/login", { email: "a@example.com", password: "x" }));

    expect(response.status).toBe(401);
    expect(await response.json()).toEqual({ detail: "Incorrect email or password" });
    expect(response.headers.get("set-cookie")).toContain("Max-Age=0"); // stale cookie cleared
    expect(response.headers.get("set-cookie")).not.toContain("refresh-1");
  });

  it("passes an account lock (423) through with its message", async () => {
    fetchMock.mockResolvedValueOnce(
      Response.json({ detail: "Account locked. Try again in 15 minutes." }, { status: 423 }),
    );

    const response = await login(post("/api/auth/login", { email: "a@example.com", password: "x" }));

    expect(response.status).toBe(423);
    expect((await response.json()).detail).toContain("15 minutes");
  });
});

describe("register", () => {
  it("returns 201 with the same cookie handling", async () => {
    fetchMock.mockResolvedValueOnce(Response.json(pair, { status: 201 }));

    const response = await register(post("/api/auth/register", { email: "a@example.com", password: "long-enough-1" }));

    expect(response.status).toBe(201);
    expect(response.headers.get("set-cookie")).toContain("lf_refresh=refresh-1");
    expect(await response.json()).toEqual({ access_token: "access-1" });
  });
});

describe("refresh", () => {
  it("refuses without a cookie and does not call the backend", async () => {
    const response = await refresh(post("/api/auth/refresh"));

    expect(response.status).toBe(401);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("sends the cookie's token to the backend and stores the rotated one", async () => {
    fetchMock.mockResolvedValueOnce(
      Response.json({ ...pair, access_token: "access-2", refresh_token: "refresh-2" }),
    );

    const response = await refresh(post("/api/auth/refresh", undefined, { Cookie: "lf_refresh=refresh-1" }));

    expect(JSON.parse(fetchMock.mock.calls[0][1]?.body as string)).toEqual({ refresh_token: "refresh-1" });
    expect(await response.json()).toEqual({ access_token: "access-2" });
    expect(response.headers.get("set-cookie")).toContain("lf_refresh=refresh-2");
  });

  it("clears the cookie when the backend rejects the token (reuse or expiry)", async () => {
    fetchMock.mockResolvedValueOnce(Response.json({ detail: "Not authenticated. Log in again." }, { status: 401 }));

    const response = await refresh(post("/api/auth/refresh", undefined, { Cookie: "a=b; lf_refresh=stale" }));

    expect(response.status).toBe(401);
    expect(response.headers.get("set-cookie")).toContain("Max-Age=0");
  });
});

describe("logout", () => {
  it("ends the backend session with the bearer token and clears the cookie", async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));

    const response = await logout(post("/api/auth/logout", undefined, { Authorization: "Bearer access-1" }));

    expect(response.status).toBe(204);
    expect(response.headers.get("set-cookie")).toContain("Max-Age=0");
    expect((fetchMock.mock.calls[0][1]?.headers as Record<string, string>).Authorization).toBe("Bearer access-1");
  });

  it("clears the cookie even if the backend is down", async () => {
    fetchMock.mockRejectedValueOnce(new Error("connect ECONNREFUSED"));

    const response = await logout(post("/api/auth/logout", undefined, { Authorization: "Bearer access-1" }));

    expect(response.status).toBe(204);
    expect(response.headers.get("set-cookie")).toContain("Max-Age=0");
  });
});
