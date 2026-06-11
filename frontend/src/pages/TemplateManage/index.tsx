import { useState, useEffect } from "react";
import {
  Table,
  Button,
  Space,
  Modal,
  Upload,
  Input,
  Tag,
  message,
  Popconfirm,
} from "antd";
import { UploadOutlined, DeleteOutlined, SearchOutlined } from "@ant-design/icons";
import type { TemplateResponse, VariableInfoResponse } from "../../types";
import * as templateApi from "../../api/templates";

export default function TemplateManagePage() {
  const [templates, setTemplates] = useState<TemplateResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [keyword, setKeyword] = useState("");

  // 上传弹窗
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploading, setUploading] = useState(false);

  // 变量详情弹窗
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
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      render: (s: string) => <Tag color={s === "draft" ? "default" : "green"}>{s}</Tag>,
    },
    {
      title: "变量数",
      key: "vars",
      render: (_: unknown, r: TemplateResponse) => {
        const master = r.versions?.find((v) => v.is_master);
        return (
          <Button type="link" onClick={() => showVariables(master?.variables || [], r.name)}>
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
      render: (t: string) => new Date(t).toLocaleString("zh-CN"),
    },
    {
      title: "操作",
      key: "action",
      render: (_: unknown, r: TemplateResponse) => (
        <Popconfirm title="确认删除？" onConfirm={() => handleDelete(r.id)}>
          <Button type="link" danger icon={<DeleteOutlined />}>删除</Button>
        </Popconfirm>
      ),
    },
  ];

  return (
    <>
      <Space style={{ marginBottom: 16, width: "100%", justifyContent: "space-between" }}>
        <Space>
          <Input
            placeholder="搜索模板"
            prefix={<SearchOutlined />}
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onPressEnter={() => { setPage(1); fetchTemplates(); }}
            style={{ width: 200 }}
          />
          <Button onClick={() => { setPage(1); fetchTemplates(); }}>查询</Button>
        </Space>
        <Button type="primary" icon={<UploadOutlined />} onClick={() => setUploadOpen(true)}>
          上传模板
        </Button>
      </Space>

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
      />

      {/* 上传弹窗 */}
      <Modal title="上传模板" open={uploadOpen} onCancel={() => setUploadOpen(false)} footer={null}>
        <Upload.Dragger
          accept=".docx,.doc"
          showUploadList={false}
          beforeUpload={(file) => { handleUpload(file); return false; }}
        >
          <p style={{ fontSize: 48, color: "#1890ff" }}><UploadOutlined /></p>
          <p>点击或拖拽上传 Word 模板文件</p>
          <p style={{ color: "#999" }}>支持 .docx 格式</p>
        </Upload.Dragger>
        {uploading && <p style={{ textAlign: "center", marginTop: 8 }}>上传中...</p>}
      </Modal>

      {/* 变量详情弹窗 */}
      <Modal title={`变量列表 — ${currentName}`} open={varsOpen} onCancel={() => setVarsOpen(false)} footer={null} width={600}>
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
    </>
  );
}