import { Suspense } from "react";

import { RequireRole } from "@/components/RequireRole";
import { ReviewView } from "@/components/ReviewView";

export const metadata = { title: "Review application · LendFlow" };

async function File({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ReviewView id={id} />;
}

export default function ReviewPage({ params }: { params: Promise<{ id: string }> }) {
  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-10">
      <h1 className="mb-6 text-2xl font-semibold">Review application</h1>
      <RequireRole roles={["officer", "supervisor"]}>
        <Suspense fallback={<p>Loading…</p>}>
          <File params={params} />
        </Suspense>
      </RequireRole>
    </main>
  );
}
