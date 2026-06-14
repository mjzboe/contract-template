"""档案归档 API 路由"""

import os
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role
from app.models.user import User
from app.schemas.contract import ArchiveDetail, ArchiveListResponse, ArchiveListItem
from app.services import archive_service

router = APIRouter(prefix="/archives", tags=["档案归档"])


@router.get("", response_model=ArchiveListResponse)
async def list_archives(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    template_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("super_admin", "template_admin", "approver", "user")),
):
    """归档列表（支持关键词、模板、项目、时间范围过滤）"""
    items, total = await archive_service.list_archives(
        db, page, page_size, keyword, template_id, project_id, date_from, date_to
    )
    return ArchiveListResponse(
        items=[ArchiveListItem(**item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{contract_id}", response_model=ArchiveDetail)
async def get_archive_detail(
    contract_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("super_admin", "template_admin", "approver", "user")),
):
    """归档详情（含操作时间线和变量）"""
    detail = await archive_service.get_archive_detail(db, contract_id)
    if not detail:
        raise HTTPException(status_code=404, detail="归档记录不存在")
    return ArchiveDetail(**detail)


@router.get("/{contract_id}/download")
async def download_archive(
    contract_id: uuid.UUID,
    format: str = Query("word", regex="^(word|docx|pdf)$"),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("super_admin", "template_admin", "approver", "user")),
):
    """下载归档文件"""
    file_path = await archive_service.get_archive_file_path(db, contract_id, format)
    if not file_path:
        if format == "pdf":
            raise HTTPException(status_code=501, detail="PDF 转换不可用，请确保已安装 LibreOffice")
        raise HTTPException(status_code=404, detail="归档记录或文件不存在")

    await db.commit()

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件已丢失")

    filename = os.path.basename(file_path)
    # PDF 文件名确保后缀为 .pdf
    if format == "pdf" and not filename.lower().endswith(".pdf"):
        filename = os.path.splitext(filename)[0] + ".pdf"
    media_type = (
        "application/pdf" if format == "pdf"
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=media_type,
    )
