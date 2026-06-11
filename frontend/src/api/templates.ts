import api from "./index";
import type {
  TemplateResponse,
  TemplateUploadResponse,
  VariableInfoResponse,
  PaginatedResponse,
} from "../types";

// 模板列表
export async function listTemplates(params?: {
  page?: number;
  page_size?: number;
  keyword?: string;
  category_id?: string;
  status?: string;
}) {
  const res = await api.get<PaginatedResponse<TemplateResponse>>("/templates", { params });
  return res.data;
}

// 上传模板
export async function uploadTemplate(formData: FormData) {
  const res = await api.post<TemplateUploadResponse>("/templates", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}

// 模板详情
export async function getTemplate(id: string) {
  const res = await api.get<TemplateResponse>(`/templates/${id}`);
  return res.data;
}

// 更新模板
export async function updateTemplate(id: string, data: Record<string, unknown>) {
  const res = await api.put<TemplateResponse>(`/templates/${id}`, data);
  return res.data;
}

// 删除模板
export async function deleteTemplate(id: string) {
  await api.delete(`/templates/${id}`);
}

// 获取模板变量
export async function getTemplateVariables(id: string) {
  const res = await api.get<VariableInfoResponse[]>(`/templates/${id}/variables`);
  return res.data;
}
