import { DataRequestsAdmin } from "@/components/DataRequestsAdmin";
import { RequireRole } from "@/components/RequireRole";

export const metadata = { title: "Data requests · LendFlow" };

export default function DataRequestsPage() {
  return (
    <RequireRole roles={["supervisor"]}>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-10">
        <h1 className="mb-6 text-2xl font-semibold">Data deletion requests</h1>
        <DataRequestsAdmin />
      </main>
    </RequireRole>
  );
}
