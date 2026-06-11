import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import AppLayout from "./components/AppLayout";
import HomePage from "./pages/Home";
import TemplateManagePage from "./pages/TemplateManage";
import ContractGeneratePage from "./pages/ContractGenerate";
import ApprovalCenterPage from "./pages/ApprovalCenter";
import ArchiveSearchPage from "./pages/ArchiveSearch";

function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>
        <AppLayout>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/templates" element={<TemplateManagePage />} />
            <Route path="/contracts" element={<ContractGeneratePage />} />
            <Route path="/approvals" element={<ApprovalCenterPage />} />
            <Route path="/archives" element={<ArchiveSearchPage />} />
          </Routes>
        </AppLayout>
      </BrowserRouter>
    </ConfigProvider>
  );
}

export default App;
