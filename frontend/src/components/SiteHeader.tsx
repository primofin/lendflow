"use client";

import { Landmark, LogOut } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { useAuth } from "@/lib/auth/AuthProvider";

function NavLink({ href, children }: { href: string; children: string }) {
  const pathname = usePathname();
  const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={`whitespace-nowrap rounded-full px-3.5 py-1.5 text-sm font-medium transition ${
        active ? "bg-blue-50 text-blue-800" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
      }`}
    >
      {children}
    </Link>
  );
}

export function SiteHeader() {
  const { status, user, logout } = useAuth();
  const router = useRouter();

  async function leave() {
    await logout();
    router.replace("/login");
  }

  return (
    <header className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-3 gap-y-1 px-4 py-2.5">
        <Link href="/" className="mr-auto flex items-center md:mr-2 gap-2 text-lg font-bold tracking-tight">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-blue-700 text-white">
            <Landmark size={18} aria-hidden="true" />
          </span>
          LendFlow
        </Link>
        <nav aria-label="Main" className="order-last -mx-1 flex w-full items-center gap-1 overflow-x-auto px-1 md:order-none md:mx-0 md:w-auto md:flex-1 md:px-0">
          <NavLink href="/calculator">Calculator</NavLink>
          {user?.role === "borrower" && <NavLink href="/apply">Apply</NavLink>}
          {user?.role === "borrower" && <NavLink href="/my-data">My data</NavLink>}
          {user?.role === "borrower" && <NavLink href="/settings">Settings</NavLink>}
          {(user?.role === "officer" || user?.role === "supervisor") && (
            <>
              <NavLink href="/queue">Queue</NavLink>
              <NavLink href="/import">Import</NavLink>
            </>
          )}
          {user?.role === "supervisor" && (
            <>
              <NavLink href="/admin/dashboard">Dashboard</NavLink>
              <NavLink href="/admin/users">Users</NavLink>
              <NavLink href="/admin/data-requests">Data requests</NavLink>
            </>
          )}
        </nav>
        {status === "anonymous" && (
          <div className="flex items-center gap-2">
            <Link href="/login" className="rounded-full px-3.5 py-1.5 text-sm font-semibold hover:bg-slate-100">
              Log in
            </Link>
            <Link
              href="/register"
              className="rounded-full bg-blue-700 px-4 py-1.5 text-sm font-semibold text-white hover:bg-blue-900"
            >
              Register
            </Link>
          </div>
        )}
        {user && (
          <div className="flex items-center gap-3">
            <span className="max-w-40 truncate text-sm text-slate-600 2xl:max-w-none" title={`${user.email} (${user.role})`}>
              {user.email} ({user.role})
            </span>
            <button
              type="button"
              onClick={leave}
              className="inline-flex items-center gap-1.5 rounded-full border border-slate-300 px-3 py-1.5 text-sm font-medium hover:bg-slate-100"
            >
              <LogOut size={14} aria-hidden="true" />
              Log out
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
