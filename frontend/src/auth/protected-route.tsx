import { Navigate, Outlet } from "react-router-dom";

import { useAuth } from "@/auth/auth-state";

export function ProtectedRoute() {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="grid min-h-dvh place-items-center bg-[#eef4f2]" role="status">
        <span className="size-9 animate-spin rounded-full border-2 border-teal-200 border-t-teal-700" />
        <span className="sr-only">Loading JuriGPT</span>
      </div>
    );
  }
  return user ? <Outlet /> : <Navigate to="/login" replace />;
}
