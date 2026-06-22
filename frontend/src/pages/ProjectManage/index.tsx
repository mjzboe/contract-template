import { useState, useEffect, useCallback } from "react";
import {
  Table,
  Button,
  Space,
  Input,
  Tag,
  message,
  Popconfirm,
  Modal,
  Form,
  Typography,
  Select,
} from "antd";
import {
  SearchOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  FileExcelOutlined,
  FormOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import type { ColumnsType } from "antd/es/table";
import type { ProjectResponse, TemplateResponse } from "../../types";
import * as projectApi from "../../api/projects";
import * as templateApi from "../../api/templates";

const { Text } = Typography;

const STATUS_OPTIONS = [
  { value: "", label: "全部状态" },
  { value: "draft", label: "草稿" },
  { value: "active", label: "进行中" },
  { value: "completed", label: "已完成" },
  { value: "archived", label: "已归档" },
];

const STATUS_STYLES: Record<string, { color: string; bg: string; label: string }> = {
  draft: { color: "#6B6B6B", bg: "#F5F3F0", label: "草稿" },
  active: { color: "#B8860B", bg: "rgba(184,134,11,0.08)", label: "进行中" },
  completed: { color: "#5B8C5A", bg: "#EFF5EF", label: "已完成" },
  archived: { color: "#999", bg: "#F5F5F5", label: "已归档" },
};

export default function ProjectManagePage() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<ProjectResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(false);
  const [keyword, setKeyword] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("");

  // 编辑弹窗
  const [editOpen, setEditOpen] = useState(false);
  const [editForm] = Form.useForm();
  const [editingId, setEditingId] = useState<string>("");
  const [editingTemplates, setEditingTemplates] = useState<TemplateResponse[]>([]);
  const [allTemplates, setAllTemplates] = useState<TemplateResponse[]>([]);
  const [saving, setSaving] = useState(false);

  // 详情弹窗
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailProject, setDetailProject] = useState<ProjectResponse | null>(null);

  const fetchProjects = useCallback(async () => {
    setLoading(true);
    try {
      const res = await projectApi.listProjects({
        page,
        page_size: pageSize,
        keyword: keyword || undefined,
        status: statusFilter || undefined,
      });
      setProjects(res.items);
      setTotal(res.total);
    } catch {
      message.error("获取项目列表失败");
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, keyword, statusFilter]);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  // 加载所有模板（用于编辑时选择）
  useEffect(() => {
    templateApi.listTemplates({ page: 1, page_size: 200 }).then((res) => {
      setAllTemplates(res.items);
    });
  }, []);

  const handleSearch = () => {
    setPage(1);
    fetchProjects();
  };

  const openDetail = (record: ProjectResponse) => {
    setDetailProject(record);
    setDetailOpen(true);
  };

  const openEdit = (record: ProjectResponse) => {
    setEditingId(record.id);
    setEditingTemplates(record.templates || []);
    editForm.setFieldsValue({
      name: record.name,
      description: record.description || "",
      status: record.status,
      template_ids: (record.templates || []).map((t) => t.id),
    });
    setEditOpen(true);
  };

  const handleEdit = async (values: {
    name: string;
    description?: string;
    status?: string;
    template_ids?: string[];
  }) => {
    setSaving(true);
    try {
      const data: Record<string, unknown> = {};
      if (values.name) data.name = values.name;
      if (values.description !== undefined) data.description = values.description;
      if (values.status) data.status = values.status;
      if (values.template_ids) data.template_ids = values.template_ids;

      await projectApi.updateProject(editingId, data);
      message.success("项目更新成功");
      setEditOpen(false);
      editForm.resetFields();
      fetchProjects();
    } catch {
      message.error("更新失败");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await projectApi.deleteProject(id);
      message.success("项目已删除");
      fetchProjects();
    } catch {
      message.error("删除失败");
    }
  };

  const columns: ColumnsType<ProjectResponse> = [
    {
      title: "项目名称",
      dataIndex: "name",
      render: (name: string, record: ProjectResponse) => (
        <Button
          type="link"
          style={{ fontWeight: 500, color: "#1A1A1A", padding: 0 }}
          onClick={() => openDetail(record)}
        >
          {name}
        </Button>
      ),
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 100,
      render: (s: string) => {
        const st = STATUS_STYLES[s] || STATUS_STYLES.draft;
        return (
          <span
            style={{
              padding: "2px 12px",
              borderRadius: 6,
              fontSize: 12,
              color: st.color,
              background: st.bg,
              fontWeight: 500,
            }}
          >
            {st.label}
          </span>
        );
      },
    },
    {
      title: "关联模板",
      width: 200,
      render: (_: unknown, r: ProjectResponse) => {
        if (!r.templates || r.templates.length === 0) {
          return <Text style={{ color: "#BFBFBF", fontSize: 13 }}>无</Text>;
        }
        return (
          <Space size={4} wrap>
            {r.templates.map((t) => (
              <Tag key={t.id} style={{ borderRadius: 6, borderColor: "#E8E4DF" }}>
                {t.name}
              </Tag>
            ))}
          </Space>
        );
      },
    },
    {
      title: "去重变量",
      width: 100,
      render: (_: unknown, r: ProjectResponse) => r.deduplicated_variables?.length || 0,
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      width: 170,
      render: (t: string) => (
        <Text style={{ color: "#6B6B6B", fontSize: 13 }}>{new Date(t).toLocaleString("zh-CN")}</Text>
      ),
    },
    {
      title: "操作",
      width: 260,
      render: (_: unknown, record: ProjectResponse) => (
        <Space size={4}>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => openDetail(record)}
          >
            详情
          </Button>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => openEdit(record)}
          >
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            icon={<FormOutlined />}
            style={{ color: "#B8860B" }}
            onClick={() => navigate(`/contracts?project_id=${record.id}`)}
          >
            生成
          </Button>
          <Popconfirm
            title="确认删除此项目？"
            description="项目下所有合同数据将一并删除"
            onConfirm={() => handleDelete(record.id)}
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ animation: "fadeIn 0.3s ease-out" }}>
      <div
        style={{
          background: "#FFFFFF",
          border: "1px solid #E8E4DF",
          borderRadius: 16,
          overflow: "hidden",
          boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
        }}
      >
        <div
          style={{
            padding: "20px 24px",
            borderBottom: "1px solid #E8E4DF",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: 12,
          }}
        >
          <Space wrap>
            <Input
              placeholder="搜索项目名称"
              prefix={<SearchOutlined style={{ color: "#BFBFBF" }} />}
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              onPressEnter={handleSearch}
              style={{ width: 220, borderRadius: 8 }}
            />
            <Select
              value={statusFilter}
              onChange={(v) => { setStatusFilter(v); setPage(1); }}
              options={STATUS_OPTIONS}
              style={{ width: 120 }}
            />
            <Button onClick={handleSearch}>查询</Button>
          </Space>
          <Button
            type="primary"
            icon={<FormOutlined />}
            onClick={() => navigate("/contracts")}
            style={{ fontWeight: 500 }}
          >
            新建项目
          </Button>
        </div>

        <Table
          rowKey="id"
          columns={columns}
          dataSource={projects}
          loading={loading}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            onChange: (p, ps) => {
              setPage(p);
              setPageSize(ps);
            },
          }}
          style={{ borderRadius: 0 }}
        />
      </div>

      {/* 详情弹窗 */}
      <Modal
        title={
          <span style={{ fontFamily: "'Cormorant Garamond', Georgia, serif", fontSize: 17, fontWeight: 500 }}>
            项目详情
          </span>
        }
        open={detailOpen}
        onCancel={() => setDetailOpen(false)}
        footer={null}
        width={640}
      >
        {detailProject && (
          <div style={{ lineHeight: 2.2 }}>
            <div>
              <Text type="secondary">项目名称：</Text>
              <Text strong>{detailProject.name}</Text>
            </div>
            <div>
              <Text type="secondary">状态：</Text>
              {(() => {
                const st = STATUS_STYLES[detailProject.status] || STATUS_STYLES.draft;
                return (
                  <span style={{ padding: "2px 12px", borderRadius: 6, fontSize: 12, color: st.color, background: st.bg, fontWeight: 500 }}>
                    {st.label}
                  </span>
                );
              })()}
            </div>
            <div>
              <Text type="secondary">描述：</Text>
              <Text>{detailProject.description || "无"}</Text>
            </div>
            <div>
              <Text type="secondary">关联模板：</Text>
              <Text>{detailProject.templates?.length || 0} 个</Text>
            </div>
            {detailProject.templates && detailProject.templates.length > 0 && (
              <div style={{ marginTop: 4, paddingLeft: 16 }}>
                {detailProject.templates.map((t) => (
                  <Tag key={t.id} style={{ borderRadius: 6, marginBottom: 4, borderColor: "#E8E4DF" }}>
                    {t.name}
                  </Tag>
                ))}
              </div>
            )}
            <div>
              <Text type="secondary">去重变量：</Text>
              <Text>{detailProject.deduplicated_variables?.length || 0} 个</Text>
            </div>
            {detailProject.deduplicated_variables && detailProject.deduplicated_variables.length > 0 && (
              <div style={{ marginTop: 4, paddingLeft: 16 }}>
                {detailProject.deduplicated_variables.map((v) => (
                  <Tag
                    key={v.name}
                    style={{ borderRadius: 6, marginBottom: 4, borderColor: "#E8E4DF", color: "#B8860B", background: "rgba(184,134,11,0.06)" }}
                  >
                    {v.display_name || v.name}
                  </Tag>
                ))}
              </div>
            )}
            <div>
              <Text type="secondary">创建时间：</Text>
              <Text>{new Date(detailProject.created_at).toLocaleString("zh-CN")}</Text>
            </div>
            <div>
              <Text type="secondary">更新时间：</Text>
              <Text>{new Date(detailProject.updated_at).toLocaleString("zh-CN")}</Text>
            </div>
            <div style={{ marginTop: 16, display: "flex", gap: 8 }}>
              <Button
                type="primary"
                icon={<FormOutlined />}
                onClick={() => {
                  setDetailOpen(false);
                  navigate(`/contracts?project_id=${detailProject.id}`);
                }}
              >
                进入生成流程
              </Button>
              <Button
                icon={<FileExcelOutlined />}
                onClick={() => {
                  projectApi.downloadExcelTemplate(detailProject.id).catch(() => {
                    message.error("下载导入模板失败");
                  });
                }}
              >
                下载导入模板
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* 编辑弹窗 */}
      <Modal
        title={
          <span style={{ fontFamily: "'Cormorant Garamond', Georgia, serif", fontSize: 17, fontWeight: 500 }}>
            编辑项目
          </span>
        }
        open={editOpen}
        onCancel={() => { setEditOpen(false); editForm.resetFields(); }}
        onOk={() => editForm.submit()}
        confirmLoading={saving}
        destroyOnClose
        width={560}
      >
        <Form form={editForm} layout="vertical" onFinish={handleEdit}>
          <Form.Item
            name="name"
            label="项目名称"
            rules={[{ required: true, message: "请输入项目名称" }]}
          >
            <Input placeholder="项目名称" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} placeholder="项目描述（可选）" />
          </Form.Item>
          <Form.Item name="status" label="状态">
            <Select options={STATUS_OPTIONS.filter((o) => o.value)} />
          </Form.Item>
          <Form.Item name="template_ids" label="关联模板" extra="修改关联模板后，变量去重将自动重新计算">
            <Select
              mode="multiple"
              placeholder="选择模板"
              optionFilterProp="label"
              options={(() => {
                const existingIds = new Set(allTemplates.map((t) => t.id));
                const extraOptions = (editingTemplates || [])
                  .filter((t) => !existingIds.has(t.id))
                  .map((t) => ({ value: t.id, label: t.name }));
                return [
                  ...allTemplates.map((t) => ({ value: t.id, label: t.name })),
                  ...extraOptions,
                ];
              })()}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
