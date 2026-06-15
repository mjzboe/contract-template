"""合同相关的 Pydantic 请求/响应 schema"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ContractGenerate(BaseModel):
    """生成合同请求"""
    title: str = Field(..., min_length=1, max_length=200)
    template_id: uuid.UUID
    template_version_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None
    variables: dict[str, str] = Field(..., description="变量名 → 值映射")


class ContractPreview(BaseModel):
    """预览请求"""
    template_id: uuid.UUID
    template_version_id: uuid.UUID | None = None
    variables: dict[str, str] = Field(..., description="变量名 → 值映射")


class ContractPreviewResponse(BaseModel):
    """预览响应"""
    preview_text: str


class ContractResponse(BaseModel):
    id: uuid.UUID
    title: str
    project_id: uuid.UUID | None = None
    template_id: uuid.UUID
    template_version_id: uuid.UUID | None = None
    variables: dict = {}
    file_path: str | None = None
    file_path_pdf: str | None = None
    status: str = "draft"
    archived_at: datetime | None = None
    status_history: list = []
    created_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContractListResponse(BaseModel):
    items: list[ContractResponse]
    total: int
    page: int
    page_size: int


class ContractExportResponse(BaseModel):
    """导出响应"""
    contract_id: uuid.UUID
    format: str
    download_url: str


class ExcelParseResponse(BaseModel):
    """Excel 解析响应（只解析不生成）"""
    headers: list[str] = Field(..., description="表头（变量名）")
    rows: list[dict[str, str]] = Field(..., description="每行数据，key 为变量名")
    total_rows: int = Field(..., description="数据行数")


class BatchGenerateFromRows(BaseModel):
    """从多行变量批量生成合同"""
    project_id: uuid.UUID
    rows: list[dict[str, str]] = Field(..., description="每行变量映射")
    selected_indices: list[int] = Field(..., description="选中的行索引（0-based）")


class AsyncTaskResponse(BaseModel):
    """异步任务状态响应"""
    task_id: str
    task_type: str
    status: str
    progress: int = 0
    total: int = 0
    result: dict | list | None = None
    error: str | None = None


class ArchiveListItem(BaseModel):
    """归档列表项（含关联名称）"""
    id: uuid.UUID
    title: str
    status: str = "archived"
    archived_at: datetime | None = None
    template_id: uuid.UUID | None = None
    template_name: str | None = None
    project_id: uuid.UUID | None = None
    project_name: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ArchiveListResponse(BaseModel):
    items: list[ArchiveListItem]
    total: int
    page: int
    page_size: int


class StatusHistoryEntry(BaseModel):
    """状态变更记录"""
    status: str
    at: str


class ArchiveDetail(BaseModel):
    """归档详情（含时间线和变量）"""
    id: uuid.UUID
    title: str
    status: str = "archived"
    archived_at: datetime | None = None
    template_id: uuid.UUID | None = None
    template_name: str | None = None
    project_id: uuid.UUID | None = None
    project_name: str | None = None
    variables: dict = {}
    status_history: list[StatusHistoryEntry] = []
    file_path: str | None = None
    file_path_pdf: str | None = None
    created_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
