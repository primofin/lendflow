import { ImportView } from "@/components/ImportView";
import { RequireRole } from "@/components/RequireRole";

export const metadata = { title: "Import applications · LendFlow" };

export default function ImportPage() {
  return (
    <RequireRole roles={["officer", "supervisor"]}>
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-10">
        <h1 className="mb-6 text-2xl font-semibold">Import applications from CSV</h1>
        <ImportView />
      </main>
    </RequireRole>
  );
}
