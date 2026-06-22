"""模板服务层：模板上传、变量解析、CRUD"""

import os
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.template import Template, TemplateVersion
from app.schemas.template import TemplateCreate, TemplateUpdate
from app.utils.variable_parser import VariableInfo, extract_variables_from_docx


async def create_template(
    db: AsyncSession,
    data: TemplateCreate,
    file_path: str,
    user_id: uuid.UUID | None = None,
) -> tuple[Template, list[VariableInfo]]:
    """创建模板并解析变量，同时创建第一个版本"""
    # 解析变量
    variables = extract_variables_from_docx(file_path)

    # 创建模板
    template = Template(
        name=data.name,
        category_id=data.category_id,
        tags=data.tags,
        description=data.description,
        status="draft",
        created_by=user_id,
    )
    db.add(template)
    await db.flush()

    # 创建第一个版本（v1），标记为 master
    var_dicts = [
        {
            "name": v.name,
            "display_name": v.display_name,
            "var_type": v.var_type,
            "default_value": v.default_value,
            "validation_rule": v.validation_rule,
            "occurrences": v.occurrences,
        }
        for v in variables
    ]
    version = TemplateVersion(
        template_id=template.id,
        version_number="v1",
        file_path=file_path,
        variables=var_dicts,
        is_master=True,
        change_log="初始版本",
        created_by=user_id,
    )
    db.add(version)
    await db.flush()
    await db.refresh(template, ["versions"])

    return template, variables


async def get_template(db: AsyncSession, template_id: uuid.UUID) -> Template | None:
    """获取模板详情"""
    result = await db.execute(
        select(Template).options(selectinload(Template.versions)).where(Template.id == template_id)
    )
    return result.scalar_one_or_none()


async def list_templates(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    category_id: uuid.UUID | None = None,
    keyword: str | None = None,
    status: str | None = None,
) -> tuple[list[Template], int]:
    """模板列表（分页 + 筛选）"""
    query = select(Template).options(selectinload(Template.versions))

    # 筛选条件
    if category_id:
        query = query.where(Template.category_id == category_id)
    if keyword:
        query = query.where(Template.name.ilike(f"%{keyword}%"))
    if status:
        query = query.where(Template.status == status)

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # 分页
    query = query.order_by(Template.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)

    return result.scalars().all(), total


async def update_template(
    db: AsyncSession, template_id: uuid.UUID, data: TemplateUpdate
) -> Template | None:
    """更新模板信息"""
    template = await get_template(db, template_id)
    if not template:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(template, key, value)

    await db.flush()
    await db.refresh(template, ["versions"])
    return template


async def delete_template(db: AsyncSession, template_id: uuid.UUID) -> bool:
    """删除模板（级联删除版本和文件，解除项目关联）"""
    template = await get_template(db, template_id)
    if not template:
        return False

    # 删除关联文件
    for version in template.versions:
        if version.file_path and os.path.exists(version.file_path):
            os.remove(version.file_path)

    # 解除项目关联（多对多）
    from app.models.project import project_templates
    from sqlalchemy import delete as sql_delete, update as sql_update
    await db.execute(
        sql_delete(project_templates).where(project_templates.c.template_id == template_id)
    )

    # 将引用此模板的合同的 template_id 设为 NULL（允许合同保留）
    from app.models.contract import Contract
    await db.execute(
        sql_update(Contract.__table__)
        .where(Contract.__table__.c.template_id == template_id)
        .values(template_id=None, template_version_id=None)
    )

    await db.delete(template)
    await db.flush()
    return True


async def create_version(
    db: AsyncSession,
    template_id: uuid.UUID,
    file_path: str,
    change_log: str | None = None,
    user_id: uuid.UUID | None = None,
) -> tuple[TemplateVersion, list[VariableInfo]] | None:
    """为已有模板上传新版本"""
    template = await get_template(db, template_id)
    if not template:
        return None

    # 计算新版本号：找到当前最大版本号 +1
    max_v = 0
    for v in template.versions:
        try:
            num = int(v.version_number.lstrip("vV"))
            if num > max_v:
                max_v = num
        except ValueError:
            pass
    new_version_number = f"v{max_v + 1}"

    # 将旧 master 取消
    for v in template.versions:
        if v.is_master:
            v.is_master = False

    # 解析变量
    variables = extract_variables_from_docx(file_path)
    var_dicts = [
        {
            "name": v.name,
            "display_name": v.display_name,
            "var_type": v.var_type,
            "default_value": v.default_value,
            "validation_rule": v.validation_rule,
            "occurrences": v.occurrences,
        }
        for v in variables
    ]

    # 创建新版本，标记为 master
    version = TemplateVersion(
        template_id=template_id,
        version_number=new_version_number,
        file_path=file_path,
        variables=var_dicts,
        is_master=True,
        change_log=change_log or f"更新至{new_version_number}",
        created_by=user_id,
    )
    db.add(version)
    await db.flush()
    await db.refresh(template, ["versions"])

    return version, variables


async def get_template_variables(
    db: AsyncSession, template_id: uuid.UUID
) -> list[VariableInfo] | None:
    """获取模板的变量列表（从 master 版本获取）"""
    result = await db.execute(
        select(TemplateVersion).where(
            TemplateVersion.template_id == template_id,
            TemplateVersion.is_master == True,
        )
    )
    version = result.scalar_one_or_none()
    if not version:
        return None

    return [
        VariableInfo(
            name=v["name"],
            display_name=v.get("display_name", ""),
            var_type=v.get("var_type", "text"),
            default_value=v.get("default_value", ""),
            validation_rule=v.get("validation_rule", ""),
            occurrences=v.get("occurrences", 1),
        )
        for v in version.variables
    ]


async def save_upload_file(file_content: bytes, filename: str, upload_dir: str) -> str:
    """保存上传的文件到本地，返回文件路径"""
    os.makedirs(upload_dir, exist_ok=True)

    # 用 UUID 避免文件名冲突
    ext = os.path.splitext(filename)[1]
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(upload_dir, unique_name)

    with open(file_path, "wb") as f:
        f.write(file_content)

    return file_path
