"""项目相关的 Pydantic 请求/响应 schema"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.template import TemplateResponse, VariableInfoResponse


# --- 项目创建/更新 ---
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    template_ids: list[uuid.UUID] = []


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    template_ids: list[uuid.UUID] | None = None


# --- 项目响应 ---
class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    status: str = "draft"
    deduplicated_variables: list[dict] = []
    created_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
    templates: list[TemplateResponse] = []

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
    page: int
    page_size: int


# --- 变量去重响应 ---
class DeduplicatedVariablesResponse(BaseModel):
    """跨模板变量去重结果"""

    project_id: uuid.UUID
    template_count: int
    total_variables_before_dedup: int
    total_variables_after_dedup: int
    variables: list[VariableInfoResponse]
    # 每个变量出现在哪些模板中
    variable_sources: dict[str, list[str]] = Field(
        default_factory=dict,
        description="变量名 → 模板名称列表",
    )
