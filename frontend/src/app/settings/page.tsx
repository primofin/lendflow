import { RequireRole } from "@/components/RequireRole";
import { ReminderSettingsForm } from "@/components/ReminderSettingsForm";

export const metadata = { title: "Settings · LendFlow" };

export default function SettingsPage() {
  return (
    <RequireRole roles={["borrower"]}>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-10">
        <h1 className="mb-6 text-2xl font-semibold">Settings</h1>
        <ReminderSettingsForm />
      </main>
    </RequireRole>
  );
}
