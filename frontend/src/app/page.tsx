import { ApiStatus } from "@/components/ApiStatus";

export default function Home() {
  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-12">
      <h1 className="text-3xl font-semibold">LendFlow</h1>
      <p className="mt-3 text-slate-600">
        A fictional digital lending app. Borrowers apply online; loan officers and supervisors
        decide.
      </p>
      <ApiStatus />
    </main>
  );
}
