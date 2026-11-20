import { postJson, tokenResponse } from "@/lib/auth/bff";

/** LF-001: create a borrower account and log in. */
export async function POST(request: Request): Promise<Response> {
  return tokenResponse(
    await postJson("/auth/register", await request.text(), request),
    201,
  );
}
