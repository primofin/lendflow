import { ApiStatus } from "@/components/ApiStatus";
import { HomeContent } from "@/components/HomeContent";

export default function Home() {
  return (
    <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-10">
      <HomeContent />
      <ApiStatus />
    </main>
  );
}
