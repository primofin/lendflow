"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { ReactNode } from "react";

import {
  apiRequest,
  refreshAccessToken,
  setAccessToken,
  setSessionExpiredHandler,
} from "@/lib/api/client";
import type { User } from "@/lib/api/types";

type Status = "loading" | "anonymous" | "authenticated";

type AuthState = {
  status: Status;
  user: User | null;
  /** Set when the session ended on its own (idle timeout); cleared on the next login. */
  sessionEndedMessage: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

type TokenBody = { access_token: string };

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>("loading");
  const [user, setUser] = useState<User | null>(null);
  const [sessionEndedMessage, setSessionEndedMessage] = useState<string | null>(
    null,
  );

  useEffect(() => {
    setSessionExpiredHandler(() => {
      setUser(null);
      setStatus("anonymous");
      setSessionEndedMessage(
        "You were signed out after being idle. Log in again to continue.",
      );
    });
    return () => setSessionExpiredHandler(null);
  }, []);

  const loadUser = useCallback(async () => {
    setUser(await apiRequest<User>("/api/auth/me"));
    setStatus("authenticated");
  }, []);

  // On first load, trade the refresh cookie (if any) for an access token.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const token = await refreshAccessToken();
      if (cancelled) return;
      if (token === null) return setStatus("anonymous");
      try {
        const me = await apiRequest<User>("/api/auth/me");
        if (cancelled) return;
        setUser(me);
        setStatus("authenticated");
      } catch {
        if (!cancelled) setStatus("anonymous");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const enter = useCallback(
    async (path: string, email: string, password: string) => {
      const body = await apiRequest<TokenBody>(path, {
        method: "POST",
        json: { email, password },
      });
      setAccessToken(body.access_token);
      setSessionEndedMessage(null);
      await loadUser();
    },
    [loadUser],
  );

  const login = useCallback(
    (e: string, p: string) => enter("/api/auth/login", e, p),
    [enter],
  );
  const register = useCallback(
    (e: string, p: string) => enter("/api/auth/register", e, p),
    [enter],
  );

  const logout = useCallback(async () => {
    try {
      await apiRequest<void>("/api/auth/logout", { method: "POST" });
    } finally {
      setAccessToken(null);
      setUser(null);
      setStatus("anonymous");
    }
  }, []);

  const value = useMemo(
    () => ({ status, user, sessionEndedMessage, login, register, logout }),
    [status, user, sessionEndedMessage, login, register, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (context === null)
    throw new Error("useAuth must be used inside <AuthProvider>");
  return context;
}
