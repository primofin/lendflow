import type { Metadata } from "next";
import { Geist } from "next/font/google";

import { AuthProvider } from "@/lib/auth/AuthProvider";

import "./globals.css";

const geist = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "LendFlow",
  description: "A fictional digital lending app. Demo only; all data is synthetic.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geist.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col bg-white text-slate-900">
        <p className="bg-amber-100 px-4 py-2 text-center text-sm text-amber-900" role="note">
          Demo only. LendFlow is fictional; use synthetic data, never real personal information.
        </p>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
