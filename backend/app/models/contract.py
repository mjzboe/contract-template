import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Contract(Base, TimestampMixin):
    """合同/签字页模型：一次生成产生一个 contract 记录"""

    __tablename__ = "contracts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("templates.id"), nullable=True
    )
    template_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("template_versions.id"), nullable=True
    )
    variables: Mapped[dict] = mapped_column(JSONB, default=dict)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_path_pdf: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status_history: Mapped[list] = mapped_column(JSONB, default=list)

    # 关系
    project: Mapped["Project | None"] = relationship("Project")
    template: Mapped["Template"] = relationship("Template")

    def __repr__(self) -> str:
        return f"<Contract {self.title}>"
