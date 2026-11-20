import { postJson, tokenResponse } from "@/lib/auth/bff";

/** LF-001: log in. The refresh token goes into an httpOnly cookie, never into the page. */
export async function POST(request: Request): Promise<Response> {
  return tokenResponse(
    await postJson("/auth/login", await request.text(), request),
  );
}
