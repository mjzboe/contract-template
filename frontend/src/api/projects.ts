import api from "./index";
import type {
  ProjectResponse,
  DeduplicatedVariablesResponse,
  PaginatedResponse,
} from "../types";

// 创建项目
export async function createProject(data: {
  name: string;
  description?: string;
  template_ids: string[];
}) {
  const res = await api.post<ProjectResponse>("/projects", data);
  return res.data;
}

// 项目列表
export async function listProjects(params?: {
  page?: number;
  page_size?: number;
  keyword?: string;
  status?: string;
}) {
  const res = await api.get<PaginatedResponse<ProjectResponse>>("/projects", { params });
  return res.data;
}

// 项目详情
export async function getProject(id: string) {
  const res = await api.get<ProjectResponse>(`/projects/${id}`);
  return res.data;
}

// 更新项目
export async function updateProject(id: string, data: Record<string, unknown>) {
  const res = await api.put<ProjectResponse>(`/projects/${id}`, data);
  return res.data;
}

// 删除项目
export async function deleteProject(id: string) {
  await api.delete(`/projects/${id}`);
}

// 获取去重变量
export async function getDeduplicatedVariables(id: string) {
  const res = await api.get<DeduplicatedVariablesResponse>(
    `/projects/${id}/deduplicated-variables`
  );
  return res.data;
}

// 获取 Excel 导入模板下载 URL（仅用于带 token 的 fetch 下载）
export function getExcelTemplateUrl(projectId: string) {
  return `/api/v1/projects/${projectId}/excel-template`;
}

// 带认证的 Excel 模板下载
export async function downloadExcelTemplate(projectId: string) {
  const token = localStorage.getItem("token");
  const res = await fetch(getExcelTemplateUrl(projectId), {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "下载失败");
  }
  const blob = await res.blob();
  const disposition = res.headers.get("content-disposition");
  let filename = `导入模板_${projectId}.xlsx`;
  if (disposition) {
    const match = disposition.match(/filename\*?=(?:UTF-8'')?"?([^";\n]+)"?/i);
    if (match) filename = decodeURIComponent(match[1].trim());
  }
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
