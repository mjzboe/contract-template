import api from "./index";
import type {
  ArchiveListItem,
  ArchiveDetail,
  PaginatedResponse,
} from "../types";

// 归档列表
export async function listArchives(params?: {
  page?: number;
  page_size?: number;
  keyword?: string;
  template_id?: string;
  project_id?: string;
  date_from?: string;
  date_to?: string;
}) {
  const res = await api.get<PaginatedResponse<ArchiveListItem>>("/archives", { params });
  return res.data;
}

// 归档详情
export async function getArchiveDetail(id: string) {
  const res = await api.get<ArchiveDetail>(`/archives/${id}`);
  return res.data;
}

// 获取归档文件下载 URL
export function getArchiveDownloadUrl(id: string, format: string = "word") {
  return `/api/v1/archives/${id}/download?format=${format}`;
}
