from fastapi import APIRouter

from app.api.v1 import (
    admin,
    audit,
    auth,
    documents,
    exceptions,
    health,
    intelligence,
    reconciliation,
    transactions,
    vendors,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(admin.router)
api_router.include_router(audit.router)
api_router.include_router(vendors.router)
api_router.include_router(transactions.router)
api_router.include_router(reconciliation.router)
api_router.include_router(documents.router)
api_router.include_router(exceptions.router)
api_router.include_router(intelligence.router)
