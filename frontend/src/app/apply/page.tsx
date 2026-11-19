import { Suspense } from "react";

import { ApplyForm } from "@/components/ApplyForm";
import { RequireRole } from "@/components/RequireRole";

export const metadata = { title: "Apply for a loan · LendFlow" };

export default function ApplyPage() {
  return (
    <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-10">
      <h1 className="mb-6 text-2xl font-semibold">Apply for a loan</h1>
      <RequireRole roles={["borrower"]}>
        <Suspense fallback={<p>Loading…</p>}>
          <div className="rounded-2xl bg-surface p-6 shadow-card ring-1 ring-slate-200/70 max-w-2xl">
            <ApplyForm />
          </div>
        </Suspense>
      </RequireRole>
    </main>
  );
}
