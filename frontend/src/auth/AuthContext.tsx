import React, { createContext, useContext, useEffect, useState } from "react";
import { api, getAccessToken, setTokens } from "../api/client";
import type { UserProfile } from "../api/types";

interface AuthContextValue {
  user: UserProfile | null;
  loading: boolean;
  hasPermission: (perm: string) => boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState<boolean>(Boolean(getAccessToken()));

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      setLoading(false);
      return;
    }
    api
      .me()
      .then((u) => setUser(u))
      .catch(() => {
        setTokens(null);
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = async (email: string, password: string) => {
    const tokens = await api.login(email, password);
    setTokens(tokens);
    const me = await api.me();
    setUser(me);
  };

  const logout = async () => {
    try {
      await api.logout(localStorage.getItem("reconx_refresh_token"));
    } catch {
      // ignore logout error on expired token
    } finally {
      setTokens(null);
      setUser(null);
    }
  };

  const hasPermission = (perm: string) => Boolean(user?.permissions.includes(perm));

  return (
    <AuthContext.Provider value={{ user, loading, hasPermission, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
