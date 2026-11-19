import Link from "next/link";

import { CredentialsForm } from "@/components/CredentialsForm";

export const metadata = { title: "Log in · LendFlow" };

export default function LoginPage() {
  return (
    <main className="mx-auto w-full max-w-md flex-1 px-4 py-12">
      <h1 className="mb-6 text-3xl font-bold tracking-tight">Log in</h1>
      <div className="rounded-2xl bg-surface p-6 shadow-card ring-1 ring-slate-200/70">
        <CredentialsForm mode="login" />
      </div>
      <p className="mt-6 text-sm">
        New here?{" "}
        <Link href="/register" className="text-blue-800 underline">
          Create an account
        </Link>
      </p>
    </main>
  );
}
