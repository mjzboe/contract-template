from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.audit import router as audit_router
from app.api.auth import router as auth_router
from app.api.contracts import router as contracts_router
from app.api.projects import router as projects_router
from app.api.templates import router as templates_router
from app.api.users import router as users_router
from app.database import get_db
from app.models.category import Category
from app.schemas.template import CategoryCreate, CategoryResponse

router = APIRouter()

router.include_router(auth_router)
router.include_router(users_router)
router.include_router(audit_router)
router.include_router(templates_router)
router.include_router(projects_router)
router.include_router(contracts_router)


# ========== 分类 API ==========
@router.post("/categories", response_model=CategoryResponse, status_code=201)
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
):
    category = Category(
        name=data.name,
        parent_id=data.parent_id,
        sort_order=data.sort_order,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).order_by(Category.sort_order))
    return list(result.scalars().all())


@router.get("/health")
async def health_check():
    return {"status": "ok"}
