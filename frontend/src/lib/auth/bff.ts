/** Helpers for the /api/auth route handlers, written against plain Web APIs so they are easy to
 * test. The backend returns both tokens in the body; here the refresh token moves into an
 * httpOnly cookie and only the short-lived access token is handed to the page. */

export const REFRESH_COOKIE = "lf_refresh";
const COOKIE_PATH = "/api/auth";
const REFRESH_DAYS = 7; // matches REFRESH_TOKEN_TTL_DAYS in the backend

export function backendUrl(): string {
  return process.env.BACKEND_URL ?? "http://localhost:8000";
}

function cookieFlags(): string {
  const secure = process.env.NODE_ENV === "production" ? "; Secure" : "";
  return `Path=${COOKIE_PATH}; HttpOnly; SameSite=Strict${secure}`;
}

export function refreshCookie(token: string): string {
  const maxAge = REFRESH_DAYS * 24 * 60 * 60;
  return `${REFRESH_COOKIE}=${encodeURIComponent(token)}; ${cookieFlags()}; Max-Age=${maxAge}`;
}

export function clearedRefreshCookie(): string {
  return `${REFRESH_COOKIE}=; ${cookieFlags()}; Max-Age=0`;
}

export function readRefreshToken(request: Request): string | null {
  const header = request.headers.get("cookie") ?? "";
  for (const part of header.split(";")) {
    const [name, ...rest] = part.trim().split("=");
    if (name === REFRESH_COOKIE && rest.length > 0)
      return decodeURIComponent(rest.join("="));
  }
  return null;
}

/** Forward a failed backend response unchanged (status and `detail`), so messages stay specific. */
export async function passThroughError(upstream: Response): Promise<Response> {
  const text = await upstream.text();
  return new Response(text, {
    status: upstream.status,
    headers: {
      "Content-Type":
        upstream.headers.get("content-type") ?? "application/json",
    },
  });
}

type TokenPair = { access_token: string; refresh_token: string };

/** Turn a backend token response into: access token in the body, refresh token in the cookie. */
export async function tokenResponse(
  upstream: Response,
  status = 200,
): Promise<Response> {
  if (!upstream.ok) {
    const failure = await passThroughError(upstream);
    if (upstream.status === 401)
      failure.headers.append("Set-Cookie", clearedRefreshCookie());
    return failure;
  }
  const pair = (await upstream.json()) as TokenPair;
  const response = Response.json(
    { access_token: pair.access_token },
    { status },
  );
  response.headers.append("Set-Cookie", refreshCookie(pair.refresh_token));
  return response;
}

/** Header the host's proxy sets to the real client address (Fly sets it and overwrites any
 * client-sent value). Forwarded so the API's audit log and rate limit see the visitor, not this
 * server; the API only trusts it when CLIENT_IP_HEADER names it. */
const CLIENT_IP_HEADER = "fly-client-ip";

export function postJson(
  path: string,
  body: string,
  incoming: Request,
): Promise<Response> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  const clientIp = incoming.headers.get(CLIENT_IP_HEADER);
  if (clientIp) headers[CLIENT_IP_HEADER] = clientIp;
  return fetch(`${backendUrl()}${path}`, {
    method: "POST",
    headers,
    body,
    cache: "no-store",
  });
}
