import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import { useEffect } from "react";
import AppLayout from "./components/AppLayout";
import HomePage from "./pages/Home";
import TemplateManagePage from "./pages/TemplateManage";
import ContractGeneratePage from "./pages/ContractGenerate";
import ApprovalCenterPage from "./pages/ApprovalCenter";
import ArchiveSearchPage from "./pages/ArchiveSearch";
import AuditLogPage from "./pages/AuditLog";
import LoginPage from "./pages/Login";
import UserManagePage from "./pages/UserManage";
import { useAuthStore } from "./stores/authStore";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

function AppRoutes() {
  const initFromStorage = useAuthStore((s) => s.initFromStorage);

  useEffect(() => {
    initFromStorage();
  }, [initFromStorage]);

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <AppLayout>
              <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/templates" element={<TemplateManagePage />} />
                <Route path="/contracts" element={<ContractGeneratePage />} />
                <Route path="/approvals" element={<ApprovalCenterPage />} />
                <Route path="/archives" element={<ArchiveSearchPage />} />
                <Route path="/audit-logs" element={<AuditLogPage />} />
                <Route path="/users" element={<UserManagePage />} />
              </Routes>
            </AppLayout>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}

function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </ConfigProvider>
  );
}

export default App;
