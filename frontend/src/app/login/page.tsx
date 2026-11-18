import Link from "next/link";

import { CredentialsForm } from "@/components/CredentialsForm";

export const metadata = { title: "Log in · LendFlow" };

export default function LoginPage() {
  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-10">
      <h1 className="mb-6 text-2xl font-semibold">Log in</h1>
      <CredentialsForm mode="login" />
      <p className="mt-6 text-sm">
        New here?{" "}
        <Link href="/register" className="text-blue-800 underline">
          Create an account
        </Link>
      </p>
    </main>
  );
}
