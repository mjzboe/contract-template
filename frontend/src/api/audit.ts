import api from "./index";

export interface AuditLogItem {
  id: string;
  user_id: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  detail: string | null;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
}

export interface AuditLogListResponse {
  items: AuditLogItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface AuditLogQuery {
  page?: number;
  page_size?: number;
  action?: string;
  resource_type?: string;
  user_id?: string;
  start_date?: string;
  end_date?: string;
}

export const auditApi = {
  list: (params: AuditLogQuery = {}) =>
    api.get<AuditLogListResponse>("/audit-logs", { params }),

  get: (id: string) =>
    api.get<AuditLogItem>(`/audit-logs/${id}`),
};
