// 类型定义 — 与后端 Pydantic schema 对齐

// ========== 通用分页 ==========
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

// ========== 变量 ==========
export interface VariableInfoResponse {
  name: string;
  display_name: string;
  var_type: string;
  default_value: string;
  validation_rule: string;
  occurrences: number;
}

// ========== 模板 ==========
export interface TemplateVersionResponse {
  id: string;
  version_number: string;
  file_path: string;
  variables: VariableInfoResponse[];
  is_master: boolean;
  change_log: string | null;
  created_at: string;
}

export interface TemplateResponse {
  id: string;
  name: string;
  category_id: string | null;
  tags: string[];
  description: string | null;
  status: string;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  versions: TemplateVersionResponse[];
}

export interface TemplateUploadResponse {
  template: TemplateResponse;
  variables: VariableInfoResponse[];
}

// ========== 项目 ==========
export interface ProjectResponse {
  id: string;
  name: string;
  description: string | null;
  status: string;
  deduplicated_variables: VariableInfoResponse[];
  created_by: string | null;
  created_at: string;
  updated_at: string;
  templates: TemplateResponse[];
}

export interface DeduplicatedVariablesResponse {
  project_id: string;
  template_count: number;
  total_variables_before_dedup: number;
  total_variables_after_dedup: number;
  variables: VariableInfoResponse[];
  variable_sources: Record<string, string[]>;
}

// ========== 合同 ==========
export interface ContractResponse {
  id: string;
  title: string;
  project_id: string | null;
  template_id: string;
  template_version_id: string | null;
  variables: Record<string, string>;
  file_path: string | null;
  file_path_pdf: string | null;
  status: string;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface ContractPreviewResponse {
  preview_text: string;
}

export interface ExcelParseResponse {
  headers: string[];
  rows: Record<string, string>[];
  total_rows: number;
}

export interface BatchGenerateFromRowsRequest {
  project_id: string;
  rows: Record<string, string>[];
  selected_indices: number[];
}

export interface AsyncTaskResponse {
  task_id: string;
  task_type: string;
  status: "pending" | "running" | "completed" | "failed";
  progress: number;
  total: number;
  result: {
    contract_ids?: string[];
    zip_path?: string;
    count?: number;
  } | null;
  error: string | null;
}

// ========== 旧类型（兼容） ==========
export interface Template extends TemplateResponse {}
export interface Variable extends VariableInfoResponse {}
export interface Contract extends ContractResponse {}
