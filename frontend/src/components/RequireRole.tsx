"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import type { ReactNode } from "react";

import type { Role } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";

/** Hides a page from the wrong audience. This is a courtesy: the API enforces access (LF-002). */
export function RequireRole({
  roles,
  children,
}: {
  roles: Role[];
  children: ReactNode;
}) {
  const { status, user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "anonymous") router.replace("/login");
  }, [status, router]);

  if (status === "loading") return <p className="px-4 py-10">Loading…</p>;
  if (status === "anonymous")
    return <p className="px-4 py-10">Redirecting to log in…</p>;
  if (user && !roles.includes(user.role)) {
    return (
      <p role="alert" className="mx-auto max-w-3xl px-4 py-10">
        You do not have access to this page.
      </p>
    );
  }
  return <>{children}</>;
}
