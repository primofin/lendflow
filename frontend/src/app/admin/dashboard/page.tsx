import { DashboardView } from "@/components/DashboardView";
import { RequireRole } from "@/components/RequireRole";

export const metadata = { title: "Operations dashboard · LendFlow" };

export default function DashboardPage() {
  return (
    <RequireRole roles={["supervisor"]}>
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-10">
        <h1 className="mb-6 text-2xl font-semibold">Operations dashboard</h1>
        <DashboardView />
      </main>
    </RequireRole>
  );
}
