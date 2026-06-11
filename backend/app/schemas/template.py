"""模板相关的 Pydantic 请求/响应 schema"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# --- 变量信息 ---
class VariableInfoResponse(BaseModel):
    name: str
    display_name: str = ""
    var_type: str = "text"
    default_value: str = ""
    validation_rule: str = ""
    occurrences: int = 1

    model_config = {"from_attributes": True}


# --- 分类 ---
class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    parent_id: uuid.UUID | None = None
    sort_order: int = 0


class CategoryResponse(BaseModel):
    id: uuid.UUID
    name: str
    parent_id: uuid.UUID | None = None
    sort_order: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


# --- 模板 ---
class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    category_id: uuid.UUID | None = None
    tags: list[str] = []
    description: str | None = None


class TemplateUpdate(BaseModel):
    name: str | None = None
    category_id: uuid.UUID | None = None
    tags: list[str] | None = None
    description: str | None = None
    status: str | None = None


class TemplateVersionResponse(BaseModel):
    id: uuid.UUID
    version_number: str
    file_path: str
    variables: list[dict] = []
    is_master: bool = False
    change_log: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TemplateResponse(BaseModel):
    id: uuid.UUID
    name: str
    category_id: uuid.UUID | None = None
    tags: list = []
    description: str | None = None
    status: str = "draft"
    created_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
    versions: list[TemplateVersionResponse] = []

    model_config = {"from_attributes": True}


class TemplateListResponse(BaseModel):
    items: list[TemplateResponse]
    total: int
    page: int
    page_size: int


# --- 模板上传响应 ---
class TemplateUploadResponse(BaseModel):
    """上传模板后的响应，包含解析出的变量"""

    template: TemplateResponse
    variables: list[VariableInfoResponse]
