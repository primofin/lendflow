import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiRequest, getAccessToken, setAccessToken } from "./client";
import { ApiError } from "./errors";

const fetchMock = vi.fn<typeof fetch>();

function authHeader(call: unknown[]): string | undefined {
  const init = call[1] as RequestInit | undefined;
  return (init?.headers as Record<string, string> | undefined)?.Authorization;
}

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
  setAccessToken(null);
});

describe("apiRequest", () => {
  it("sends the access token and parses JSON", async () => {
    setAccessToken("tok-1");
    fetchMock.mockResolvedValueOnce(Response.json({ id: "a1" }));

    const result = await apiRequest<{ id: string }>("/api/applications/a1");

    expect(result).toEqual({ id: "a1" });
    expect(authHeader(fetchMock.mock.calls[0])).toBe("Bearer tok-1");
  });

  it("sends a JSON body with a content type, and a form body without one", async () => {
    fetchMock.mockImplementation(async () => Response.json({}));
    await apiRequest("/api/x", { method: "POST", json: { a: 1 } });
    const form = new FormData();
    form.set("doc_type", "national_id");
    await apiRequest("/api/y", { method: "POST", form });

    const jsonInit = fetchMock.mock.calls[0][1] as RequestInit;
    expect((jsonInit.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
    expect(jsonInit.body).toBe('{"a":1}');
    const formInit = fetchMock.mock.calls[1][1] as RequestInit;
    expect(formInit.body).toBe(form);
    expect((formInit.headers as Record<string, string>)["Content-Type"]).toBeUndefined();
  });

  it("returns undefined for 204", async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));
    await expect(apiRequest<void>("/api/auth/logout", { method: "POST" })).resolves.toBeUndefined();
  });

  it("throws the backend's message for failures", async () => {
    fetchMock.mockResolvedValueOnce(Response.json({ detail: "Not found" }, { status: 404 }));
    await expect(apiRequest("/api/applications/x")).rejects.toMatchObject({
      status: 404,
      message: "Not found",
    });
  });

  it("refreshes once on 401 and retries with the new token", async () => {
    setAccessToken("expired");
    fetchMock
      .mockResolvedValueOnce(Response.json({ detail: "Not authenticated" }, { status: 401 }))
      .mockResolvedValueOnce(Response.json({ access_token: "fresh" }))
      .mockResolvedValueOnce(Response.json({ ok: true }));

    const result = await apiRequest<{ ok: boolean }>("/api/queue");

    expect(result).toEqual({ ok: true });
    expect(fetchMock.mock.calls[1][0]).toBe("/api/auth/refresh");
    expect(authHeader(fetchMock.mock.calls[2])).toBe("Bearer fresh");
    expect(getAccessToken()).toBe("fresh");
  });

  it("gives up and clears the token when the refresh fails", async () => {
    setAccessToken("expired");
    fetchMock
      .mockResolvedValueOnce(Response.json({ detail: "Not authenticated" }, { status: 401 }))
      .mockResolvedValueOnce(Response.json({ detail: "Log in again" }, { status: 401 }));

    await expect(apiRequest("/api/queue")).rejects.toBeInstanceOf(ApiError);
    expect(getAccessToken()).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(2); // no retry loop
  });

  it("shares one refresh between parallel requests (refresh tokens rotate)", async () => {
    setAccessToken("expired");
    fetchMock.mockImplementation(async (input, init) => {
      if (input === "/api/auth/refresh") return Response.json({ access_token: "fresh" });
      const bearer = (init?.headers as Record<string, string>).Authorization;
      return bearer === "Bearer fresh"
        ? Response.json({ ok: true })
        : Response.json({ detail: "Not authenticated" }, { status: 401 });
    });

    await Promise.all([apiRequest("/api/a"), apiRequest("/api/b"), apiRequest("/api/c")]);

    const refreshes = fetchMock.mock.calls.filter(([url]) => url === "/api/auth/refresh");
    expect(refreshes).toHaveLength(1);
  });

  it("does not try to refresh when no one is logged in", async () => {
    fetchMock.mockResolvedValueOnce(Response.json({ detail: "Incorrect email or password" }, { status: 401 }));
    await expect(
      apiRequest("/api/auth/login", { method: "POST", json: { email: "a", password: "b" } }),
    ).rejects.toMatchObject({ message: "Incorrect email or password" });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
