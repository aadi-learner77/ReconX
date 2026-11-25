import React from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { Layout } from "./components/Layout";
import { AdminPage } from "./pages/AdminPage";
import { AgentHarnessPage } from "./pages/AgentHarnessPage";
import { AuditPage } from "./pages/AuditPage";
import { CashViewPage } from "./pages/CashViewPage";
import { DashboardPage } from "./pages/DashboardPage";
import { DocumentsPage } from "./pages/DocumentsPage";
import { ExceptionDetailPage } from "./pages/ExceptionDetailPage";
import { ExceptionsPage } from "./pages/ExceptionsPage";
import { LoginPage } from "./pages/LoginPage";
import { ObligationGraphPage } from "./pages/ObligationGraphPage";
import { TransactionDetailPage } from "./pages/TransactionDetailPage";
import { TransactionsPage } from "./pages/TransactionsPage";
import { VendorsPage } from "./pages/VendorsPage";

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, loading } = useAuth();
  if (loading) return <div className="p-8 text-sm text-slate-500">Authenticating...</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
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
          <Route path="audit" element={<AuditPage />} />
          <Route path="admin" element={<AdminPage />} />
        </Route>
      </Routes>
    </AuthProvider>
  );
};

export default App;
