import { vi } from "vitest";

import type { User } from "@/lib/api/types";

export const replace = vi.fn();

/** Shared stand-in for next/navigation: tests assert on `replace`. */
export const navigationMock = () => ({
  useRouter: () => ({ replace, push: vi.fn() }),
});

export function user(role: User["role"], email = `${role}@example.com`): User {
  return { id: `id-${role}`, email, role };
}
