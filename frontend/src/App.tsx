import { MotionConfig } from "framer-motion";
import { Navigate, Route, Routes } from "react-router-dom";

import { WorkspacePage } from "@/pages/workspace-page";

export default function App() {
  return (
    <MotionConfig reducedMotion="user" transition={{ duration: 0.22, ease: "easeOut" }}>
      <Routes>
        <Route path="/" element={<WorkspacePage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </MotionConfig>
  );
}
