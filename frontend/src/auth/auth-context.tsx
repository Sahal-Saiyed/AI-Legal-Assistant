import { useEffect, useMemo, useState, type ReactNode } from "react";

import { AuthContext, type AuthContextValue } from "@/auth/auth-state";
import {
  AUTH_TOKEN_STORAGE_KEY,
  clearAuthToken,
  getCurrentUser,
  hasAuthToken,
  loginAccount,
  logoutAccount,
  registerAccount,
  renewAuthSession,
  type AuthUser,
} from "@/services/api";

const SESSION_RENEWAL_INTERVAL_MS = 5 * 60 * 1000;

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(hasAuthToken());

  useEffect(() => {
    if (!hasAuthToken()) return;
    void getCurrentUser()
      .then(setUser)
      .catch(() => clearAuthToken())
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const handleUnauthorized = () => {
      setUser(null);
      setLoading(false);
    };
    window.addEventListener("jurigpt:unauthorized", handleUnauthorized);
    return () => window.removeEventListener("jurigpt:unauthorized", handleUnauthorized);
  }, []);

  useEffect(() => {
    const handleStorage = (event: StorageEvent) => {
      if (event.key !== AUTH_TOKEN_STORAGE_KEY) return;
      if (!event.newValue) {
        setUser(null);
        setLoading(false);
        return;
      }
      setLoading(true);
      void getCurrentUser()
        .then(setUser)
        .catch(() => clearAuthToken())
        .finally(() => setLoading(false));
    };
    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  useEffect(() => {
    if (!user) return;
    let lastRenewedAt = Date.now();

    const renew = (keepalive = false, force = false) => {
      const now = Date.now();
      if (!force && now - lastRenewedAt < SESSION_RENEWAL_INTERVAL_MS) return;
      lastRenewedAt = now;
      void renewAuthSession(keepalive).catch(() => undefined);
    };
    const handleActivity = () => renew();
    const handleVisibilityChange = () => {
      renew(document.visibilityState === "hidden", true);
    };
    const handlePageHide = () => renew(true, true);
    const intervalId = window.setInterval(() => {
      if (document.visibilityState === "visible") renew(false, true);
    }, SESSION_RENEWAL_INTERVAL_MS);

    window.addEventListener("pointerdown", handleActivity, { passive: true });
    window.addEventListener("keydown", handleActivity);
    window.addEventListener("pagehide", handlePageHide);
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      window.clearInterval(intervalId);
      window.removeEventListener("pointerdown", handleActivity);
      window.removeEventListener("keydown", handleActivity);
      window.removeEventListener("pagehide", handlePageHide);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [user]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      login: async (email, password) => setUser((await loginAccount(email, password)).user),
      register: async (name, email, password) =>
        setUser((await registerAccount(name, email, password)).user),
      logout: () => {
        setUser(null);
        void logoutAccount();
      },
    }),
    [loading, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
