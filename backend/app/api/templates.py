"""模板管理 API 路由"""

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.schemas.template import (
    TemplateListResponse,
    TemplateResponse,
    TemplateUploadResponse,
    TemplateUpdate,
    VariableInfoResponse,
)
from app.services import template_service

router = APIRouter(prefix="/templates", tags=["模板管理"])


@router.post("", response_model=TemplateUploadResponse)
async def create_template(
    name: str = Form(..., min_length=1, max_length=200),
    file: UploadFile = File(...),
    category_id: uuid.UUID | None = Form(None),
    tags: str = Form("[]"),
    description: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """上传模板文件并自动解析变量"""
    # 验证文件类型
    if not file.filename or not file.filename.endswith((".docx", ".doc")):
        raise HTTPException(status_code=400, detail="仅支持 Word 文档（.docx/.doc）")

    # 保存文件
    import json

    from app.config import settings

    file_content = await file.read()
    file_path = await template_service.save_upload_file(
        file_content, file.filename, settings.UPLOAD_DIR
    )

    # 创建模板 + 解析变量
    try:
        import json as _json

        tags_list = _json.loads(tags) if isinstance(tags, str) else tags
    except (json.JSONDecodeError, TypeError):
        tags_list = []

    from app.schemas.template import TemplateCreate

    data = TemplateCreate(
        name=name,
        category_id=category_id,
        tags=tags_list,
        description=description,
    )

    user_id = None
    uid = current_user.get("user_id")
    if uid and uid != "dev-user":
        try:
            user_id = uuid.UUID(uid)
        except (ValueError, AttributeError):
            user_id = None

    template, variables = await template_service.create_template(
        db, data, file_path, user_id=user_id
    )
    await db.commit()

    return TemplateUploadResponse(
        template=TemplateResponse.model_validate(template),
        variables=[VariableInfoResponse(**v.__dict__) for v in variables],
    )


@router.get("", response_model=TemplateListResponse)
async def list_templates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category_id: uuid.UUID | None = None,
    keyword: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """模板列表（分页 + 筛选）"""
    templates, total = await template_service.list_templates(
        db, page, page_size, category_id, keyword, status
    )
    return TemplateListResponse(
        items=[TemplateResponse.model_validate(t) for t in templates],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """获取模板详情"""
    template = await template_service.get_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    return TemplateResponse.model_validate(template)


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: uuid.UUID,
    data: TemplateUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新模板信息"""
    template = await template_service.update_template(db, template_id, data)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    await db.commit()
    return TemplateResponse.model_validate(template)


@router.delete("/{template_id}")
async def delete_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """删除模板"""
    success = await template_service.delete_template(db, template_id)
    if not success:
        raise HTTPException(status_code=404, detail="模板不存在")
    await db.commit()
    return {"message": "删除成功"}


@router.get("/{template_id}/variables", response_model=list[VariableInfoResponse])
async def get_template_variables(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """获取模板的变量列表"""
    variables = await template_service.get_template_variables(db, template_id)
    if variables is None:
        raise HTTPException(status_code=404, detail="模板或主版本不存在")
    return [VariableInfoResponse(**v.__dict__) for v in variables]
