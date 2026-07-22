import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import {
  clearAuthToken,
  getCurrentUser,
  hasAuthToken,
  loginAccount,
  registerAccount,
  type AuthUser,
} from "@/services/api";

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

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
    const handleUnauthorized = () => setUser(null);
    window.addEventListener("jurigpt:unauthorized", handleUnauthorized);
    return () => window.removeEventListener("jurigpt:unauthorized", handleUnauthorized);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      login: async (email, password) => setUser((await loginAccount(email, password)).user),
      register: async (name, email, password) =>
        setUser((await registerAccount(name, email, password)).user),
      logout: () => {
        clearAuthToken();
        setUser(null);
      },
    }),
    [loading, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used within AuthProvider");
  return value;
}
