import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { ApiError } from "../api/client";
import { useAuth } from "../auth/context";

interface Props {
  mode: "signIn" | "signUp";
}

const COPY = {
  signIn: {
    heading: "Sign in",
    submit: "Sign in",
    prompt: "Need an account?",
    linkTo: "/register",
    linkText: "Register",
  },
  signUp: {
    heading: "Create an account",
    submit: "Register",
    prompt: "Already have an account?",
    linkTo: "/login",
    linkText: "Sign in",
  },
} as const;

/**
 * Login and registration differ only in wording and which call they make, so
 * they share one component rather than two near-identical copies.
 */
export function AuthPage({ mode }: Props) {
  const { signIn, signUp } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const copy = COPY[mode];

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await (mode === "signIn" ? signIn : signUp)(email, password);
    } catch (caught) {
      setError(
        caught instanceof ApiError ? caught.message : "Could not reach the server.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="auth">
      <form className="auth__card" onSubmit={handleSubmit}>
        <h1>{copy.heading}</h1>

        <label htmlFor="email">Email</label>
        <input
          id="email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />

        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          autoComplete={mode === "signIn" ? "current-password" : "new-password"}
          required
          minLength={8}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
        {mode === "signUp" && <p className="hint">At least 8 characters.</p>}

        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}

        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Working…" : copy.submit}
        </button>

        <p className="auth__switch">
          {copy.prompt} <Link to={copy.linkTo}>{copy.linkText}</Link>
        </p>
      </form>
    </main>
  );
}
