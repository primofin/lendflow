import { ApiStatus } from "@/components/ApiStatus";
import { HomeContent } from "@/components/HomeContent";

export default function Home() {
  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-10">
      <h1 className="text-3xl font-semibold">LendFlow</h1>
      <HomeContent />
      <ApiStatus />
    </main>
  );
}
