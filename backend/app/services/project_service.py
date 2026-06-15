"""项目服务层：项目 CRUD、跨模板变量去重"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import Project
from app.models.template import Template, TemplateVersion
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.utils.variable_parser import VariableInfo, deduplicate_variables


async def create_project(
    db: AsyncSession,
    data: ProjectCreate,
    user_id: uuid.UUID | None = None,
) -> Project:
    """创建项目，关联模板并自动去重变量"""
    # 查询选中的模板
    templates = []
    if data.template_ids:
        result = await db.execute(
            select(Template)
            .options(selectinload(Template.versions))
            .where(Template.id.in_(data.template_ids))
        )
        templates = list(result.scalars().all())

    # 从各模板的 master 版本提取变量
    all_variables = await _collect_template_variables(templates)

    # 跨模板去重
    deduped = deduplicate_variables(all_variables)

    # 构建变量来源映射
    var_sources = _build_variable_sources(templates, all_variables)

    # 序列化去重结果
    deduped_dicts = [
        {
            "name": v.name,
            "display_name": v.display_name,
            "var_type": v.var_type,
            "default_value": v.default_value,
            "validation_rule": v.validation_rule,
            "occurrences": v.occurrences,
        }
        for v in deduped
    ]

    project = Project(
        name=data.name,
        description=data.description,
        status="draft",
        deduplicated_variables=deduped_dicts,
        created_by=user_id,
        templates=templates,
    )
    db.add(project)
    await db.flush()
    await db.refresh(project, ["templates"])

    return project


async def get_project(db: AsyncSession, project_id: uuid.UUID) -> Project | None:
    """获取项目详情"""
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.templates).selectinload(Template.versions))
        .where(Project.id == project_id)
    )
    return result.scalar_one_or_none()


async def list_projects(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    status: str | None = None,
    user_id: uuid.UUID | None = None,
    is_admin: bool = False,
) -> tuple[list[Project], int]:
    """项目列表（普通用户只看自己创建的，管理员看全部）"""
    query = select(Project).options(selectinload(Project.templates).selectinload(Template.versions))

    if keyword:
        query = query.where(Project.name.ilike(f"%{keyword}%"))
    if status:
        query = query.where(Project.status == status)
    if not is_admin and user_id:
        query = query.where(Project.created_by == user_id)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(Project.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)

    return list(result.scalars().all()), total


async def update_project(
    db: AsyncSession, project_id: uuid.UUID, data: ProjectUpdate
) -> Project | None:
    """更新项目信息"""
    project = await get_project(db, project_id)
    if not project:
        return None

    # 如果更新了 template_ids，需要重新去重
    if data.template_ids is not None:
        result = await db.execute(
            select(Template)
            .options(selectinload(Template.versions))
            .where(Template.id.in_(data.template_ids))
        )
        templates = list(result.scalars().all())
        project.templates = templates

        all_variables = await _collect_template_variables(templates)
        deduped = deduplicate_variables(all_variables)
        project.deduplicated_variables = [
            {
                "name": v.name,
                "display_name": v.display_name,
                "var_type": v.var_type,
                "default_value": v.default_value,
                "validation_rule": v.validation_rule,
                "occurrences": v.occurrences,
            }
            for v in deduped
        ]

    update_data = data.model_dump(exclude_unset=True, exclude={"template_ids"})
    for key, value in update_data.items():
        setattr(project, key, value)

    await db.flush()
    # 重新查询以确保所有关系正确加载
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.templates).selectinload(Template.versions))
        .where(Project.id == project_id)
    )
    return result.scalar_one_or_none()


async def delete_project(db: AsyncSession, project_id: uuid.UUID) -> bool:
    """删除项目"""
    project = await get_project(db, project_id)
    if not project:
        return False
    await db.delete(project)
    await db.flush()
    return True


async def get_deduplicated_variables(
    db: AsyncSession, project_id: uuid.UUID
) -> dict | None:
    """获取项目的去重变量详情，包含来源信息"""
    project = await get_project(db, project_id)
    if not project:
        return None

    # 从各模板的 master 版本重新提取变量（保证实时性）
    all_variables = await _collect_template_variables(project.templates)
    deduped = deduplicate_variables(all_variables)
    var_sources = _build_variable_sources(project.templates, all_variables)

    total_before = sum(len(v) for v in all_variables)

    return {
        "project_id": project.id,
        "template_count": len(project.templates),
        "total_variables_before_dedup": total_before,
        "total_variables_after_dedup": len(deduped),
        "variables": [
            {
                "name": v.name,
                "display_name": v.display_name,
                "var_type": v.var_type,
                "default_value": v.default_value,
                "validation_rule": v.validation_rule,
                "occurrences": v.occurrences,
            }
            for v in deduped
        ],
        "variable_sources": var_sources,
    }


async def _collect_template_variables(
    templates: list[Template],
) -> list[list[VariableInfo]]:
    """从多个模板的 master 版本中提取变量"""
    all_variables: list[list[VariableInfo]] = []

    for template in templates:
        # 从 versions 关系中找 master 版本
        master = None
        for v in template.versions:
            if v.is_master:
                master = v
                break

        if master and master.variables:
            all_variables.append(
                [
                    VariableInfo(
                        name=var["name"],
                        display_name=var.get("display_name", ""),
                        var_type=var.get("var_type", "text"),
                        default_value=var.get("default_value", ""),
                        validation_rule=var.get("validation_rule", ""),
                        occurrences=var.get("occurrences", 1),
                    )
                    for var in master.variables
                ]
            )
        else:
            all_variables.append([])

    return all_variables


def _build_variable_sources(
    templates: list[Template],
    all_variables: list[list[VariableInfo]],
) -> dict[str, list[str]]:
    """构建变量 → 来源模板的映射"""
    sources: dict[str, list[str]] = {}

    for template, variables in zip(templates, all_variables):
        for var in variables:
            if var.name not in sources:
                sources[var.name] = []
            if template.name not in sources[var.name]:
                sources[var.name].append(template.name)

    return sources
