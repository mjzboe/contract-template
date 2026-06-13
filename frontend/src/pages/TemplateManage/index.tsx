import { useState, useEffect } from "react";
import {
  Table,
  Button,
  Space,
  Modal,
  Upload,
  Input,
  message,
  Popconfirm,
  Typography,
} from "antd";
import { UploadOutlined, DeleteOutlined, SearchOutlined } from "@ant-design/icons";
import type { TemplateResponse, VariableInfoResponse } from "../../types";
import * as templateApi from "../../api/templates";

const { Text } = Typography;

const STATUS_STYLES: Record<string, { color: string; bg: string; label: string }> = {
  draft: { color: "#6B6B6B", bg: "#F5F3F0", label: "草稿" },
  active: { color: "#5B8C5A", bg: "#EFF5EF", label: "启用" },
  archived: { color: "#999", bg: "#F5F5F5", label: "归档" },
};

export default function TemplateManagePage() {
  const [templates, setTemplates] = useState<TemplateResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [keyword, setKeyword] = useState("");

  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploading, setUploading] = useState(false);

  const [varsOpen, setVarsOpen] = useState(false);
  const [currentVars, setCurrentVars] = useState<VariableInfoResponse[]>([]);
  const [currentName, setCurrentName] = useState("");

  const fetchTemplates = async () => {
    setLoading(true);
    try {
      const res = await templateApi.listTemplates({ page, page_size: 10, keyword: keyword || undefined });
      setTemplates(res.items);
      setTotal(res.total);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchTemplates(); }, [page]);

  const handleUpload = async (file: File) => {
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("name", file.name.replace(/\.docx?$/, ""));
      fd.append("tags", "[]");
      const res = await templateApi.uploadTemplate(fd);
      message.success(`上传成功，解析出 ${res.variables.length} 个变量`);
      setUploadOpen(false);
      fetchTemplates();
    } catch {
      message.error("上传失败");
    } finally {
      setUploading(false);
    }
    return false;
  };

  const handleDelete = async (id: string) => {
    try {
      await templateApi.deleteTemplate(id);
      message.success("删除成功");
      fetchTemplates();
    } catch {
      message.error("删除失败");
    }
  };

  const showVariables = (vars: VariableInfoResponse[], name: string) => {
    setCurrentVars(vars);
    setCurrentName(name);
    setVarsOpen(true);
  };

  const columns = [
    {
      title: "模板名称",
      dataIndex: "name",
      key: "name",
      render: (name: string) => <Text style={{ fontWeight: 500, color: "#1A1A1A" }}>{name}</Text>,
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      render: (s: string) => {
        const style = STATUS_STYLES[s] || STATUS_STYLES.draft;
        return (
          <span
            style={{
              display: "inline-block",
              padding: "2px 12px",
              borderRadius: 6,
              fontSize: 12,
              color: style.color,
              background: style.bg,
              fontWeight: 500,
            }}
          >
            {style.label}
          </span>
        );
      },
    },
    {
      title: "变量数",
      key: "vars",
      render: (_: unknown, r: TemplateResponse) => {
        const master = r.versions?.find((v) => v.is_master);
        return (
          <Button
            type="link"
            style={{ color: "#B8860B", fontWeight: 500, padding: 0 }}
            onClick={() => showVariables(master?.variables || [], r.name)}
          >
            {master?.variables?.length || 0} 个
          </Button>
        );
      },
    },
    {
      title: "版本",
      key: "version",
      render: (_: unknown, r: TemplateResponse) => r.versions?.length || 0,
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      key: "created_at",
      render: (t: string) => (
        <Text style={{ color: "#6B6B6B", fontSize: 13 }}>{new Date(t).toLocaleString("zh-CN")}</Text>
      ),
    },
    {
      title: "操作",
      key: "action",
      render: (_: unknown, r: TemplateResponse) => (
        <Popconfirm title="确认删除？" onConfirm={() => handleDelete(r.id)}>
          <Button type="link" danger icon={<DeleteOutlined />} style={{ fontWeight: 500 }}>
            删除
          </Button>
        </Popconfirm>
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
          }}
        >
          <Space>
            <Input
              placeholder="搜索模板"
              prefix={<SearchOutlined style={{ color: "#BFBFBF" }} />}
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              onPressEnter={() => { setPage(1); fetchTemplates(); }}
              style={{ width: 220, borderRadius: 8 }}
            />
            <Button onClick={() => { setPage(1); fetchTemplates(); }}>查询</Button>
          </Space>
          <Button
            type="primary"
            icon={<UploadOutlined />}
            onClick={() => setUploadOpen(true)}
            style={{ fontWeight: 500 }}
          >
            上传模板
          </Button>
        </div>

        <Table
          rowKey="id"
          columns={columns}
          dataSource={templates}
          loading={loading}
          pagination={{
            current: page,
            total,
            pageSize: 10,
            onChange: setPage,
          }}
          style={{ borderRadius: 0 }}
        />
      </div>

      <Modal
        title={
          <span style={{ fontFamily: "'Cormorant Garamond', Georgia, serif", fontSize: 17 }}>
            上传模板
          </span>
        }
        open={uploadOpen}
        onCancel={() => setUploadOpen(false)}
        footer={null}
      >
        <Upload.Dragger
          accept=".docx,.doc"
          showUploadList={false}
          beforeUpload={(file) => { handleUpload(file); return false; }}
        >
          <p style={{ fontSize: 36, color: "#B8860B" }}><UploadOutlined /></p>
          <p style={{ color: "#1A1A1A", fontWeight: 500 }}>点击或拖拽上传 Word 模板文件</p>
          <p style={{ color: "#999", fontSize: 13 }}>支持 .docx 格式</p>
        </Upload.Dragger>
        {uploading && <p style={{ textAlign: "center", marginTop: 8, color: "#6B6B6B" }}>上传中...</p>}
      </Modal>

      <Modal
        title={
          <span style={{ fontFamily: "'Cormorant Garamond', Georgia, serif", fontSize: 17 }}>
            变量列表 — {currentName}
          </span>
        }
        open={varsOpen}
        onCancel={() => setVarsOpen(false)}
        footer={null}
        width={600}
      >
        <Table
          rowKey="name"
          size="small"
          pagination={false}
          dataSource={currentVars}
          columns={[
            { title: "变量名", dataIndex: "name" },
            { title: "显示名", dataIndex: "display_name" },
            { title: "类型", dataIndex: "var_type" },
            { title: "出现次数", dataIndex: "occurrences" },
            { title: "默认值", dataIndex: "default_value" },
          ]}
        />
      </Modal>
    </div>
  );
}
