import { Layout, Menu, Dropdown, Avatar } from "antd";
import {
  HomeOutlined,
  FileTextOutlined,
  FormOutlined,
  AuditOutlined,
  FolderOpenOutlined,
  SafetyCertificateOutlined,
  UserOutlined,
  LogoutOutlined,
  TeamOutlined,
} from "@ant-design/icons";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";
import { useRole } from "../hooks/useRole";
import type { ReactNode } from "react";

const { Sider, Content, Header } = Layout;

const ALL_MENU_ITEMS = [
  { key: "/", icon: <HomeOutlined />, label: "首页", roles: ["super_admin", "template_admin", "approver", "user"] },
  { key: "/templates", icon: <FileTextOutlined />, label: "模板管理", roles: ["super_admin", "template_admin", "approver", "user"] },
  { key: "/contracts", icon: <FormOutlined />, label: "合同生成", roles: ["super_admin", "template_admin", "approver", "user"] },
  { key: "/approvals", icon: <AuditOutlined />, label: "审批中心", roles: ["super_admin", "approver"] },
  { key: "/archives", icon: <FolderOpenOutlined />, label: "档案检索", roles: ["super_admin", "template_admin", "approver", "user"] },
  { key: "/audit-logs", icon: <SafetyCertificateOutlined />, label: "审计日志", roles: ["super_admin"] },
  { key: "/users", icon: <TeamOutlined />, label: "用户管理", roles: ["super_admin"] },
];

export default function AppLayout({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const { roleLabel } = useRole();

  const visibleMenuItems = ALL_MENU_ITEMS.filter(
    (item) => user && item.roles.includes(user.role)
  );

  const dropdownItems = [
    { key: "role", label: `角色：${roleLabel}`, disabled: true },
    { key: "logout", icon: <LogoutOutlined />, label: "退出登录" },
  ];

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
          items={visibleMenuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            background: "#fff",
            padding: "0 24px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span style={{ fontSize: 18, fontWeight: "bold" }}>
            合同模板管理系统
          </span>
          {user && (
            <Dropdown
              menu={{
                items: dropdownItems,
                onClick: ({ key }) => {
                  if (key === "logout") {
                    logout();
                    navigate("/login");
                  }
                },
              }}
            >
              <span style={{ cursor: "pointer" }}>
                <Avatar icon={<UserOutlined />} style={{ marginRight: 8 }} />
                {user.username}
              </span>
            </Dropdown>
          )}
        </Header>
        <Content style={{ margin: 24, padding: 24, background: "#fff" }}>
          {children}
        </Content>
      </Layout>
    </Layout>
  );
}