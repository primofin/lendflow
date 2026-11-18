"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { useAuth } from "@/lib/auth/AuthProvider";

const link = "text-blue-800 underline underline-offset-2";

export function SiteHeader() {
  const { status, user, logout } = useAuth();
  const router = useRouter();

  async function leave() {
    await logout();
    router.replace("/login");
  }

  return (
    <header className="border-b border-slate-200">
      <nav
        aria-label="Main"
        className="mx-auto flex max-w-3xl flex-wrap items-center gap-4 px-4 py-3"
      >
        <Link href="/" className="mr-auto text-lg font-semibold">
          LendFlow
        </Link>
        <Link href="/calculator" className={link}>
          Calculator
        </Link>
        {user?.role === "borrower" && (
          <Link href="/apply" className={link}>
            Apply
          </Link>
        )}
        {status === "anonymous" && (
          <>
            <Link href="/login" className={link}>
              Log in
            </Link>
            <Link href="/register" className={link}>
              Register
            </Link>
          </>
        )}
        {user?.role === "borrower" && (
          <Link href="/my-data" className={link}>
            My data
          </Link>
        )}
        {(user?.role === "officer" || user?.role === "supervisor") && (
          <>
            <Link href="/queue" className={link}>
              Queue
            </Link>
            <Link href="/import" className={link}>
              Import
            </Link>
          </>
        )}
        {user?.role === "supervisor" && (
          <>
            <Link href="/admin/dashboard" className={link}>
              Dashboard
            </Link>
            <Link href="/admin/users" className={link}>
              Users
            </Link>
            <Link href="/admin/data-requests" className={link}>
              Data requests
            </Link>
          </>
        )}
        {user && (
          <>
            <span className="text-sm text-slate-600">
              {user.email} ({user.role})
            </span>
            <button type="button" onClick={leave} className={link}>
              Log out
            </button>
          </>
        )}
      </nav>
    </header>
  );
}
