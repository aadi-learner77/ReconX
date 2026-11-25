from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class OrgScopedRepository(Generic[ModelT]):
    """Base repository that enforces organization_id scoping on every query (NFR-SEC-03)."""

    def __init__(self, db: Session, model: type[ModelT], organization_id: UUID) -> None:
        self.db = db
        self.model = model
        self.organization_id = organization_id

    def base_query(self) -> Select[ModelT]:
        return select(self.model).where(self.model.organization_id == self.organization_id)  # type: ignore[attr-defined]

    def get_by_id(self, entity_id: UUID) -> ModelT | None:
        stmt = self.base_query().where(self.model.id == entity_id)  # type: ignore[attr-defined]
        return self.db.scalar(stmt)

    def list_all(self, offset: int = 0, limit: int = 50) -> list[ModelT]:
        stmt = self.base_query().offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())
