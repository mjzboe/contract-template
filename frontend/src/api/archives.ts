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

// 带认证的归档文件下载
export async function downloadArchive(id: string, format: string = "word") {
  const token = localStorage.getItem("token");
  const res = await fetch(getArchiveDownloadUrl(id, format), {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "下载失败");
  }
  const blob = await res.blob();
  const disposition = res.headers.get("content-disposition");
  let filename = `archive_${id}.docx`;
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
