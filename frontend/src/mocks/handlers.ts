import { http, HttpResponse } from "msw";

const mockTemplate = {
  id: "mock-template-id-1",
  name: "测试模板",
  category_id: null,
  tags: [],
  description: null,
  status: "draft",
  created_by: null,
  created_at: "2024-01-01T00:00:00",
  updated_at: "2024-01-01T00:00:00",
  versions: [
    {
      id: "mock-version-id-1",
      version_number: "v1",
      file_path: "/uploads/test.docx",
      variables: [
        { name: "公司名称", display_name: "公司名称", var_type: "text", default_value: "", validation_rule: "", occurrences: 2 },
        { name: "法定代表人", display_name: "法定代表人", var_type: "text", default_value: "", validation_rule: "", occurrences: 1 },
        { name: "日期", display_name: "日期", var_type: "date", default_value: "", validation_rule: "", occurrences: 1 },
      ],
      is_master: true,
      change_log: "初始版本",
      created_at: "2024-01-01T00:00:00",
    },
  ],
};

const mockProject = {
  id: "mock-project-id-1",
  name: "测试项目",
  description: null,
  status: "draft",
  deduplicated_variables: [
    { name: "公司名称", display_name: "公司名称", var_type: "text", default_value: "", validation_rule: "", occurrences: 2 },
    { name: "法定代表人", display_name: "法定代表人", var_type: "text", default_value: "", validation_rule: "", occurrences: 1 },
    { name: "日期", display_name: "日期", var_type: "date", default_value: "", validation_rule: "", occurrences: 1 },
  ],
  created_by: null,
  created_at: "2024-01-01T00:00:00",
  updated_at: "2024-01-01T00:00:00",
  templates: [mockTemplate],
};

const mockContract = {
  id: "mock-contract-id-1",
  title: "测试合同",
  project_id: "mock-project-id-1",
  template_id: "mock-template-id-1",
  template_version_id: null,
  variables: { 公司名称: "XX科技", 法定代表人: "张三", 日期: "2024-01-01" },
  file_path: "/uploads/contracts/test.docx",
  file_path_pdf: null,
  status: "generated",
  created_by: null,
  created_at: "2024-01-01T00:00:00",
  updated_at: "2024-01-01T00:00:00",
};

export const handlers = [
  http.get("/api/v1/health", () => HttpResponse.json({ status: "ok" })),

  http.get("/api/v1/templates", () =>
    HttpResponse.json({ items: [mockTemplate], total: 1, page: 1, page_size: 20 })
  ),
  http.post("/api/v1/templates", async () =>
    HttpResponse.json(
      { template: mockTemplate, variables: mockTemplate.versions[0].variables },
      { status: 200 }
    )
  ),
  http.get("/api/v1/templates/:id", () => HttpResponse.json(mockTemplate)),
  http.delete("/api/v1/templates/:id", () => HttpResponse.json({ message: "删除成功" })),
  http.get("/api/v1/templates/:id/variables", () =>
    HttpResponse.json(mockTemplate.versions[0].variables)
  ),

  http.get("/api/v1/projects", () =>
    HttpResponse.json({ items: [mockProject], total: 1, page: 1, page_size: 20 })
  ),
  http.post("/api/v1/projects", async () => HttpResponse.json(mockProject)),
  http.get("/api/v1/projects/:id", () => HttpResponse.json(mockProject)),
  http.get("/api/v1/projects/:id/deduplicated-variables", () =>
    HttpResponse.json({
      project_id: "mock-project-id-1",
      template_count: 1,
      total_variables_before_dedup: 3,
      total_variables_after_dedup: 3,
      variables: mockProject.deduplicated_variables,
      variable_sources: { 公司名称: ["测试模板"], 法定代表人: ["测试模板"], 日期: ["测试模板"] },
    })
  ),

  http.get("/api/v1/contracts", () =>
    HttpResponse.json({ items: [mockContract], total: 1, page: 1, page_size: 20 })
  ),
  http.post("/api/v1/contracts", async () => HttpResponse.json(mockContract)),
  http.post("/api/v1/contracts/preview", async () =>
    HttpResponse.json({ preview_text: "甲方：XX科技 法定代表人：张三 日期：2024-01-01" })
  ),
  http.post("/api/v1/contracts/parse-excel", async () =>
    HttpResponse.json({
      headers: ["公司名称", "法定代表人", "日期"],
      rows: [
        { 公司名称: "公司A", 法定代表人: "张三", 日期: "2024-01-01" },
        { 公司名称: "公司B", 法定代表人: "李四", 日期: "2024-01-02" },
      ],
      total_rows: 2,
    })
  ),
  http.post("/api/v1/contracts/batch-from-rows-async", async () =>
    HttpResponse.json({
      task_id: "mock-task-id",
      task_type: "batch_generate",
      status: "completed",
      progress: 2,
      total: 2,
      result: { contract_ids: ["mock-contract-id-1"], zip_path: "/uploads/zip/test.zip", count: 2 },
      error: null,
    })
  ),
  http.get("/api/v1/contracts/tasks/:id", () =>
    HttpResponse.json({
      task_id: "mock-task-id",
      task_type: "batch_generate",
      status: "completed",
      progress: 2,
      total: 2,
      result: { contract_ids: ["mock-contract-id-1"], zip_path: "/uploads/zip/test.zip", count: 2 },
      error: null,
    })
  ),
];
