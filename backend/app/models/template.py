import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.project import project_templates  # noqa: F401


class Template(Base, TimestampMixin):
    """模板模型"""

    __tablename__ = "templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True
    )
    tags: Mapped[list] = mapped_column(JSONB, default=list)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # 关系
    category: Mapped["Category | None"] = relationship("Category")
    versions: Mapped[list["TemplateVersion"]] = relationship(
        "TemplateVersion", back_populates="template", cascade="all, delete-orphan"
    )
    projects: Mapped[list["Project"]] = relationship(
        "Project", secondary=project_templates, back_populates="templates", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Template {self.name}>"


class TemplateVersion(Base, TimestampMixin):
    """模板版本模型"""

    __tablename__ = "template_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("templates.id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[str] = mapped_column(String(20), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    variables: Mapped[list] = mapped_column(JSONB, default=list)
    is_master: Mapped[bool] = mapped_column(Boolean, default=False)
    change_log: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # 关系
    template: Mapped["Template"] = relationship("Template", back_populates="versions")

    __table_args__ = (
        UniqueConstraint("template_id", "version_number", name="uq_template_version"),
    )

    def __repr__(self) -> str:
        return f"<TemplateVersion {self.template_id}:{self.version_number}>"
