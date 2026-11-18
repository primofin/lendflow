import { Suspense } from "react";

import { ApplicationSummary } from "@/components/ApplicationSummary";
import { RequireRole } from "@/components/RequireRole";

export const metadata = { title: "Your application · LendFlow" };

async function Summary({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ApplicationSummary id={id} />;
}

export default function ApplicationPage({ params }: { params: Promise<{ id: string }> }) {
  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-10">
      <h1 className="mb-6 text-2xl font-semibold">Your application</h1>
      <RequireRole roles={["borrower"]}>
        <Suspense fallback={<p>Loading…</p>}>
          <Summary params={params} />
        </Suspense>
      </RequireRole>
    </main>
  );
}
