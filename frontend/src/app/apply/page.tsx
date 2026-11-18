import { Suspense } from "react";

import { ApplyForm } from "@/components/ApplyForm";
import { RequireRole } from "@/components/RequireRole";

export const metadata = { title: "Apply for a loan · LendFlow" };

export default function ApplyPage() {
  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-10">
      <h1 className="mb-6 text-2xl font-semibold">Apply for a loan</h1>
      <RequireRole roles={["borrower"]}>
        <Suspense fallback={<p>Loading…</p>}>
          <ApplyForm />
        </Suspense>
      </RequireRole>
    </main>
  );
}
