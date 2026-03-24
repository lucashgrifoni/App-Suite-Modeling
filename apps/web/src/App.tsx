import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { SessionProvider } from "./context/SessionContext";
import { AppLayout } from "./components/layout/AppLayout";
import { HomePage } from "./pages/HomePage";
import { TemplatesPage } from "./pages/TemplatesPage";
import { WizardPage } from "./pages/WizardPage";
import { ReviewPage } from "./pages/ReviewPage";
import { AnalysisPage } from "./pages/AnalysisPage";
import { ExportPage } from "./pages/ExportPage";

export default function App() {
  return (
    <BrowserRouter>
      <SessionProvider>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/templates" element={<TemplatesPage />} />
            <Route path="/wizard" element={<WizardPage />} />
            <Route path="/review" element={<ReviewPage />} />
            <Route path="/analysis" element={<AnalysisPage />} />
            <Route path="/export" element={<ExportPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </SessionProvider>
    </BrowserRouter>
  );
}
