from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import CurrentUserContext, require_permission
from app.services.reconciliation_adapter import execute_reconciliation

router = APIRouter(tags=["reconciliation"])


@router.post("/transactions/{transaction_id}/reconcile")
def reconcile_transaction_endpoint(
    transaction_id: UUID,
    current_user: CurrentUserContext = Depends(require_permission("reconciliation:run")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return execute_reconciliation(
        db,
        organization_id=current_user.organization_id,
        transaction_id=transaction_id,
        actor_type="USER",
        actor_id=str(current_user.id),
    )
