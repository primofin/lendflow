import { QueueView } from "@/components/QueueView";
import { RequireRole } from "@/components/RequireRole";

export const metadata = { title: "Review queue · LendFlow" };

export default function QueuePage() {
  return (
    <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-10">
      <h1 className="mb-6 text-2xl font-semibold">Review queue</h1>
      <RequireRole roles={["officer", "supervisor"]}>
        <QueueView />
      </RequireRole>
    </main>
  );
}
