"use client";

import Link from "next/link";

import { useAuth } from "@/lib/auth/AuthProvider";

import { MyApplications } from "./MyApplications";

const intro =
  "A fictional digital lending app. Borrowers apply online; loan officers and supervisors decide.";

export function HomeContent() {
  const { status, user } = useAuth();

  if (status === "loading") return <p>Loading…</p>;

  if (!user) {
    return (
      <>
        <p className="mt-3 text-slate-700">{intro}</p>
        <p className="mt-6 flex gap-4">
          <Link href="/calculator" className="text-blue-800 underline">
            Loan calculator
          </Link>
          <Link href="/register" className="text-blue-800 underline">
            Create an account
          </Link>
          <Link href="/login" className="text-blue-800 underline">
            Log in
          </Link>
        </p>
      </>
    );
  }

  if (user.role === "borrower") {
    return (
      <>
        <p className="mt-3 text-slate-700">You are logged in as borrower.</p>
        <MyApplications />
      </>
    );
  }

  return (
    <>
      <p className="mt-3 text-slate-700">You are logged in as {user.role}.</p>
      <p className="mt-4">
        <Link href="/queue" className="text-blue-800 underline">
          Open the review queue
        </Link>
      </p>
    </>
  );
}
