/**
 * SkillSpark AI — App Root
 * Sets up routing and shares pathway state
 * across Upload and Dashboard pages.
 */

import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { usePathway } from "./hooks/usePathway";
import Upload from "./pages/Upload";
import Dashboard from "./pages/Dashboard";

const App = () => {
  // Single shared state — passed to both pages
  const pathwayHook = usePathway();

  return (
    <BrowserRouter>
      <Routes>

        {/* Upload page — step 1 */}
        <Route
          path="/"
          element={<Upload pathwayHook={pathwayHook} />}
        />

        {/* Dashboard — results */}
        <Route
          path="/dashboard"
          element={<Dashboard pathwayHook={pathwayHook} />}
        />

        {/* Catch all — redirect to home */}
        <Route
          path="*"
          element={<Navigate to="/" replace />}
        />

      </Routes>
    </BrowserRouter>
  );
};

export default App;