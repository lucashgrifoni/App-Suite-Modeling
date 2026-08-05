import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import { SessionProvider } from "./context/SessionContext";
import { AnalysisHistoryProvider } from "./context/AnalysisHistoryContext";
import { AppLayout } from "./components/layout/AppLayout";
import { RouteFallback } from "./components/layout/RouteFallback";

const HomePage = lazy(() =>
  import("./pages/HomePage").then((m) => ({ default: m.HomePage })),
);
const TemplatesPage = lazy(() =>
  import("./pages/TemplatesPage").then((m) => ({ default: m.TemplatesPage })),
);
const ImportPage = lazy(() =>
  import("./pages/ImportPage").then((m) => ({ default: m.ImportPage })),
);
const WizardPage = lazy(() =>
  import("./pages/WizardPage").then((m) => ({ default: m.WizardPage })),
);
const ReviewPage = lazy(() =>
  import("./pages/ReviewPage").then((m) => ({ default: m.ReviewPage })),
);
const AnalysisPage = lazy(() =>
  import("./pages/AnalysisPage").then((m) => ({ default: m.AnalysisPage })),
);
const ExportPage = lazy(() =>
  import("./pages/ExportPage").then((m) => ({ default: m.ExportPage })),
);
const DiffPage = lazy(() =>
  import("./pages/DiffPage").then((m) => ({ default: m.DiffPage })),
);
const HistoryPage = lazy(() =>
  import("./pages/HistoryPage").then((m) => ({ default: m.HistoryPage })),
);

/** Every path the application answers. Exported so tests assert against one list. */
export const APP_ROUTES = [
  "/",
  "/templates",
  "/import",
  "/wizard",
  "/review",
  "/analysis",
  "/export",
  "/diff",
  "/history",
] as const;

/**
 * Everything inside the router.
 *
 * Split out from `App` so tests can mount it under a `MemoryRouter` and drive real
 * navigation. With `BrowserRouter` hardcoded around it there was no way to start at a
 * given URL, which is why the routing table had no test at all.
 */
export function AppRoutes() {
  return (
    <SessionProvider>
      <AnalysisHistoryProvider>
        <Suspense fallback={<RouteFallback />}>
          <Routes>
            <Route element={<AppLayout />}>
              <Route path="/" element={<HomePage />} />
              <Route path="/templates" element={<TemplatesPage />} />
              <Route path="/import" element={<ImportPage />} />
              <Route path="/wizard" element={<WizardPage />} />
              <Route path="/review" element={<ReviewPage />} />
              <Route path="/analysis" element={<AnalysisPage />} />
              <Route path="/export" element={<ExportPage />} />
              <Route path="/diff" element={<DiffPage />} />
              <Route path="/history" element={<HistoryPage />} />
              {/* An unknown URL must land on the home page, never on a blank screen. */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </Suspense>
      </AnalysisHistoryProvider>
    </SessionProvider>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}
