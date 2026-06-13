import { useState, useEffect, useCallback } from "react";
import {
  Table,
  Button,
  Space,
  Input,
  Tag,
  message,
  DatePicker,
  Select,
  Modal,
  Timeline,
  Descriptions,
  Typography,
} from "antd";
import {
  SearchOutlined,
  DownloadOutlined,
  EyeOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import type { ArchiveListItem, ArchiveDetail } from "../../types";
import * as archiveApi from "../../api/archives";
import * as templateApi from "../../api/templates";
import * as projectApi from "../../api/projects";

const { Text } = Typography;
const { RangePicker } = DatePicker;

const STATUS_LABELS: Record<string, { color: string; bg: string; label: string }> = {
  archived: { color: "#5B8C5A", bg: "#EFF5EF", label: "已归档" },
};

export default function ArchiveSearchPage() {
  const [archives, setArchives] = useState<ArchiveListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(false);

  const [keyword, setKeyword] = useState("");
  const [templateFilter, setTemplateFilter] = useState<string | undefined>();
  const [projectFilter, setProjectFilter] = useState<string | undefined>();
  const [dateRange, setDateRange] = useState<[string, string] | undefined>();

  const [templateOptions, setTemplateOptions] = useState<{ value: string; label: string }[]>([]);
  const [projectOptions, setProjectOptions] = useState<{ value: string; label: string }[]>([]);

  const [detailOpen, setDetailOpen] = useState(false);
  const [detail, setDetail] = useState<ArchiveDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    templateApi.listTemplates({ page: 1, page_size: 200 }).then((res) => {
      setTemplateOptions(res.items.map((t) => ({ value: t.id, label: t.name })));
    });
    projectApi.listProjects({ page: 1, page_size: 200 }).then((res) => {
      setProjectOptions(res.items.map((p) => ({ value: p.id, label: p.name })));
    });
  }, []);

  const fetchArchives = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = {
        page,
        page_size: pageSize,
        keyword: keyword || undefined,
        template_id: templateFilter,
        project_id: projectFilter,
      };
      if (dateRange) {
        params.date_from = dateRange[0];
        params.date_to = dateRange[1];
      }
      const res = await archiveApi.listArchives(params as Parameters<typeof archiveApi.listArchives>[0]);
      setArchives(res.items);
      setTotal(res.total);
    } catch {
      message.error("获取归档列表失败");
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, keyword, templateFilter, projectFilter, dateRange]);

  useEffect(() => {
    fetchArchives();
  }, [fetchArchives]);

  const handleSearch = () => {
    setPage(1);
    fetchArchives();
  };

  const handleReset = () => {
    setKeyword("");
    setTemplateFilter(undefined);
    setProjectFilter(undefined);
    setDateRange(undefined);
    setPage(1);
  };

  const openDetail = async (id: string) => {
    setDetailLoading(true);
    setDetailOpen(true);
    try {
      const d = await archiveApi.getArchiveDetail(id);
      setDetail(d);
    } catch {
      message.error("获取归档详情失败");
    } finally {
      setDetailLoading(false);
    }
  };

  const columns: ColumnsType<ArchiveListItem> = [
    {
      title: "合同标题",
      dataIndex: "title",
      render: (title: string, record: ArchiveListItem) => (
        <Button
          type="link"
          style={{ fontWeight: 500, color: "#1A1A1A", padding: 0 }}
          onClick={() => openDetail(record.id)}
        >
          {title}
        </Button>
      ),
    },
    {
      title: "模板",
      dataIndex: "template_name",
      width: 150,
      render: (name: string | null) => (
        <Text style={{ color: "#6B6B6B", fontSize: 13 }}>{name || "-"}</Text>
      ),
    },
    {
      title: "项目",
      dataIndex: "project_name",
      width: 150,
      render: (name: string | null) => (
        <Text style={{ color: "#6B6B6B", fontSize: 13 }}>{name || "-"}</Text>
      ),
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 90,
      render: (s: string) => {
        const st = STATUS_LABELS[s] || STATUS_LABELS.archived;
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
      title: "归档时间",
      dataIndex: "archived_at",
      width: 170,
      render: (t: string | null) => (
        <Text style={{ color: "#6B6B6B", fontSize: 13 }}>
          {t ? new Date(t).toLocaleString("zh-CN") : "-"}
        </Text>
      ),
    },
    {
      title: "操作",
      width: 160,
      render: (_: unknown, record: ArchiveListItem) => (
        <Space size={4}>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => openDetail(record.id)}
          >
            详情
          </Button>
          <Button
            type="link"
            size="small"
            icon={<DownloadOutlined />}
            onClick={() => {
              archiveApi.downloadArchive(record.id).catch(() => {
                message.error("下载失败");
              });
            }}
          >
            下载
          </Button>
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
        {/* 搜索栏 */}
        <div
          style={{
            padding: "20px 24px",
            borderBottom: "1px solid #E8E4DF",
            display: "flex",
            flexWrap: "wrap",
            gap: 12,
            alignItems: "center",
          }}
        >
          <Input
            placeholder="搜索合同标题"
            prefix={<SearchOutlined style={{ color: "#BFBFBF" }} />}
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onPressEnter={handleSearch}
            style={{ width: 220, borderRadius: 8 }}
          />
          <Select
            placeholder="选择模板"
            value={templateFilter}
            onChange={setTemplateFilter}
            options={templateOptions}
            allowClear
            style={{ width: 180 }}
          />
          <Select
            placeholder="选择项目"
            value={projectFilter}
            onChange={setProjectFilter}
            options={projectOptions}
            allowClear
            style={{ width: 180 }}
          />
          <RangePicker
            onChange={(_, dateStrings) => {
              if (dateStrings[0] && dateStrings[1]) {
                setDateRange([dateStrings[0], dateStrings[1]]);
              } else {
                setDateRange(undefined);
              }
            }}
            style={{ borderRadius: 8 }}
          />
          <Button onClick={handleSearch} icon={<SearchOutlined />}>
            查询
          </Button>
          <Button onClick={handleReset} icon={<ReloadOutlined />}>
            重置
          </Button>
        </div>

        {/* 表格 */}
        <Table
          rowKey="id"
          columns={columns}
          dataSource={archives}
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
            归档详情
          </span>
        }
        open={detailOpen}
        onCancel={() => setDetailOpen(false)}
        footer={null}
        width={700}
        loading={detailLoading}
      >
        {detail && (
          <div>
            <Descriptions column={2} bordered size="small" style={{ marginBottom: 24 }}>
              <Descriptions.Item label="合同标题" span={2}>
                <Text strong>{detail.title}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <span
                  style={{
                    padding: "2px 12px",
                    borderRadius: 6,
                    fontSize: 12,
                    color: "#5B8C5A",
                    background: "#EFF5EF",
                    fontWeight: 500,
                  }}
                >
                  已归档
                </span>
              </Descriptions.Item>
              <Descriptions.Item label="归档时间">
                {detail.archived_at ? new Date(detail.archived_at).toLocaleString("zh-CN") : "-"}
              </Descriptions.Item>
              <Descriptions.Item label="模板">
                {detail.template_name || "-"}
              </Descriptions.Item>
              <Descriptions.Item label="项目">
                {detail.project_name || "-"}
              </Descriptions.Item>
            </Descriptions>

            {/* 变量值 */}
            {detail.variables && Object.keys(detail.variables).length > 0 && (
              <div style={{ marginBottom: 24 }}>
                <Text strong style={{ fontSize: 14, display: "block", marginBottom: 8 }}>
                  变量值
                </Text>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {Object.entries(detail.variables).map(([key, value]) => (
                    <Tag
                      key={key}
                      style={{
                        borderRadius: 6,
                        borderColor: "#E8E4DF",
                        color: "#B8860B",
                        background: "rgba(184,134,11,0.06)",
                      }}
                    >
                      {key}：{value}
                    </Tag>
                  ))}
                </div>
              </div>
            )}

            {/* 操作时间线 */}
            {detail.status_history && detail.status_history.length > 0 && (
              <div style={{ marginBottom: 24 }}>
                <Text strong style={{ fontSize: 14, display: "block", marginBottom: 8 }}>
                  操作时间线
                </Text>
                <Timeline
                  items={detail.status_history.map((entry) => ({
                    color: entry.status === "archived" ? "green" : "blue",
                    children: (
                      <span>
                        <Text strong>{entry.status === "draft" ? "创建草稿" : entry.status === "archived" ? "已归档" : entry.status}</Text>
                        <br />
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {new Date(entry.at).toLocaleString("zh-CN")}
                        </Text>
                      </span>
                    ),
                  }))}
                />
              </div>
            )}

            {/* 文件操作 */}
            <div style={{ display: "flex", gap: 8 }}>
              <Button
                icon={<DownloadOutlined />}
                onClick={() => {
                  archiveApi.downloadArchive(detail.id, "word").catch(() => {
                    message.error("下载失败");
                  });
                }}
              >
                下载 Word
              </Button>
              <Button
                icon={<DownloadOutlined />}
                onClick={() => {
                  archiveApi.downloadArchive(detail.id, "pdf").catch(() => {
                    message.error("下载失败");
                  });
                }}
              >
                下载 PDF
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
