import { backendUrl, clearedRefreshCookie } from "@/lib/auth/bff";

/** LF-001: end the session on the backend and always clear the cookie. */
export async function POST(request: Request): Promise<Response> {
  const authorization = request.headers.get("authorization");
  if (authorization) {
    try {
      await fetch(`${backendUrl()}/auth/logout`, {
        method: "POST",
        headers: { Authorization: authorization },
        cache: "no-store",
      });
    } catch {
      // The backend session expires on its own; the cookie is cleared regardless.
    }
  }
  const response = new Response(null, { status: 204 });
  response.headers.append("Set-Cookie", clearedRefreshCookie());
  return response;
}
