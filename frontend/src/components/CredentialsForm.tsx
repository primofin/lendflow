"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { ApiError } from "@/lib/api/errors";
import { useAuth } from "@/lib/auth/AuthProvider";

import { buttonClass, FormField, inputClass } from "./FormField";
import { FormError } from "./FormError";

type Props = { mode: "login" | "register" };

/** LF-001: the log in and register forms share one component; only the call and the hints differ. */
export function CredentialsForm({ mode }: Props) {
  const { status, login, register, sessionEndedMessage } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const isRegister = mode === "register";

  useEffect(() => {
    if (status === "authenticated") router.replace("/");
  }, [status, router]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSending(true);
    try {
      await (isRegister ? register : login)(email.trim(), password);
      // Next.js keeps a page it navigated away from alive (hidden), so do not leave the
      // password sitting in this form's state.
      setPassword("");
      router.replace("/");
    } catch (failure) {
      setError(
        failure instanceof ApiError
          ? failure.message
          : "Something went wrong. Try again.",
      );
    } finally {
      setSending(false);
    }
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
      {!isRegister && sessionEndedMessage && (
        <p
          role="status"
          className="rounded border border-amber-300 bg-amber-50 px-3 py-2"
        >
          {sessionEndedMessage}
        </p>
      )}
      <FormField id="email" label="Email">
        {(describedBy) => (
          <input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            aria-describedby={describedBy}
            className={inputClass}
          />
        )}
      </FormField>
      <FormField
        id="password"
        label="Password"
        hint={isRegister ? "At least 10 characters." : undefined}
      >
        {(describedBy) => (
          <input
            id="password"
            type="password"
            autoComplete={isRegister ? "new-password" : "current-password"}
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            aria-describedby={describedBy}
            className={inputClass}
          />
        )}
      </FormField>
      <FormError message={error} />
      <button type="submit" disabled={sending} className={buttonClass}>
        {sending ? "Please wait…" : isRegister ? "Create account" : "Log in"}
      </button>
    </form>
  );
}
