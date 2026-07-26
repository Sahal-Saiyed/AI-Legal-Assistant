import { MotionConfig } from "framer-motion";
import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "@/auth/protected-route";

const LoginPage = lazy(() =>
  import("@/pages/login-page").then((module) => ({ default: module.LoginPage })),
);
const WorkspacePage = lazy(() =>
  import("@/pages/workspace-page").then((module) => ({ default: module.WorkspacePage })),
);

function RouteFallback() {
  return (
    <div className="grid min-h-dvh place-items-center bg-background" role="status">
      <div className="flex items-center gap-3 text-sm font-medium text-slate-500">
        <span className="size-4 animate-spin rounded-full border-2 border-teal-700 border-t-transparent" />
        Loading JuriGPT
      </div>
    </div>
  );
}

export default function App() {
  return (
    <MotionConfig reducedMotion="user" transition={{ duration: 0.22, ease: "easeOut" }}>
      <Suspense fallback={<RouteFallback />}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<ProtectedRoute />}>
            <Route path="/chat/:conversationId?" element={<WorkspacePage />} />
          </Route>
          <Route path="/" element={<Navigate to="/chat" replace />} />
          <Route path="*" element={<Navigate to="/chat" replace />} />
        </Routes>
      </Suspense>
    </MotionConfig>
  );
}
