import Link from "next/link";

import { CredentialsForm } from "@/components/CredentialsForm";

export const metadata = { title: "Create an account · LendFlow" };

export default function RegisterPage() {
  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-10">
      <h1 className="mb-6 text-2xl font-semibold">Create an account</h1>
      <CredentialsForm mode="register" />
      <p className="mt-6 text-sm">
        Already registered?{" "}
        <Link href="/login" className="text-blue-800 underline">
          Log in
        </Link>
      </p>
    </main>
  );
}
