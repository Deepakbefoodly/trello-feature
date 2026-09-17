/** Route guards: signed-in users never see the auth pages, and vice versa. */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AppRoutes } from "./App";
import { api } from "./api/client";
import type { User } from "./api/types";
import { AuthContext, type AuthValue } from "./auth/context";

const USER: User = { id: "u1", email: "owner@example.com", created_at: "" };

function renderAt(path: string, auth: Partial<AuthValue>) {
  const value: AuthValue = {
    user: null,
    isRestoring: false,
    signIn: vi.fn(),
    signUp: vi.fn(),
    signOut: vi.fn(),
    ...auth,
  };

  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <AuthContext.Provider value={value}>
        <MemoryRouter initialEntries={[path]}>
          <AppRoutes />
        </MemoryRouter>
      </AuthContext.Provider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.restoreAllMocks();
  // BoardsPage fetches on mount once a redirect lands there.
  vi.spyOn(api, "get").mockResolvedValue([]);
});

describe("route guards", () => {
  it("redirects an authenticated user away from /login", async () => {
    renderAt("/login", { user: USER });

    expect(await screen.findByRole("heading", { name: "Boards" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Sign in" })).not.toBeInTheDocument();
  });

  it("redirects an authenticated user away from /register", async () => {
    renderAt("/register", { user: USER });

    expect(await screen.findByRole("heading", { name: "Boards" })).toBeInTheDocument();
  });

  it("sends an anonymous visitor from a protected route to sign in", async () => {
    renderAt("/boards", { user: null });

    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });

  it("waits for the stored token to be checked before deciding", () => {
    renderAt("/boards", { user: null, isRestoring: true });

    // Neither destination yet — redirecting here would bounce a returning user
    // with a perfectly valid token out to the login page.
    expect(screen.queryByRole("heading", { name: "Sign in" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Boards" })).not.toBeInTheDocument();
  });
});
