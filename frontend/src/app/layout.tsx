import type { Metadata } from "next";
import { Suspense } from "react";
import { Geist } from "next/font/google";

import { SiteHeader } from "@/components/SiteHeader";
import { AuthProvider } from "@/lib/auth/AuthProvider";

import "./globals.css";

const geist = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "LendFlow",
  description:
    "A fictional digital lending app. Demo only; all data is synthetic.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geist.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col text-slate-900">
        <p
          className="bg-brand-ink px-4 py-1.5 text-center text-xs text-indigo-100"
          role="note"
        >
          Demo only. LendFlow is fictional; use synthetic data, never real
          personal information.
        </p>
        <AuthProvider>
          <Suspense fallback={<div className="h-[3.75rem] border-b border-slate-200 bg-white" />}>
            <SiteHeader />
          </Suspense>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
