"use client";

import { ClipboardCheck, FileText, ShieldCheck, UserCheck } from "lucide-react";
import Link from "next/link";

import { useAuth } from "@/lib/auth/AuthProvider";

import { buttonClass, secondaryButtonClass } from "./FormField";
import { HeroCalculator } from "./HeroCalculator";
import { MyApplications } from "./MyApplications";

const STEPS = [
  { icon: FileText, title: "Apply online", text: "Tell us how much you need and give your consent. It takes a few minutes." },
  { icon: ClipboardCheck, title: "Upload documents", text: "Only the documents your income type needs. Track every step." },
  { icon: UserCheck, title: "A person decides", text: "A loan officer reviews your file. You always get the reasons." },
];

const TRUST = [
  "Humans decide, never an algorithm alone",
  "Every action is recorded in an audit log",
  "Your data: view, export or delete it any time",
];

function Landing() {
  return (
    <div className="flex flex-col gap-16">
      <section className="grid items-center gap-10 md:grid-cols-2" aria-label="Introduction">
        <div>
          <p className="inline-block rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-800">
            Fictional lender · demo with synthetic data
          </p>
          <h1 className="mt-4 text-4xl font-bold leading-tight tracking-tight sm:text-5xl">
            A loan you can follow, <span className="text-blue-700">step by step.</span>
          </h1>
          <p className="mt-4 max-w-md text-lg text-slate-600">
            Apply online, see where your application stands and why a decision was made. No phone calls, no
            re-typing the same ID.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link href="/register" className={buttonClass}>
              Get started
            </Link>
            <Link href="/calculator" className={secondaryButtonClass}>
              Try the calculator
            </Link>
          </div>
        </div>
        <HeroCalculator />
      </section>

      <section aria-label="How it works">
        <h2 className="text-2xl font-bold tracking-tight">How it works</h2>
        <ol className="mt-5 grid gap-4 md:grid-cols-3">
          {STEPS.map(({ icon: Icon, title, text }, index) => (
            <li key={title} className="rounded-2xl bg-surface p-5 shadow-card ring-1 ring-slate-200/70">
              <span className="grid h-10 w-10 place-items-center rounded-xl bg-blue-50 text-blue-700">
                <Icon size={20} aria-hidden="true" />
              </span>
              <p className="mt-3 text-sm font-semibold text-slate-500">Step {index + 1}</p>
              <p className="text-lg font-semibold">{title}</p>
              <p className="mt-1 text-slate-600">{text}</p>
            </li>
          ))}
        </ol>
      </section>

      <section aria-label="Trust" className="rounded-3xl bg-brand-ink p-6 text-indigo-50 sm:p-8">
        <ul className="grid gap-4 md:grid-cols-3">
          {TRUST.map((text) => (
            <li key={text} className="flex items-start gap-3">
              <ShieldCheck size={22} className="mt-0.5 shrink-0 text-indigo-300" aria-hidden="true" />
              <span>{text}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

export function HomeContent() {
  const { status, user } = useAuth();

  if (status === "loading") return <p className="text-slate-500">Loading…</p>;
  if (!user) return <Landing />;

  if (user.role === "borrower") {
    return (
      <>
        <h1 className="text-3xl font-bold tracking-tight">Welcome back</h1>
        <p className="mt-1 text-slate-600">You are logged in as borrower.</p>
        <MyApplications />
      </>
    );
  }

  return (
    <>
      <h1 className="text-3xl font-bold tracking-tight">Welcome back</h1>
      <p className="mt-1 text-slate-600">You are logged in as {user.role}.</p>
      <p className="mt-5">
        <Link href="/queue" className={buttonClass + " inline-flex"}>
          Open the review queue
        </Link>
      </p>
    </>
  );
}
