import uuid

from sqlalchemy import Column, ForeignKey, String, Table, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

# 项目-模板多对多关联表
project_templates = Table(
    "project_templates",
    Base.metadata,
    Column("project_id", UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    Column("template_id", UUID(as_uuid=True), ForeignKey("templates.id", ondelete="CASCADE"), primary_key=True),
)


class Project(Base, TimestampMixin):
    """项目模型：一个项目关联多个模板，用于跨模板变量去重和批量生成"""

    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    # 去重后的变量快照（JSON）
    deduplicated_variables: Mapped[list] = mapped_column(JSONB, default=list)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # 多对多关系
    templates: Mapped[list["Template"]] = relationship(
        "Template", secondary=project_templates, back_populates="projects", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Project {self.name}>"
