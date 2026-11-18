import { MyDataView } from "@/components/MyDataView";
import { RequireRole } from "@/components/RequireRole";

export const metadata = { title: "My data · LendFlow" };

export default function MyDataPage() {
  return (
    <RequireRole roles={["borrower"]}>
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-10">
        <h1 className="mb-6 text-2xl font-semibold">My data</h1>
        <MyDataView />
      </main>
    </RequireRole>
  );
}
