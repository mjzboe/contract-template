import { Layout, Menu } from "antd";
import {
  HomeOutlined,
  FileTextOutlined,
  FormOutlined,
  AuditOutlined,
  FolderOpenOutlined,
} from "@ant-design/icons";
import { useNavigate, useLocation } from "react-router-dom";
import type { ReactNode } from "react";

const { Sider, Content, Header } = Layout;

const menuItems = [
  { key: "/", icon: <HomeOutlined />, label: "首页" },
  { key: "/templates", icon: <FileTextOutlined />, label: "模板管理" },
  { key: "/contracts", icon: <FormOutlined />, label: "合同生成" },
  { key: "/approvals", icon: <AuditOutlined />, label: "审批中心" },
  { key: "/archives", icon: <FolderOpenOutlined />, label: "档案检索" },
];

export default function AppLayout({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider collapsible>
        <div
          style={{
            height: 48,
            margin: 16,
            color: "#fff",
            fontSize: 16,
            fontWeight: "bold",
            textAlign: "center",
            lineHeight: "48px",
          }}
        >
          签字页管理
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            background: "#fff",
            padding: "0 24px",
            fontSize: 18,
            fontWeight: "bold",
          }}
        >
          合同模板管理系统
        </Header>
        <Content style={{ margin: 24, padding: 24, background: "#fff" }}>
          {children}
        </Content>
      </Layout>
    </Layout>
  );
}
