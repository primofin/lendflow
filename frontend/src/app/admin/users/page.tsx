"use client";

import { RequireRole } from "@/components/RequireRole";
import { UsersAdmin } from "@/components/UsersAdmin";

export default function UsersPage() {
  return (
    <RequireRole roles={["supervisor"]}>
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-10">
        <h1 className="mb-6 text-2xl font-semibold">Users</h1>
        <UsersAdmin />
      </main>
    </RequireRole>
  );
}
