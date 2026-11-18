import { postJson, readRefreshToken, tokenResponse } from "@/lib/auth/bff";

/** LF-001: exchange the refresh cookie for a new access token (the backend rotates it). */
export async function POST(request: Request): Promise<Response> {
  const token = readRefreshToken(request);
  if (token === null) {
    return Response.json({ detail: "Not authenticated. Log in again." }, { status: 401 });
  }
  return tokenResponse(await postJson("/auth/refresh", JSON.stringify({ refresh_token: token })));
}
