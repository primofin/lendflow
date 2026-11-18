"use client";

import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";

import { apiRequest } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import { ROLES } from "@/lib/api/types";
import type { AdminUser, Role } from "@/lib/api/types";

import { buttonClass, FormField, inputClass } from "./FormField";
import { FormError } from "./FormError";

function message(failure: unknown): string {
  return failure instanceof ApiError
    ? failure.message
    : "Something went wrong. Try again.";
}

/** LF-002 AC3: a supervisor creates users and assigns roles. The API refuses everyone else. */
export function UsersAdmin() {
  const [users, setUsers] = useState<AdminUser[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("officer");
  const [sending, setSending] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setUsers(await apiRequest<AdminUser[]>("/api/users"));
    } catch (failure) {
      setError(message(failure));
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    apiRequest<AdminUser[]>("/api/users")
      .then((loaded) => {
        if (!cancelled) setUsers(loaded);
      })
      .catch((failure: unknown) => {
        if (!cancelled) setError(message(failure));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    setSending(true);
    try {
      const created = await apiRequest<AdminUser>("/api/users", {
        method: "POST",
        json: { email: email.trim(), password, role },
      });
      setNotice(`Created ${created.email} as ${created.role}.`);
      setEmail("");
      setPassword("");
      await load();
    } catch (failure) {
      setError(message(failure));
    } finally {
      setSending(false);
    }
  }

  async function changeRole(user: AdminUser, next: Role) {
    setError(null);
    setNotice(null);
    try {
      await apiRequest<AdminUser>(`/api/users/${user.id}/role`, {
        method: "PATCH",
        json: { role: next },
      });
      setNotice(`${user.email} is now ${next}.`);
    } catch (failure) {
      setError(message(failure));
    }
    await load(); // always show what the server holds, including after a refusal
  }

  return (
    <div className="flex flex-col gap-8">
      <FormError message={error} />
      {notice && (
        <p
          role="status"
          className="rounded border border-green-300 bg-green-50 px-3 py-2"
        >
          {notice}
        </p>
      )}

      <section aria-labelledby="create-heading">
        <h2 id="create-heading" className="mb-3 text-xl font-semibold">
          Create a user
        </h2>
        <form onSubmit={create} className="flex max-w-sm flex-col gap-4">
          <FormField id="new-email" label="Email">
            {(d) => (
              <input
                id="new-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                aria-describedby={d}
                className={inputClass}
              />
            )}
          </FormField>
          <FormField
            id="new-password"
            label="Password"
            hint="At least 10 characters."
          >
            {(d) => (
              <input
                id="new-password"
                type="password"
                autoComplete="new-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                aria-describedby={d}
                className={inputClass}
              />
            )}
          </FormField>
          <FormField id="new-role" label="Role">
            {(d) => (
              <select
                id="new-role"
                value={role}
                onChange={(e) => setRole(e.target.value as Role)}
                aria-describedby={d}
                className={inputClass}
              >
                {ROLES.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            )}
          </FormField>
          <button type="submit" disabled={sending} className={buttonClass}>
            {sending ? "Please wait…" : "Create user"}
          </button>
        </form>
      </section>

      <section aria-labelledby="list-heading">
        <h2 id="list-heading" className="mb-3 text-xl font-semibold">
          Users
        </h2>
        {users === null ? (
          <p>Loading…</p>
        ) : (
          <table className="w-full border-collapse text-left">
            <thead>
              <tr className="border-b border-slate-300">
                <th scope="col" className="py-2 pr-4">
                  Email
                </th>
                <th scope="col" className="py-2">
                  Role
                </th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id} className="border-b border-slate-200">
                  <td className="py-2 pr-4">{user.email}</td>
                  <td className="py-2">
                    <select
                      aria-label={`Role for ${user.email}`}
                      value={user.role}
                      onChange={(e) =>
                        void changeRole(user, e.target.value as Role)
                      }
                      className={inputClass}
                    >
                      {ROLES.map((r) => (
                        <option key={r} value={r}>
                          {r}
                        </option>
                      ))}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
