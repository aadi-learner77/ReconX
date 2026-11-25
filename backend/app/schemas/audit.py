from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class AuditEventResponse(BaseModel):
    id: UUID
    organization_id: UUID
    actor_type: str
    actor_id: str
    action: str
    entity_type: str
    entity_id: str
    before_json: dict[str, Any] | None
    after_json: dict[str, Any] | None
    timestamp: datetime
    correlation_id: str
