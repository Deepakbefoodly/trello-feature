import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import { api, tokenStore } from "../api/client";
import type { AuthResponse, User } from "../api/types";
import { AuthContext, type AuthValue } from "./context";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isRestoring, setIsRestoring] = useState(Boolean(tokenStore.read()));
  const queryClient = useQueryClient();

  // A stored token may be expired or signed with a rotated secret, so it is
  // verified against /auth/me rather than trusted on sight.
  useEffect(() => {
    if (!tokenStore.read()) return;

    let cancelled = false;
    api
      .get<{ user: User }>("/auth/me")
      .then(({ user: restored }) => {
        if (!cancelled) setUser(restored);
      })
      .catch(() => {
        tokenStore.clear();
      })
      .finally(() => {
        if (!cancelled) setIsRestoring(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const authenticate = useCallback(async (path: string, email: string, password: string) => {
    const result = await api.post<AuthResponse>(path, { email, password });
    tokenStore.write(result.access_token);
    setUser(result.user);
  }, []);

  const signOut = useCallback(() => {
    tokenStore.clear();
    setUser(null);
    // Otherwise the next user to sign in on this browser would briefly see the
    // previous user's cached boards.
    queryClient.clear();
  }, [queryClient]);

  const value = useMemo<AuthValue>(
    () => ({
      user,
      isRestoring,
      signIn: (email, password) => authenticate("/auth/login", email, password),
      signUp: (email, password) => authenticate("/auth/register", email, password),
      signOut,
    }),
    [user, isRestoring, authenticate, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
