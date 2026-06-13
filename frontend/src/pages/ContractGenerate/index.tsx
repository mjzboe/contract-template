import { useState, useEffect, useRef } from "react";
import {
  Steps,
  Button,
  Space,
  Table,
  Input,
  Form,
  Card,
  Tag,
  message,
  Upload,
  Alert,
  Divider,
  Progress,
} from "antd";
import {
  UploadOutlined,
  DownloadOutlined,
  DeleteOutlined,
  FileZipOutlined,
  FileExcelOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import type {
  TemplateResponse,
  ProjectResponse,
  DeduplicatedVariablesResponse,
  ContractResponse,
  ExcelParseResponse,
  AsyncTaskResponse,
} from "../../types";
import * as templateApi from "../../api/templates";
import * as projectApi from "../../api/projects";
import * as contractApi from "../../api/contracts";

export default function ContractGeneratePage() {
  const navigate = useNavigate();
  const [current, setCurrent] = useState(0);

  // Step 1: 选模板
  const [templates, setTemplates] = useState<TemplateResponse[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [projectName, setProjectName] = useState("");
  const [creating, setCreating] = useState(false);

  // Step 2: 填变量
  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [dedupInfo, setDedupInfo] = useState<DeduplicatedVariablesResponse | null>(null);
  const [varValues, setVarValues] = useState<Record<string, string>>({});

  // Step 2: Excel 多行预览
  const [excelData, setExcelData] = useState<ExcelParseResponse | null>(null);
  const [selectedRowKeys, setSelectedRowKeys] = useState<number[]>([]);
  const [parsingExcel, setParsingExcel] = useState(false);

  // Step 3: 生成下载
  const [contracts, setContracts] = useState<ContractResponse[]>([]);
  const [generating, setGenerating] = useState(false);

  // 异步任务状态
  const [taskId, setTaskId] = useState<string | null>(null);
  const [taskStatus, setTaskStatus] = useState<AsyncTaskResponse | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 加载模板列表
  useEffect(() => {
    templateApi.listTemplates({ page: 1, page_size: 100 }).then((res) => {
      setTemplates(res.items);
    });
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  // ========== Step 1: 创建项目 ==========
  const handleCreateProject = async () => {
    if (!projectName.trim()) { message.warning("请输入项目名称"); return; }
    if (selectedIds.length === 0) { message.warning("请选择至少一个模板"); return; }

    setCreating(true);
    try {
      const proj = await projectApi.createProject({
        name: projectName,
        template_ids: selectedIds,
      });
      setProject(proj);
      const dedup = await projectApi.getDeduplicatedVariables(proj.id);
      setDedupInfo(dedup);
      const init: Record<string, string> = {};
      dedup.variables.forEach((v) => { init[v.name] = v.default_value || ""; });
      setVarValues(init);
      setCurrent(1);
      message.success("项目创建成功，变量已去重");
    } catch {
      message.error("创建项目失败");
    } finally {
      setCreating(false);
    }
  };

  // ========== Step 2: Excel 解析 ==========
  const handleExcelUpload = async (file: File) => {
    setParsingExcel(true);
    try {
      const data = await contractApi.parseExcel(file);
      setExcelData(data);
      setSelectedRowKeys(data.rows.map((_, i) => i));
      message.success(`解析成功，共 ${data.total_rows} 行数据`);
    } catch {
      message.error("Excel 解析失败，请检查文件格式");
    } finally {
      setParsingExcel(false);
    }
    return false;
  };

  // ========== Step 2 → Step 3: 异步生成 ==========
  const handleGenerate = async () => {
    if (!project) return;

    const hasExcelSelection = excelData && selectedRowKeys.length > 0;
    const hasManualVars = Object.values(varValues).some((v) => v.trim());

    if (!hasExcelSelection && !hasManualVars) {
      message.warning("请填写变量或上传 Excel");
      return;
    }

    setGenerating(true);
    try {
      if (excelData && selectedRowKeys.length > 0) {
        // Excel 模式：异步批量生成
        const task = await contractApi.batchGenerateFromRowsAsync({
          project_id: project.id,
          rows: excelData.rows,
          selected_indices: selectedRowKeys,
        });
        setTaskId(task.task_id);
        setTaskStatus(task);
        setCurrent(2);
        // 开始轮询
        startPolling(task.task_id);
      } else {
        // 手动模式：同步生成（数量少）
        const results: ContractResponse[] = [];
        for (const tmpl of project.templates) {
          const contract = await contractApi.generateContract({
            title: `${project.name} - ${tmpl.name}`,
            template_id: tmpl.id,
            variables: varValues,
            project_id: project.id,
          });
          results.push(contract);
        }
        setContracts(results);
        setTaskId(null);
        setCurrent(2);
        message.success(`成功生成 ${results.length} 份签字页`);
      }
    } catch {
      message.error("生成失败");
    } finally {
      setGenerating(false);
    }
  };

  // 轮询任务状态
  const startPolling = (tid: string) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const status = await contractApi.getTaskStatus(tid);
        setTaskStatus(status);
        if (status.status === "completed") {
          if (pollRef.current) clearInterval(pollRef.current);
          message.success(`生成完成，共 ${status.result?.count || 0} 份签字页`);
        } else if (status.status === "failed") {
          if (pollRef.current) clearInterval(pollRef.current);
          message.error(`生成失败：${status.error || "未知错误"}`);
        }
      } catch {
        // 轮询失败不中断
      }
    }, 2000);
  };

  // ========== 渲染 ==========
  const steps = [
    { title: "创建项目", description: "选择模板" },
    { title: "填写变量", description: "去重后变量" },
    { title: "生成下载", description: "导出文件" },
  ];

  const isTaskDone = taskStatus?.status === "completed";
  const isTaskFailed = taskStatus?.status === "failed";
  const isTaskRunning = taskStatus?.status === "running" || taskStatus?.status === "pending";

  return (
    <div style={{ animation: "fadeIn 0.3s ease-out" }}>
      <Steps current={current} items={steps} style={{ marginBottom: 28 }} />

      {/* Step 1 */}
      {current === 0 && (
        <Card title={<span style={{ fontFamily: "'Cormorant Garamond', Georgia, serif", fontSize: 17, fontWeight: 500 }}>创建项目</span>}>
          <Space direction="vertical" style={{ width: "100%" }} size="large">
            <Input
              placeholder="输入项目名称，如：XX公司IPO签字页"
              size="large"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              style={{ maxWidth: 400 }}
            />
            <Table
              rowKey="id"
              size="small"
              dataSource={templates}
              rowSelection={{
                selectedRowKeys: selectedIds,
                onChange: (keys) => setSelectedIds(keys as string[]),
              }}
              pagination={false}
              columns={[
                { title: "模板名称", dataIndex: "name" },
                {
                  title: "变量数",
                  render: (_: unknown, r: TemplateResponse) =>
                    r.versions?.find((v) => v.is_master)?.variables?.length || 0,
                },
                { title: "状态", dataIndex: "status", render: (s: string) => {
                  const statusStyles: Record<string, { color: string; bg: string; label: string }> = {
                    draft: { color: "#6B6B6B", bg: "#F5F3F0", label: "草稿" },
                    active: { color: "#5B8C5A", bg: "#EFF5EF", label: "启用" },
                  };
                  const st = statusStyles[s] || { color: "#6B6B6B", bg: "#F5F3F0", label: s };
                  return <span style={{ padding: "2px 12px", borderRadius: 6, fontSize: 12, color: st.color, background: st.bg }}>{st.label}</span>;
                }},
              ]}
            />
            <Button
              type="primary"
              size="large"
              loading={creating}
              disabled={selectedIds.length === 0}
              onClick={handleCreateProject}
            >
              下一步：填写变量（已选 {selectedIds.length} 个模板）
            </Button>
          </Space>
        </Card>
      )}

      {/* Step 2 */}
      {current === 1 && dedupInfo && (
        <Card title={<span style={{ fontFamily: "'Cormorant Garamond', Georgia, serif", fontSize: 17, fontWeight: 500 }}>填写变量</span>}>
          <Space direction="vertical" style={{ width: "100%" }} size="middle">
            <Alert
              type="info"
              message={`去重结果：${dedupInfo.total_variables_before_dedup} 个变量 → ${dedupInfo.total_variables_after_dedup} 个（减少 ${dedupInfo.total_variables_before_dedup - dedupInfo.total_variables_after_dedup} 个重复）`}
            />

            {/* 手动填写变量 */}
            <Form layout="vertical" style={{ maxWidth: 600 }}>
              {dedupInfo.variables.map((v) => {
                const sources = dedupInfo.variable_sources[v.name] || [];
                const isShared = sources.length > 1;
                return (
                  <Form.Item
                    key={v.name}
                    label={
                      <Space>
                        <span>{v.display_name || v.name}</span>
                        {isShared && <Tag color="gold" style={{ borderRadius: 6, fontSize: 11 }}>共享（{sources.length} 个模板）</Tag>}
                      </Space>
                    }
                  >
                    <Input
                      value={varValues[v.name] || ""}
                      onChange={(e) =>
                        setVarValues((prev) => ({ ...prev, [v.name]: e.target.value }))
                      }
                      placeholder={`请输入${v.display_name || v.name}`}
                    />
                  </Form.Item>
                );
              })}
            </Form>

            <Divider>或通过 Excel 批量导入</Divider>

            {/* Excel 上传 + 多行预览 */}
            <Space>
              <Upload
                accept=".xlsx,.xls"
                showUploadList={false}
                beforeUpload={(file) => { handleExcelUpload(file); return false; }}
              >
                <Button icon={<UploadOutlined />} loading={parsingExcel}>
                  上传 Excel
                </Button>
              </Upload>
              {project && (
                <Button
                  icon={<FileExcelOutlined />}
                  onClick={() => {
                    projectApi.downloadExcelTemplate(project.id).catch(() => {
                      message.error("下载导入模板失败");
                    });
                  }}
                >
                  下载导入模板
                </Button>
              )}
              {excelData && (
                <Button
                  type="link"
                  danger
                  icon={<DeleteOutlined />}
                  onClick={() => { setExcelData(null); setSelectedRowKeys([]); }}
                >
                  清除 Excel 数据
                </Button>
              )}
            </Space>

            {excelData && (
              <>
                <Alert
                  type="success"
                  message={`已解析 ${excelData.total_rows} 行数据，已选 ${selectedRowKeys.length} 行`}
                />
                <Table
                  rowKey={(_, index) => index!}
                  size="small"
                  dataSource={excelData.rows}
                  scroll={{ x: true }}
                  rowSelection={{
                    selectedRowKeys: selectedRowKeys,
                    onChange: (keys) => setSelectedRowKeys(keys as number[]),
                  }}
                  pagination={excelData.total_rows > 20 ? { pageSize: 20 } : false}
                  columns={[
                    { title: "#", render: (_: unknown, __: unknown, index: number) => index + 1, width: 50 },
                    ...excelData.headers.map((h) => ({
                      title: h,
                      dataIndex: h,
                      key: h,
                      ellipsis: true,
                    })),
                  ]}
                />
              </>
            )}

            <Space>
              <Button onClick={() => setCurrent(0)}>上一步</Button>
              <Button
                type="primary"
                loading={generating}
                disabled={excelData ? selectedRowKeys.length === 0 : !Object.values(varValues).some((v) => v.trim())}
                onClick={handleGenerate}
              >
                {excelData
                  ? `生成签字页（${selectedRowKeys.length} 行 × ${project?.templates.length || 0} 个模板）`
                  : "生成签字页"}
              </Button>
            </Space>
          </Space>
        </Card>
      )}

      {/* Step 3 */}
      {current === 2 && (
        <Card title={<span style={{ fontFamily: "'Cormorant Garamond', Georgia, serif", fontSize: 17, fontWeight: 500 }}>生成与下载</span>}>
          <Space direction="vertical" style={{ width: "100%" }} size="middle">
            {/* 异步任务状态 */}
            {taskId && taskStatus && (
              <>
                {isTaskRunning && (
                  <Alert
                    type="info"
                    message="正在生成签字页..."
                    description={
                      <Progress
                        percent={taskStatus.total > 0 ? Math.round((taskStatus.progress / taskStatus.total) * 100) : undefined}
                        status="active"
                      />
                    }
                  />
                )}
                {isTaskFailed && (
                  <Alert type="error" message={`生成失败：${taskStatus.error || "未知错误"}`} />
                )}
                {isTaskDone && (
                  <Alert
                    type="success"
                    message={`生成完成，共 ${taskStatus.result?.count || 0} 份签字页`}
                  />
                )}
              </>
            )}

            {/* 手动模式的合同列表 */}
            {contracts.length > 0 && (
              <Table
                rowKey="id"
                size="small"
                dataSource={contracts}
                pagination={false}
                columns={[
                  { title: "标题", dataIndex: "title", ellipsis: true },
                  { title: "状态", dataIndex: "status", render: (s: string) => (
                    <span style={{ padding: "2px 12px", borderRadius: 6, fontSize: 12, color: "#5B8C5A", background: "#EFF5EF", fontWeight: 500 }}>{s}</span>
                  ) },
                  {
                    title: "操作",
                    render: (_: unknown, r: ContractResponse) => (
                      <Button
                        type="link"
                        icon={<DownloadOutlined />}
                        onClick={() => {
                          contractApi.downloadContract(r.id, "word").catch(() => {
                            message.error("下载失败");
                          });
                        }}
                      >
                        下载 Word
                      </Button>
                    ),
                  },
                ]}
              />
            )}

            {/* 下载按钮区 */}
            <Space>
              {/* 异步任务完成后：下载 zip */}
              {taskId && isTaskDone && (
                <Button
                  type="primary"
                  icon={<FileZipOutlined />}
                  onClick={() => {
                    contractApi.downloadTaskZip(taskId).catch(() => {
                      message.error("下载失败");
                    });
                  }}
                >
                  下载全部（ZIP）
                </Button>
              )}
              {/* 手动模式且项目存在：下载项目 zip */}
              {!taskId && contracts.length > 0 && project && (
                <Button
                  icon={<FileZipOutlined />}
                  onClick={() => {
                    contractApi.downloadProjectZip(project.id).catch(() => {
                      message.error("下载失败");
                    });
                  }}
                >
                  打包下载全部（ZIP）
                </Button>
              )}
              <Button onClick={() => setCurrent(1)}>上一步</Button>
              <Button onClick={() => navigate("/")}>返回首页</Button>
            </Space>
          </Space>
        </Card>
      )}
    </div>
  );
}
