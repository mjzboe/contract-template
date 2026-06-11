import { useState, useEffect } from "react";
import { Card, Col, Row, Statistic, Button, Table, Space } from "antd";
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
    <>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card>
            <Statistic title="模板总数" value={stats.templates} prefix={<FileTextOutlined />} />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic title="项目总数" value={stats.projects} prefix={<ProjectOutlined />} />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic title="已生成签字页" value={stats.contracts} prefix={<FileWordOutlined />} />
          </Card>
        </Col>
      </Row>

      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/contracts")}>
          创建项目
        </Button>
        <Button icon={<FileTextOutlined />} onClick={() => navigate("/templates")}>
          管理模板
        </Button>
      </Space>

      {recentProjects.length > 0 && (
        <Card title="最近项目" style={{ marginTop: 16 }}>
          <Table
            rowKey="id"
            size="small"
            pagination={false}
            dataSource={recentProjects}
            columns={[
              { title: "项目名称", dataIndex: "name" },
              { title: "模板数", render: (_: unknown, r: ProjectResponse) => r.templates?.length || 0 },
              { title: "去重变量数", render: (_: unknown, r: ProjectResponse) => r.deduplicated_variables?.length || 0 },
              {
                title: "创建时间",
                dataIndex: "created_at",
                render: (t: string) => new Date(t).toLocaleString("zh-CN"),
              },
            ]}
          />
        </Card>
      )}
    </>
  );
}