import React, { Suspense, lazy } from "react";
import { MotionConfig } from "framer-motion";
import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { ThemeProvider } from "./theme/ThemeContext";
import { Layout } from "./components/Layout";
import { PageSkeleton, Toaster } from "./components/ui";
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { DocumentsPage } from "./pages/DocumentsPage";
import { TransactionsPage } from "./pages/TransactionsPage";
import { ExceptionsPage } from "./pages/ExceptionsPage";
import { ExceptionDetailPage } from "./pages/ExceptionDetailPage";
import { VendorsPage } from "./pages/VendorsPage";
import { CashViewPage } from "./pages/CashViewPage";
import { PolicyStudioPage } from "./pages/PolicyStudioPage";
import { ExecutiveBriefPage } from "./pages/ExecutiveBriefPage";
import { AuditPage } from "./pages/AuditPage";
import { AdminPage } from "./pages/AdminPage";
import { StyleguidePage } from "./pages/StyleguidePage";
import { UiKitPage } from "./pages/UiKitPage";

// Lazy-load heavy React Flow pages for bundle performance
const TransactionDetailPage = lazy(() =>
  import("./pages/TransactionDetailPage").then((m) => ({ default: m.TransactionDetailPage }))
);
const AgentHarnessPage = lazy(() =>
  import("./pages/AgentHarnessPage").then((m) => ({ default: m.AgentHarnessPage }))
);
const ObligationGraphPage = lazy(() =>
  import("./pages/ObligationGraphPage").then((m) => ({ default: m.ObligationGraphPage }))
);

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="p-8 max-w-6xl mx-auto">
        <PageSkeleton />
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
};

export const App: React.FC = () => {
  return (
    <MotionConfig reducedMotion="user">
      <ThemeProvider>
        <AuthProvider>
        <Toaster />
        <Suspense
          fallback={
            <div className="p-8 max-w-6xl mx-auto">
              <PageSkeleton />
            </div>
          }
        >
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/styleguide" element={<StyleguidePage />} />
            <Route path="/dev/ui-kit" element={<UiKitPage />} />
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Layout />
                </ProtectedRoute>
              }
            >
              <Route index element={<DashboardPage />} />
              <Route path="documents" element={<DocumentsPage />} />
              <Route path="transactions" element={<TransactionsPage />} />
              <Route path="transactions/:id" element={<TransactionDetailPage />} />
              <Route path="exceptions" element={<ExceptionsPage />} />
              <Route path="exceptions/:id" element={<ExceptionDetailPage />} />
              <Route path="vendors" element={<VendorsPage />} />
              <Route path="vendors/:id" element={<VendorsPage />} />
              <Route path="cash" element={<CashViewPage />} />
              <Route path="agent-harness" element={<AgentHarnessPage />} />
              <Route path="obligation-graph" element={<ObligationGraphPage />} />
              <Route path="policy-studio" element={<PolicyStudioPage />} />
              <Route path="executive-brief" element={<ExecutiveBriefPage />} />
              <Route path="audit" element={<AuditPage />} />
              <Route path="admin" element={<AdminPage />} />
            </Route>
          </Routes>
        </Suspense>
      </AuthProvider>
    </ThemeProvider>
    </MotionConfig>
  );
};

export default App;
