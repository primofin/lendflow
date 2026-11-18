/** Browser API client. The access token lives in memory only; the refresh token is an httpOnly
 * cookie managed by the /api/auth route handlers, so page scripts never see it. */

import { ApiError, errorFromResponse } from "./errors";

let accessToken: string | null = null;
let refreshing: Promise<string | null> | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

/** One refresh at a time: parallel 401s share a single request (refresh tokens rotate). */
export function refreshAccessToken(): Promise<string | null> {
  refreshing ??= (async () => {
    try {
      const response = await fetch("/api/auth/refresh", { method: "POST" });
      if (!response.ok) {
        accessToken = null;
        return null;
      }
      const body = (await response.json()) as { access_token: string };
      accessToken = body.access_token;
      return accessToken;
    } catch {
      accessToken = null;
      return null;
    } finally {
      refreshing = null;
    }
  })();
  return refreshing;
}

export type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  json?: unknown;
  form?: FormData;
  signal?: AbortSignal;
};

function send(path: string, options: RequestOptions, token: string | null): Promise<Response> {
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  let body: BodyInit | undefined;
  if (options.form) {
    body = options.form; // the browser sets the multipart boundary itself
  } else if (options.json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.json);
  }
  return fetch(path, { method: options.method ?? "GET", headers, body, signal: options.signal });
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  let response = await send(path, options, accessToken);
  if (response.status === 401 && accessToken !== null) {
    const fresh = await refreshAccessToken();
    if (fresh) response = await send(path, options, fresh);
  }
  if (!response.ok) throw await errorFromResponse(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export { ApiError };
