import Link from "next/link";

import { CredentialsForm } from "@/components/CredentialsForm";

export const metadata = { title: "Create an account · LendFlow" };

export default function RegisterPage() {
  return (
    <main className="mx-auto w-full max-w-md flex-1 px-4 py-12">
      <h1 className="mb-6 text-3xl font-bold tracking-tight">Create an account</h1>
      <div className="rounded-2xl bg-surface p-6 shadow-card ring-1 ring-slate-200/70">
        <CredentialsForm mode="register" />
      </div>
      <p className="mt-6 text-sm">
        Already registered?{" "}
        <Link href="/login" className="text-blue-800 underline">
          Log in
        </Link>
      </p>
    </main>
  );
}
