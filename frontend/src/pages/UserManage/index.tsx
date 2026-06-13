import { useState, useEffect, useCallback } from "react";
import {
  Card,
  Table,
  Tag,
  Select,
  Button,
  message,
  Space,
  Modal,
  Input,
  Form,
  Popconfirm,
} from "antd";
import {
  PlusOutlined,
  EditOutlined,
  SearchOutlined,
  StopOutlined,
  CheckCircleOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import {
  usersApi,
  type UserRoleResponse,
  type CreateUserRequest,
  type UpdateUserRequest,
} from "../../api/users";

const ROLE_LABELS: Record<string, string> = {
  super_admin: "超级管理员",
  template_admin: "模板管理员",
  approver: "审批人",
  user: "普通用户",
};

export default function UserManagePage() {
  const [users, setUsers] = useState<UserRoleResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [keyword, setKeyword] = useState("");

  // 新增用户弹窗
  const [createOpen, setCreateOpen] = useState(false);
  const [createForm] = Form.useForm();

  // 修改用户弹窗
  const [editOpen, setEditOpen] = useState(false);
  const [editForm] = Form.useForm();
  const [editUserId, setEditUserId] = useState<string>("");

  const fetchUsers = useCallback(async (kw?: string) => {
    setLoading(true);
    try {
      const res = await usersApi.list(kw || keyword);
      setUsers(res.data);
    } catch {
      message.error("获取用户列表失败");
    } finally {
      setLoading(false);
    }
  }, [keyword]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const handleSearch = () => {
    fetchUsers(keyword);
  };

  // 新增用户
  const handleCreate = async (values: CreateUserRequest) => {
    try {
      await usersApi.create(values);
      message.success("用户创建成功");
      setCreateOpen(false);
      createForm.resetFields();
      fetchUsers();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "创建失败";
      message.error(msg);
    }
  };

  // 修改用户
  const openEdit = (record: UserRoleResponse) => {
    setEditUserId(record.id);
    editForm.setFieldsValue({ email: record.email, password: "" });
    setEditOpen(true);
  };

  const handleEdit = async (values: UpdateUserRequest) => {
    const data: UpdateUserRequest = {};
    if (values.email) data.email = values.email;
    if (values.password) data.password = values.password;
    try {
      await usersApi.update(editUserId, data);
      message.success("修改成功");
      setEditOpen(false);
      editForm.resetFields();
      fetchUsers();
    } catch {
      message.error("修改失败");
    }
  };

  // 切换启用/禁用
  const handleToggleActive = async (record: UserRoleResponse) => {
    try {
      await usersApi.toggleActive(record.id);
      message.success(record.is_active ? "已禁用" : "已启用");
      fetchUsers();
    } catch {
      message.error("操作失败");
    }
  };

  // 修改角色
  const handleChangeRole = async (userId: string, username: string, newRole: string) => {
    Modal.confirm({
      title: "确认修改角色",
      content: `将用户「${username}」的角色修改为「${ROLE_LABELS[newRole]}」？`,
      onOk: async () => {
        try {
          await usersApi.changeRole(userId, newRole);
          message.success("角色修改成功");
          fetchUsers();
        } catch {
          message.error("角色修改失败");
        }
      },
    });
  };

  const columns: ColumnsType<UserRoleResponse> = [
    {
      title: "用户名",
      dataIndex: "username",
      width: 130,
    },
    {
      title: "邮箱",
      dataIndex: "email",
      width: 200,
    },
    {
      title: "角色",
      dataIndex: "role",
      width: 180,
      render: (role: string, record: UserRoleResponse) => (
        <Select
          value={role}
          style={{ width: 140 }}
          onChange={(value) => handleChangeRole(record.id, record.username, value)}
          options={Object.entries(ROLE_LABELS).map(([value, label]) => ({ value, label }))}
        />
      ),
    },
    {
      title: "状态",
      dataIndex: "is_active",
      width: 80,
      render: (active: boolean) => (
        <Tag color={active ? "green" : "red"}>
          {active ? "正常" : "禁用"}
        </Tag>
      ),
    },
    {
      title: "操作",
      width: 200,
      render: (_: unknown, record: UserRoleResponse) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => openEdit(record)}
          >
            修改
          </Button>
          <Popconfirm
            title={record.is_active ? "确定禁用该用户？" : "确定启用该用户？"}
            onConfirm={() => handleToggleActive(record)}
          >
            <Button
              type="link"
              size="small"
              danger={record.is_active}
              icon={record.is_active ? <StopOutlined /> : <CheckCircleOutlined />}
            >
              {record.is_active ? "禁用" : "启用"}
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Card title="用户管理">
      <Space style={{ marginBottom: 16 }} wrap>
        <Input.Search
          placeholder="搜索用户名或邮箱"
          allowClear
          style={{ width: 260 }}
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onSearch={handleSearch}
          enterButton={<SearchOutlined />}
        />
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
          新增用户
        </Button>
      </Space>

      <Table
        columns={columns}
        dataSource={users}
        rowKey="id"
        loading={loading}
      />

      {/* 新增用户弹窗 */}
      <Modal
        title="新增用户"
        open={createOpen}
        onCancel={() => { setCreateOpen(false); createForm.resetFields(); }}
        onOk={() => createForm.submit()}
        destroyOnClose
      >
        <Form form={createForm} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="username" label="用户名" rules={[{ required: true, message: "请输入用户名" }]}>
            <Input />
          </Form.Item>
          <Form.Item name="email" label="邮箱" rules={[{ required: true, message: "请输入邮箱" }, { type: "email", message: "邮箱格式不正确" }]}>
            <Input />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true, message: "请输入密码" }, { min: 6, message: "密码至少6位" }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item name="role" label="角色" initialValue="user">
            <Select options={Object.entries(ROLE_LABELS).map(([value, label]) => ({ value, label }))} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 修改用户弹窗 */}
      <Modal
        title="修改用户"
        open={editOpen}
        onCancel={() => { setEditOpen(false); editForm.resetFields(); }}
        onOk={() => editForm.submit()}
        destroyOnClose
      >
        <Form form={editForm} layout="vertical" onFinish={handleEdit}>
          <Form.Item name="email" label="邮箱" rules={[{ type: "email", message: "邮箱格式不正确" }]}>
            <Input placeholder="修改邮箱" />
          </Form.Item>
          <Form.Item name="password" label="新密码" rules={[{ min: 6, message: "密码至少6位" }]}>
            <Input.Password placeholder="留空则不修改密码" />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}
