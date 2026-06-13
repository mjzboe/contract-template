"""合同生成 API 路由"""

import asyncio
import os
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role
from app.models.user import User
from app.schemas.contract import (
    AsyncTaskResponse,
    BatchGenerateFromRows,
    ContractGenerate,
    ContractListResponse,
    ContractPreview,
    ContractPreviewResponse,
    ContractResponse,
    ExcelParseResponse,
)
from app.services import contract_service
from app.services.task_manager import AsyncTask, TaskStatus, create_task, get_task, run_task
from app.services.template_service import save_upload_file

router = APIRouter(prefix="/contracts", tags=["合同生成"])


@router.post("/preview", response_model=ContractPreviewResponse)
async def preview_contract(
    data: ContractPreview,
    db: AsyncSession = Depends(get_db),
):
    """预览：替换变量后返回文档文本内容"""
    try:
        preview_text = await contract_service.preview_contract(
            db, data.template_id, data.variables, data.template_version_id
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return ContractPreviewResponse(preview_text=preview_text)


@router.post("", response_model=ContractResponse)
async def generate_contract(
    data: ContractGenerate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("user", "template_admin", "approver", "super_admin")),
):
    """生成合同文档"""
    try:
        contract = await contract_service.generate_contract(
            db,
            title=data.title,
            template_id=data.template_id,
            variables=data.variables,
            project_id=data.project_id,
            template_version_id=data.template_version_id,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    await db.commit()
    return ContractResponse.model_validate(contract)


@router.get("", response_model=ContractListResponse)
async def list_contracts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    project_id: uuid.UUID | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """合同列表"""
    contracts, total = await contract_service.list_contracts(
        db, page, page_size, project_id, status
    )
    return ContractListResponse(
        items=[ContractResponse.model_validate(c) for c in contracts],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{contract_id}", response_model=ContractResponse)
async def get_contract(
    contract_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """合同详情"""
    contract = await contract_service.get_contract(db, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")
    return ContractResponse.model_validate(contract)


@router.get("/{contract_id}/export")
async def export_contract(
    contract_id: uuid.UUID,
    format: str = Query("word", regex="^(word|docx|pdf)$"),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("user", "template_admin", "approver", "super_admin")),
):
    """导出合同文件（下载）"""
    file_path = await contract_service.export_contract(db, contract_id, format)
    if not file_path:
        if format == "pdf":
            raise HTTPException(status_code=501, detail="PDF 转换不可用，请确保已安装 LibreOffice")
        raise HTTPException(status_code=404, detail="合同或文件不存在")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件已丢失")

    filename = os.path.basename(file_path)
    media_type = (
        "application/pdf" if format == "pdf"
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=media_type,
    )


@router.post("/batch", response_model=list[ContractResponse])
async def batch_generate(
    template_id: uuid.UUID = Form(...),
    excel_file: UploadFile = File(...),
    project_id: uuid.UUID | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("user", "template_admin", "approver", "super_admin")),
):
    """批量生成合同：上传 Excel 文件，表头为变量名，每行为一组数据"""
    if not excel_file.filename or not excel_file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="仅支持 Excel 文件（.xlsx/.xls）")

    from app.config import settings

    file_content = await excel_file.read()
    excel_path = await save_upload_file(
        file_content, excel_file.filename, os.path.join(settings.UPLOAD_DIR, "excel")
    )

    try:
        contracts = await contract_service.batch_generate_from_excel(
            db, template_id, excel_path, project_id, user_id=current_user.id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await db.commit()
    return [ContractResponse.model_validate(c) for c in contracts]


@router.post("/parse-excel", response_model=ExcelParseResponse)
async def parse_excel(
    excel_file: UploadFile = File(...),
):
    """解析 Excel 文件，返回表头和行数据（不生成合同，供前端预览）"""
    if not excel_file.filename or not excel_file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="仅支持 Excel 文件（.xlsx/.xls）")

    from app.config import settings
    file_content = await excel_file.read()
    excel_path = await save_upload_file(
        file_content, excel_file.filename, os.path.join(settings.UPLOAD_DIR, "excel")
    )

    try:
        headers, rows = await contract_service.parse_excel(excel_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return ExcelParseResponse(headers=headers, rows=rows, total_rows=len(rows))


@router.post("/batch-from-rows", response_model=list[ContractResponse])
async def batch_generate_from_rows(
    data: BatchGenerateFromRows,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("user", "template_admin", "approver", "super_admin")),
):
    """从选中的行数据批量生成合同（每个模板各生成一份）"""
    try:
        contracts = await contract_service.batch_generate_from_rows(
            db, data.project_id, data.rows, data.selected_indices, user_id=current_user.id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await db.commit()
    return [ContractResponse.model_validate(c) for c in contracts]


@router.post("/batch-from-rows-async", response_model=AsyncTaskResponse)
async def batch_generate_from_rows_async(
    data: BatchGenerateFromRows,
    current_user: User = Depends(require_role("user", "template_admin", "approver", "super_admin")),
):
    """异步批量生成合同（返回任务 ID，前端轮询状态）"""
    task = create_task("batch_generate")

    async def _do_generate():
        from app.database import async_session_factory
        async with async_session_factory() as session:
            contracts = await contract_service.batch_generate_from_rows(
                session, data.project_id, data.rows, data.selected_indices, user_id=current_user.id
            )
            await session.commit()
            for c in contracts:
                await session.refresh(c)
            zip_path = contract_service.build_zip(contracts)
            return {
                "contract_ids": [str(c.id) for c in contracts],
                "zip_path": zip_path,
                "count": len(contracts),
            }

    asyncio.create_task(run_task(task, _do_generate()))
    return _task_to_response(task)


@router.get("/tasks/{task_id}", response_model=AsyncTaskResponse)
async def get_task_status(task_id: str):
    """查询异步任务状态"""
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return _task_to_response(task)


@router.get("/tasks/{task_id}/download-zip")
async def download_task_zip(task_id: str):
    """下载异步任务生成的 zip 文件"""
    task = get_task(task_id)
    if not task or task.status != TaskStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="任务未完成或不存在")

    result = task.result or {}
    zip_path = result.get("zip_path")
    if not zip_path or not os.path.exists(zip_path):
        raise HTTPException(status_code=404, detail="zip 文件不存在")

    filename = os.path.basename(zip_path)
    return FileResponse(
        path=zip_path,
        filename=filename,
        media_type="application/zip",
    )


@router.get("/project/{project_id}/download-zip")
async def download_project_zip(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """下载项目下所有合同的 zip 包"""
    contracts, _ = await contract_service.list_contracts(
        db, page=1, page_size=1000, project_id=project_id
    )
    if not contracts:
        raise HTTPException(status_code=404, detail="项目下无合同")

    zip_path = contract_service.build_zip(contracts)
    filename = os.path.basename(zip_path)
    return FileResponse(
        path=zip_path,
        filename=filename,
        media_type="application/zip",
    )


def _task_to_response(task: AsyncTask) -> AsyncTaskResponse:
    return AsyncTaskResponse(
        task_id=task.id,
        task_type=task.task_type,
        status=task.status.value,
        progress=task.progress,
        total=task.total,
        result=task.result,
        error=task.error,
    )


@router.delete("/{contract_id}")
async def delete_contract(
    contract_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("super_admin")),
):
    """删除合同"""
    success = await contract_service.delete_contract(db, contract_id)
    if not success:
        raise HTTPException(status_code=404, detail="合同不存在")
    await db.commit()
    return {"message": "删除成功"}
