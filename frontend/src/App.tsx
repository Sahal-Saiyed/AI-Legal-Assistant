import { MotionConfig } from "framer-motion";
import { Navigate, Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "@/auth/protected-route";
import { LoginPage } from "@/pages/login-page";
import { WorkspacePage } from "@/pages/workspace-page";

export default function App() {
  return (
    <MotionConfig reducedMotion="user" transition={{ duration: 0.22, ease: "easeOut" }}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/" element={<WorkspacePage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </MotionConfig>
  );
}
