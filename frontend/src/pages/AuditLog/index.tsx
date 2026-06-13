import { useState, useEffect } from "react";
import {
  Card,
  Table,
  Select,
  DatePicker,
  Space,
  Tag,
  Button,
  Modal,
  Typography,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import { auditApi, type AuditLogItem } from "../../api/audit";

const { RangePicker } = DatePicker;
const { Text } = Typography;

const ACTION_COLORS: Record<string, string> = {
  login: "blue",
  logout: "default",
  create: "green",
  update: "orange",
  delete: "red",
  export: "purple",
  download: "cyan",
  approve: "green",
  reject: "red",
  transfer: "orange",
  upload: "blue",
  post: "blue",
  put: "orange",
  patch: "orange",
};

const ACTION_LABELS: Record<string, string> = {
  login: "登录",
  logout: "登出",
  create: "创建",
  update: "更新",
  delete: "删除",
  export: "导出",
  download: "下载",
  approve: "审批通过",
  reject: "审批驳回",
  transfer: "转交",
  upload: "上传",
  post: "POST",
  put: "PUT",
  patch: "PATCH",
};

export default function AuditLogPage() {
  const [data, setData] = useState<AuditLogItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(false);
  const [actionFilter, setActionFilter] = useState<string | undefined>();
  const [resourceTypeFilter, setResourceTypeFilter] = useState<string | undefined>();
  const [detailModal, setDetailModal] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await auditApi.list({
        page,
        page_size: pageSize,
        action: actionFilter,
        resource_type: resourceTypeFilter,
      });
      setData(res.data.items);
      setTotal(res.data.total);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [page, pageSize, actionFilter, resourceTypeFilter]);

  const columns: ColumnsType<AuditLogItem> = [
    {
      title: "时间",
      dataIndex: "created_at",
      width: 180,
      render: (v: string) => new Date(v).toLocaleString("zh-CN"),
    },
    {
      title: "操作人",
      dataIndex: "user_id",
      width: 120,
      render: (v: string | null) => v ? v.slice(0, 8) + "..." : "-",
    },
    {
      title: "操作",
      dataIndex: "action",
      width: 100,
      render: (v: string) => (
        <Tag color={ACTION_COLORS[v] || "default"}>
          {ACTION_LABELS[v] || v}
        </Tag>
      ),
    },
    {
      title: "资源类型",
      dataIndex: "resource_type",
      width: 100,
    },
    {
      title: "资源ID",
      dataIndex: "resource_id",
      width: 200,
      ellipsis: true,
    },
    {
      title: "IP",
      dataIndex: "ip_address",
      width: 130,
    },
    {
      title: "详情",
      width: 80,
      render: (_: unknown, record: AuditLogItem) =>
        record.detail ? (
          <Button type="link" size="small" onClick={() => setDetailModal(record.detail)}>
            查看
          </Button>
        ) : (
          "-"
        ),
    },
  ];

  return (
    <div style={{ animation: "fadeIn 0.3s ease-out" }}>
    <Card title={<span style={{ fontFamily: "'Cormorant Garamond', Georgia, serif", fontSize: 17, fontWeight: 500 }}>审计日志</span>}>
      <Space style={{ marginBottom: 16 }} wrap>
        <Select
          placeholder="操作类型"
          allowClear
          style={{ width: 120 }}
          value={actionFilter}
          onChange={setActionFilter}
          options={Object.entries(ACTION_LABELS).map(([value, label]) => ({ value, label }))}
        />
        <Select
          placeholder="资源类型"
          allowClear
          style={{ width: 120 }}
          value={resourceTypeFilter}
          onChange={setResourceTypeFilter}
          options={[
            { value: "template", label: "模板" },
            { value: "contract", label: "合同" },
            { value: "user", label: "用户" },
            { value: "approval", label: "审批" },
            { value: "file", label: "文件" },
            { value: "api", label: "API" },
          ]}
        />
        <RangePicker />
      </Space>
      <Table
        columns={columns}
        dataSource={data}
        rowKey="id"
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
      />
      <Modal
        title="审计详情"
        open={!!detailModal}
        onCancel={() => setDetailModal(null)}
        footer={null}
        width={600}
      >
        {detailModal && (
          <Text>
            <pre style={{ maxHeight: 400, overflow: "auto", fontSize: 12 }}>
              {(() => {
                try {
                  return JSON.stringify(JSON.parse(detailModal), null, 2);
                } catch {
                  return detailModal;
                }
              })()}
            </pre>
          </Text>
        )}
      </Modal>
    </Card>
    </div>
  );
}
