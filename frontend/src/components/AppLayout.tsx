import { Layout, Menu, Dropdown, Avatar, Space, Typography } from "antd";
import {
  HomeOutlined,
  FileTextOutlined,
  ProjectOutlined,
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
const { Text } = Typography;

const ALL_MENU_ITEMS = [
  { key: "/", icon: <HomeOutlined />, label: "首页", roles: ["super_admin", "template_admin", "approver", "user"] },
  { key: "/templates", icon: <FileTextOutlined />, label: "模板管理", roles: ["super_admin", "template_admin", "approver", "user"] },
  { key: "/contracts", icon: <FormOutlined />, label: "合同生成", roles: ["super_admin", "template_admin", "approver", "user"] },
  { key: "/projects", icon: <ProjectOutlined />, label: "项目管理", roles: ["super_admin", "template_admin", "approver", "user"] },
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
    { type: "divider" as const },
    { key: "logout", icon: <LogoutOutlined />, label: "退出登录" },
  ];

  return (
    <Layout style={{ minHeight: "100vh", background: "#F7F5F2" }}>
      <Sider
        width={220}
        collapsible
        breakpoint="lg"
        style={{
          background: "#FFFFFF",
          borderRight: "1px solid #E8E4DF",
          position: "sticky",
          top: 0,
          height: "100vh",
          overflow: "auto",
        }}
      >
        <div
          style={{
            padding: "28px 20px 20px",
            borderBottom: "1px solid #E8E4DF",
          }}
        >
          <div
            style={{
              fontFamily: "'Cormorant Garamond', Georgia, serif",
              fontSize: 22,
              fontWeight: 600,
              color: "#1A1A1A",
              letterSpacing: "0.02em",
              lineHeight: 1.2,
            }}
          >
            SIGNAPAGE
          </div>
          <div
            style={{
              fontSize: 11,
              color: "#999",
              marginTop: 4,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}
          >
            签字页管理系统
          </div>
          <div
            style={{
              width: 32,
              height: 2,
              background: "#B8860B",
              marginTop: 12,
              borderRadius: 1,
            }}
          />
        </div>
        <Menu
          theme="light"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={visibleMenuItems}
          onClick={({ key }) => navigate(key)}
          style={{
            borderRight: "none",
            padding: "8px 0",
            marginTop: 4,
          }}
        />
      </Sider>
      <Layout style={{ background: "#F7F5F2" }}>
        <Header
          style={{
            background: "#FFFFFF",
            padding: "0 32px",
            display: "flex",
            justifyContent: "flex-end",
            alignItems: "center",
            height: 56,
            lineHeight: "56px",
            borderBottom: "1px solid #E8E4DF",
            position: "sticky",
            top: 0,
            zIndex: 10,
          }}
        >
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
              <Space
                style={{
                  cursor: "pointer",
                  padding: "4px 12px",
                  borderRadius: 8,
                  transition: "all 0.2s",
                }}
              >
                <Avatar
                  size={30}
                  icon={<UserOutlined />}
                  style={{
                    backgroundColor: "#B8860B",
                    fontSize: 13,
                  }}
                />
                <Text
                  style={{
                    fontSize: 13.5,
                    color: "#1A1A1A",
                    fontWeight: 500,
                  }}
                >
                  {user.username}
                </Text>
              </Space>
            </Dropdown>
          )}
        </Header>
        <Content
          style={{
            margin: 0,
            padding: "28px 32px",
            minHeight: "calc(100vh - 56px)",
          }}
        >
          {children}
        </Content>
      </Layout>
    </Layout>
  );
}
