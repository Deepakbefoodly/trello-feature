import { BrowserRouter, Navigate, Outlet, Route, Routes } from "react-router-dom";

import { useAuth } from "./auth/context";
import { ProgressBar } from "./components/ProgressBar";
import { AuthPage } from "./pages/AuthPage";
import { BoardPage } from "./pages/BoardPage";
import { BoardsPage } from "./pages/BoardsPage";

/**
 * Both guards wait for `isRestoring`, otherwise a page reload with a valid
 * token would bounce the user to /login before the token has been checked.
 */
function RequireAuth() {
  const { user, isRestoring } = useAuth();
  if (isRestoring) return <p className="state">Loading…</p>;
  return user ? <Outlet /> : <Navigate to="/login" replace />;
}

function GuestOnly() {
  const { user, isRestoring } = useAuth();
  if (isRestoring) return <p className="state">Loading…</p>;
  return user ? <Navigate to="/boards" replace /> : <Outlet />;
}

/** Exported without the router so tests can supply a MemoryRouter. */
export function AppRoutes() {
  return (
    <Routes>
      <Route element={<GuestOnly />}>
        <Route path="/login" element={<AuthPage mode="signIn" />} />
        <Route path="/register" element={<AuthPage mode="signUp" />} />
      </Route>

      <Route element={<RequireAuth />}>
        <Route path="/boards" element={<BoardsPage />} />
        <Route path="/boards/:boardId" element={<BoardPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/boards" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      {/* Outside AppRoutes so it survives navigation, and so route tests can
          render the routes without needing a query client for the bar. */}
      <ProgressBar />
      <AppRoutes />
    </BrowserRouter>
  );
}
