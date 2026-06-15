"""档案归档服务层：检索、详情、下载"""

import os
import uuid
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contract import Contract
from app.models.project import Project
from app.models.template import Template


async def list_archives(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    template_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    user_id: uuid.UUID | None = None,
    is_admin: bool = False,
) -> tuple[list[dict], int]:
    """归档列表（普通用户只看自己创建的，管理员看全部）"""
    query = (
        select(Contract, Template.name.label("template_name"), Project.name.label("project_name"))
        .outerjoin(Template, Contract.template_id == Template.id)
        .outerjoin(Project, Contract.project_id == Project.id)
        .where(Contract.archived_at.isnot(None))
    )

    if keyword:
        query = query.where(Contract.title.ilike(f"%{keyword}%"))
    if template_id:
        query = query.where(Contract.template_id == template_id)
    if project_id:
        query = query.where(Contract.project_id == project_id)
    if date_from:
        query = query.where(Contract.archived_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.where(Contract.archived_at <= datetime.combine(date_to, datetime.max.time()))
    if not is_admin and user_id:
        query = query.where(Contract.created_by == user_id)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(Contract.archived_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)

    items = []
    for row in result:
        contract = row[0]
        template_name = row[1]
        project_name = row[2]
        items.append({
            "id": contract.id,
            "title": contract.title,
            "status": contract.status,
            "archived_at": contract.archived_at,
            "template_id": contract.template_id,
            "template_name": template_name,
            "project_id": contract.project_id,
            "project_name": project_name,
            "created_at": contract.created_at,
            "updated_at": contract.updated_at,
        })

    return items, total


async def get_archive_detail(
    db: AsyncSession,
    contract_id: uuid.UUID,
) -> dict | None:
    """归档详情（含模板名、项目名、时间线）"""
    query = (
        select(Contract, Template.name.label("template_name"), Project.name.label("project_name"))
        .outerjoin(Template, Contract.template_id == Template.id)
        .outerjoin(Project, Contract.project_id == Project.id)
        .where(Contract.id == contract_id, Contract.archived_at.isnot(None))
    )
    result = await db.execute(query)
    row = result.first()
    if not row:
        return None

    contract = row[0]
    return {
        "id": contract.id,
        "title": contract.title,
        "status": contract.status,
        "archived_at": contract.archived_at,
        "template_id": contract.template_id,
        "template_name": row[1],
        "project_id": contract.project_id,
        "project_name": row[2],
        "variables": contract.variables,
        "status_history": contract.status_history or [],
        "file_path": contract.file_path,
        "file_path_pdf": contract.file_path_pdf,
        "created_by": contract.created_by,
        "created_at": contract.created_at,
        "updated_at": contract.updated_at,
    }


async def get_archive_file_path(
    db: AsyncSession,
    contract_id: uuid.UUID,
    format: str = "word",
) -> str | None:
    """获取归档文件路径"""
    result = await db.execute(
        select(Contract).where(Contract.id == contract_id, Contract.archived_at.isnot(None))
    )
    contract = result.scalar_one_or_none()
    if not contract:
        return None

    if format == "pdf":
        if contract.file_path_pdf and os.path.exists(contract.file_path_pdf):
            return contract.file_path_pdf

        from app.utils.pdf_converter import convert_docx_to_pdf, is_libreoffice_available
        if not is_libreoffice_available():
            return None

        if contract.file_path and os.path.exists(contract.file_path):
            pdf_dir = os.path.dirname(contract.file_path)
            pdf_path = convert_docx_to_pdf(contract.file_path, pdf_dir)
            if pdf_path:
                contract.file_path_pdf = pdf_path
                await db.flush()
                return pdf_path

        return None
    return contract.file_path
