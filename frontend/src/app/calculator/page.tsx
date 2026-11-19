import { CalculatorForm } from "@/components/CalculatorForm";

export const metadata = { title: "Loan calculator · LendFlow" };

export default function CalculatorPage() {
  return (
    <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-10">
      <h1 className="mb-6 text-2xl font-semibold">Loan calculator</h1>
      <CalculatorForm />
    </main>
  );
}
