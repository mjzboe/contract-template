import api from "./index";
import type {
  ContractResponse,
  ContractPreviewResponse,
  ExcelParseResponse,
  BatchGenerateFromRowsRequest,
  AsyncTaskResponse,
  PaginatedResponse,
} from "../types";

// 预览合同
export async function previewContract(data: {
  template_id: string;
  variables: Record<string, string>;
  template_version_id?: string;
}) {
  const res = await api.post<ContractPreviewResponse>("/contracts/preview", data);
  return res.data;
}

// 生成合同
export async function generateContract(data: {
  title: string;
  template_id: string;
  variables: Record<string, string>;
  project_id?: string;
  template_version_id?: string;
}) {
  const res = await api.post<ContractResponse>("/contracts", data);
  return res.data;
}

// 合同列表
export async function listContracts(params?: {
  page?: number;
  page_size?: number;
  project_id?: string;
  status?: string;
}) {
  const res = await api.get<PaginatedResponse<ContractResponse>>("/contracts", { params });
  return res.data;
}

// 合同详情
export async function getContract(id: string) {
  const res = await api.get<ContractResponse>(`/contracts/${id}`);
  return res.data;
}

// 导出/下载合同
export function getExportUrl(id: string, format: string = "word") {
  return `/api/v1/contracts/${id}/export?format=${format}`;
}

// 删除合同
export async function deleteContract(id: string) {
  await api.delete(`/contracts/${id}`);
}

// Excel 批量导入（旧接口，保留兼容）
export async function batchGenerate(formData: FormData) {
  const res = await api.post<ContractResponse[]>("/contracts/batch", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}

// 解析 Excel（只解析不生成）
export async function parseExcel(file: File) {
  const fd = new FormData();
  fd.append("excel_file", file);
  const res = await api.post<ExcelParseResponse>("/contracts/parse-excel", fd, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}

// 从选中行批量生成（同步）
export async function batchGenerateFromRows(data: BatchGenerateFromRowsRequest) {
  const res = await api.post<ContractResponse[]>("/contracts/batch-from-rows", data);
  return res.data;
}

// 从选中行异步批量生成（返回任务 ID）
export async function batchGenerateFromRowsAsync(data: BatchGenerateFromRowsRequest) {
  const res = await api.post<AsyncTaskResponse>("/contracts/batch-from-rows-async", data);
  return res.data;
}

// 查询异步任务状态
export async function getTaskStatus(taskId: string) {
  const res = await api.get<AsyncTaskResponse>(`/contracts/tasks/${taskId}`);
  return res.data;
}

// 获取异步任务 zip 下载 URL
export function getTaskZipDownloadUrl(taskId: string) {
  return `/api/v1/contracts/tasks/${taskId}/download-zip`;
}

// 获取项目 zip 下载 URL
export function getProjectZipDownloadUrl(projectId: string) {
  return `/api/v1/contracts/project/${projectId}/download-zip`;
}