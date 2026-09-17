import type { ApiErrorBody } from "./types";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const TOKEN_KEY = "kanban.token";

/**
 * The token lives in localStorage. That is readable by any script running on
 * this origin, so an XSS bug would expose it; an httpOnly cookie would not, at
 * the cost of needing CSRF protection. Chosen knowingly for a single-page app
 * with no cookie-based flows.
 */
export const tokenStore = {
  read: () => localStorage.getItem(TOKEN_KEY),
  write: (token: string) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly field?: string;

  constructor(status: number, code: string, message: string, field?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.field = field;
  }
}

type Method = "GET" | "POST" | "PATCH" | "DELETE";

async function request<T>(method: Method, path: string, body?: unknown): Promise<T> {
  const token = tokenStore.read();

  const response = await fetch(`${BASE_URL}/api${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (response.status === 204) return undefined as T;

  // A failure from outside the app — a proxy, or the server being down — will
  // not be JSON, so parsing has to tolerate that and still produce an ApiError.
  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    const envelope = payload as ApiErrorBody | null;
    throw new ApiError(
      response.status,
      envelope?.error.code ?? "INTERNAL_ERROR",
      envelope?.error.message ?? "Something went wrong.",
      envelope?.error.details?.field,
    );
  }

  return payload as T;
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body),
  patch: <T>(path: string, body: unknown) => request<T>("PATCH", path, body),
  remove: (path: string) => request<void>("DELETE", path),
};
