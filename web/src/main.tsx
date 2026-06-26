import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { LandingPage } from "./landing/LandingPage";
import { Dashboard } from "./pages/Dashboard";
import { GapsPage } from "./pages/Gaps";
import { IngestPage } from "./pages/Ingest";
import { QueryPage } from "./pages/Query";
import { QuarantinePage } from "./pages/Quarantine";
import { SettingsPage } from "./pages/Settings";
import "./app.css";

const basename = import.meta.env.BASE_URL.replace(/\/$/, "") || undefined;
const landingOnly = import.meta.env.VITE_LANDING_ONLY === "true";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {landingOnly ? (
      <LandingPage />
    ) : (
      <BrowserRouter basename={basename}>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/app" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="ingest" element={<IngestPage />} />
            <Route path="query" element={<QueryPage />} />
            <Route path="quarantine" element={<QuarantinePage />} />
            <Route path="gaps" element={<GapsPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    )}
  </StrictMode>,
);
