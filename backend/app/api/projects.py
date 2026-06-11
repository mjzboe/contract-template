"""项目管理 API 路由"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.schemas.project import (
    DeduplicatedVariablesResponse,
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
    VariableInfoResponse,
)
from app.schemas.template import VariableInfoResponse as TemplateVarResp
from app.services import project_service

router = APIRouter(prefix="/projects", tags=["项目管理"])


@router.post("", response_model=ProjectResponse)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """创建项目，关联模板并自动变量去重"""
    user_id = None
    uid = current_user.get("user_id")
    if uid and uid != "dev-user":
        try:
            user_id = uuid.UUID(uid)
        except (ValueError, AttributeError):
            user_id = None

    project = await project_service.create_project(db, data, user_id)
    await db.commit()
    return ProjectResponse.model_validate(project)


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """项目列表"""
    projects, total = await project_service.list_projects(
        db, page, page_size, keyword, status
    )
    return ProjectListResponse(
        items=[ProjectResponse.model_validate(p) for p in projects],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """项目详情"""
    project = await project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return ProjectResponse.model_validate(project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新项目信息（如更新模板列表会自动重新去重）"""
    project = await project_service.update_project(db, project_id, data)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    await db.commit()
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}")
async def delete_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """删除项目"""
    success = await project_service.delete_project(db, project_id)
    if not success:
        raise HTTPException(status_code=404, detail="项目不存在")
    await db.commit()
    return {"message": "删除成功"}


@router.get("/{project_id}/deduplicated-variables", response_model=DeduplicatedVariablesResponse)
async def get_deduplicated_variables(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """获取项目的跨模板去重变量，含来源映射"""
    result = await project_service.get_deduplicated_variables(db, project_id)
    if not result:
        raise HTTPException(status_code=404, detail="项目不存在")

    return DeduplicatedVariablesResponse(
        project_id=result["project_id"],
        template_count=result["template_count"],
        total_variables_before_dedup=result["total_variables_before_dedup"],
        total_variables_after_dedup=result["total_variables_after_dedup"],
        variables=[TemplateVarResp(**v) for v in result["variables"]],
        variable_sources=result["variable_sources"],
    )