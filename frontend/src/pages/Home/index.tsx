import { useState, useEffect } from "react";
import { Row, Col, Button, Table, Space, Typography } from "antd";
import {
  FileTextOutlined,
  ProjectOutlined,
  FileWordOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import type { ProjectResponse } from "../../types";
import * as templateApi from "../../api/templates";
import * as projectApi from "../../api/projects";
import * as contractApi from "../../api/contracts";

const { Text } = Typography;

function StatCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
}) {
  return (
    <div
      style={{
        padding: "28px 24px",
        background: "#FFFFFF",
        border: "1px solid #E8E4DF",
        borderRadius: 16,
        boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
        transition: "all 0.2s cubic-bezier(0.4,0,0.2,1)",
        animation: "fadeIn 0.4s ease-out",
        cursor: "default",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.boxShadow =
          "0 4px 12px rgba(0,0,0,0.06)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.boxShadow =
          "0 1px 3px rgba(0,0,0,0.04)";
      }}
    >
      <Space
        size={16}
        align="center"
        style={{ marginBottom: 20 }}
      >
        <div
          style={{
            width: 40,
            height: 40,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            borderRadius: 10,
            background: "rgba(184,134,11,0.08)",
            color: "#B8860B",
            fontSize: 18,
          }}
        >
          {icon}
        </div>
        <Text
          style={{
            fontSize: 13,
            color: "#6B6B6B",
            letterSpacing: "0.04em",
            textTransform: "uppercase",
            fontWeight: 500,
          }}
        >
          {label}
        </Text>
      </Space>
      <div
        style={{
          fontFamily: "'Cormorant Garamond', Georgia, serif",
          fontSize: 38,
          fontWeight: 600,
          color: "#1A1A1A",
          lineHeight: 1,
          letterSpacing: "-0.02em",
        }}
      >
        {value}
      </div>
    </div>
  );
}

export default function HomePage() {
  const navigate = useNavigate();
  const [stats, setStats] = useState({ templates: 0, projects: 0, contracts: 0 });
  const [recentProjects, setRecentProjects] = useState<ProjectResponse[]>([]);

  useEffect(() => {
    Promise.all([
      templateApi.listTemplates({ page: 1, page_size: 1 }),
      projectApi.listProjects({ page: 1, page_size: 1 }),
      contractApi.listContracts({ page: 1, page_size: 1 }),
    ]).then(([t, p, c]) => {
      setStats({ templates: t.total, projects: p.total, contracts: c.total });
    });

    projectApi.listProjects({ page: 1, page_size: 5 }).then((res) => {
      setRecentProjects(res.items);
    });
  }, []);

  return (
    <div style={{ animation: "fadeIn 0.3s ease-out" }}>
      <Row gutter={[20, 20]} style={{ marginBottom: 28 }}>
        <Col span={8}>
          <StatCard icon={<FileTextOutlined />} label="模板总数" value={stats.templates} />
        </Col>
        <Col span={8}>
          <StatCard icon={<ProjectOutlined />} label="项目总数" value={stats.projects} />
        </Col>
        <Col span={8}>
          <StatCard icon={<FileWordOutlined />} label="已生成签字页" value={stats.contracts} />
        </Col>
      </Row>

      <Space style={{ marginBottom: 24 }}>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => navigate("/contracts")}
          style={{ fontWeight: 500 }}
        >
          创建项目
        </Button>
        <Button
          icon={<FileTextOutlined />}
          onClick={() => navigate("/templates")}
        >
          管理模板
        </Button>
      </Space>

      {recentProjects.length > 0 && (
        <div
          style={{
            background: "#FFFFFF",
            border: "1px solid #E8E4DF",
            borderRadius: 16,
            padding: 0,
            boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
          }}
        >
          <div
            style={{
              padding: "20px 24px 16px",
              borderBottom: "1px solid #E8E4DF",
            }}
          >
            <Text
              style={{
                fontFamily: "'Cormorant Garamond', Georgia, serif",
                fontSize: 17,
                fontWeight: 500,
                color: "#1A1A1A",
              }}
            >
              最近项目
            </Text>
          </div>
          <Table
            rowKey="id"
            size="middle"
            pagination={false}
            dataSource={recentProjects}
            columns={[
              {
                title: "项目名称",
                dataIndex: "name",
                render: (name: string) => (
                  <Text style={{ fontWeight: 500, color: "#1A1A1A" }}>{name}</Text>
                ),
              },
              {
                title: "模板数",
                render: (_: unknown, r: ProjectResponse) => r.templates?.length || 0,
              },
              {
                title: "去重变量数",
                render: (_: unknown, r: ProjectResponse) => r.deduplicated_variables?.length || 0,
              },
              {
                title: "创建时间",
                dataIndex: "created_at",
                render: (t: string) => (
                  <Text style={{ color: "#6B6B6B", fontSize: 13 }}>
                    {new Date(t).toLocaleString("zh-CN")}
                  </Text>
                ),
              },
            ]}
            style={{ borderRadius: 0 }}
          />
        </div>
      )}
    </div>
  );
}
