import csv
import io
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import AppError
from app.core.permissions import CurrentUserContext, require_permission
from app.models.audit import AuditEvent
from app.models.domain import (
    Document,
    ExceptionCase,
    Investigation,
    Invoice,
    Job,
    PurchaseOrder,
    ReconciliationRun,
    Vendor,
    VendorBankChange,
)
from app.models.policy import LLMTelemetry
from app.repositories.base import OrgScopedRepository
from app.services.agents.copilot import answer_copilot_query
from app.services.agents.investigator import run_case_investigation
from app.services.audit.service import record_audit_event
from app.services.graph.builder import (
    build_transaction_evidence_graph,
    build_transaction_obligation_graph,
    rebuild_transaction_evidence_graph,
)
from app.services.neo4j import get_graph_health, get_sync_status, neo4j_manager
from app.services.neo4j.backfill import backfill_organization_graph
from app.services.neo4j.outbox_worker import retry_failed_outbox_events
from app.services.neo4j.queries.agent_queries import (
    query_agent_execution_graph,
    query_agent_investigations,
    query_cross_investigation_analytics,
)
from app.services.neo4j.queries.obligation_queries import (
    query_obligation_graph,
    query_relationship_path,
    query_vendor_network,
    search_obligation_graph,
)
from app.services.neo4j.queries.vendor_queries import query_graph_risk_discovery
from app.services.neo4j.sync_service import sync_transaction_to_neo4j
from app.services.llm.adapter import record_llm_telemetry, test_gemini_connection
from app.services.risk.engine import compute_vendor_profile, evaluate_transaction_risk

router = APIRouter(tags=["intelligence"])


class BankChangeRequest(BaseModel):
    new_bank_account_masked: str = Field(min_length=4, max_length=64)


class CopilotQueryRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)


def _ensure_org_transaction(db: Session, organization_id: UUID, transaction_id: UUID) -> None:
    po = OrgScopedRepository(db, PurchaseOrder, organization_id).get_by_id(transaction_id)
    inv = (
        None
        if po is not None
        else OrgScopedRepository(db, Invoice, organization_id).get_by_id(transaction_id)
    )
    if po is None and inv is None:
        raise AppError(
            "TRANSACTION_NOT_FOUND", "Transaction not found.", status.HTTP_404_NOT_FOUND
        )


@router.get("/transactions/{transaction_id}/risk")
def get_transaction_risk(
    transaction_id: UUID,
    current_user: CurrentUserContext = Depends(require_permission("transactions:read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    _ensure_org_transaction(db, current_user.organization_id, transaction_id)
    signals = evaluate_transaction_risk(
        db,
        organization_id=current_user.organization_id,
        transaction_id=transaction_id,
        persist=True,
    )
    return {
        "transaction_id": str(transaction_id),
        "disclaimer": "Risk indicators are signals for human review, not proof of fraud.",
        "signals": signals,
    }


@router.get("/vendors/{vendor_id}/profile")
def get_vendor_profile(
    vendor_id: UUID,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    current_user: CurrentUserContext = Depends(require_permission("vendors:read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    profile = compute_vendor_profile(
        db,
        organization_id=current_user.organization_id,
        vendor_id=vendor_id,
        date_from=date_from,
        date_to=date_to,
    )
    if not profile:
        raise AppError("VENDOR_NOT_FOUND", "Vendor not found.", status.HTTP_404_NOT_FOUND)
    return profile


@router.post("/vendors/{vendor_id}/bank-change", status_code=status.HTTP_201_CREATED)
def record_vendor_bank_change(
    vendor_id: UUID,
    payload: BankChangeRequest,
    current_user: CurrentUserContext = Depends(require_permission("vendors:write")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    vendor = OrgScopedRepository(db, Vendor, current_user.organization_id).get_by_id(vendor_id)
    if not vendor:
        raise AppError("VENDOR_NOT_FOUND", "Vendor not found.", status.HTTP_404_NOT_FOUND)

    evt = VendorBankChange(
        organization_id=current_user.organization_id,
        vendor_id=vendor.id,
        previous_masked=vendor.bank_account_masked,
        new_masked=payload.new_bank_account_masked,
        requested_by=str(current_user.id),
        verification_status="ENHANCED_VERIFICATION_REQUIRED",
    )
    db.add(evt)
    db.flush()

    record_audit_event(
        db,
        organization_id=current_user.organization_id,
        actor_type="USER",
        actor_id=str(current_user.id),
        action="VENDOR_BANK_CHANGE_REQUESTED",
        entity_type="vendor_bank_change",
        entity_id=str(evt.id),
        before={"bank_account_masked": vendor.bank_account_masked},
        after={
            "new_masked": payload.new_bank_account_masked,
            "verification_status": evt.verification_status,
        },
    )
    db.commit()
    return {
        "id": str(evt.id),
        "vendor_id": str(vendor.id),
        "verification_status": evt.verification_status,
        "message": (
            "Enhanced human verification required; never accepted solely on AI recommendation."
        ),
    }


@router.post("/exceptions/{case_id}/investigations", status_code=status.HTTP_201_CREATED)
def start_investigation(
    case_id: UUID,
    current_user: CurrentUserContext = Depends(require_permission("investigations:run")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return run_case_investigation(db, case_id=case_id, current_user=current_user)


@router.get("/investigations/{investigation_id}")
def get_investigation(
    investigation_id: UUID,
    current_user: CurrentUserContext = Depends(require_permission("exceptions:read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    inv = OrgScopedRepository(db, Investigation, current_user.organization_id).get_by_id(
        investigation_id
    )
    if not inv:
        raise AppError(
            "INVESTIGATION_NOT_FOUND", "Investigation not found.", status.HTTP_404_NOT_FOUND
        )
    return {
        "investigation_id": str(inv.id),
        "case_id": str(inv.case_id),
        "status": inv.status,
        "agent_version": inv.agent_version,
        "model_provider": inv.model_provider,
        "model_name": inv.model_name,
        "prompt_version": inv.prompt_version,
        "confidence": float(inv.confidence),
        "created_at": inv.created_at.isoformat(),
        **inv.structured_output_json,
    }


@router.get("/dashboard/summary")
def get_dashboard_summary(
    current_user: CurrentUserContext = Depends(require_permission("transactions:read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    org_id = current_user.organization_id
    docs_count = (
        db.scalar(
            select(func.count()).select_from(
                OrgScopedRepository(db, Document, org_id).base_query().subquery()
            )
        )
        or 0
    )
    po_rows = list(db.scalars(OrgScopedRepository(db, PurchaseOrder, org_id).base_query()).all())
    runs = list(
        db.scalars(
            OrgScopedRepository(db, ReconciliationRun, org_id)
            .base_query()
            .order_by(desc(ReconciliationRun.completed_at))
        ).all()
    )
    latest_by_tx: dict[UUID, str] = {}
    for r in runs:
        if r.transaction_id not in latest_by_tx:
            latest_by_tx[r.transaction_id] = r.outcome

    outcome_counts: dict[str, int] = {
        "MATCHED": 0,
        "MATCHED_WITH_TOLERANCE": 0,
        "EXCEPTION": 0,
        "INCOMPLETE": 0,
        "REVIEW_REQUIRED": 0,
    }
    for oc in latest_by_tx.values():
        outcome_counts[oc] = outcome_counts.get(oc, 0) + 1

    open_excs = list(
        db.scalars(
            OrgScopedRepository(db, ExceptionCase, org_id)
            .base_query()
            .where(ExceptionCase.status.notin_(["APPROVED", "REJECTED"]))
            .order_by(desc(ExceptionCase.created_at))
            .limit(10)
        ).all()
    )
    jobs = list(db.scalars(OrgScopedRepository(db, Job, org_id).base_query()).all())
    job_counts = {
        "QUEUED": sum(1 for j in jobs if j.status == "QUEUED"),
        "PROCESSING": sum(1 for j in jobs if j.status == "PROCESSING"),
        "SUCCEEDED": sum(1 for j in jobs if j.status == "SUCCEEDED"),
        "FAILED": sum(1 for j in jobs if j.status == "FAILED"),
    }
    recent_audit = list(
        db.scalars(
            OrgScopedRepository(db, AuditEvent, org_id)
            .base_query()
            .order_by(desc(AuditEvent.timestamp))
            .limit(10)
        ).all()
    )

    tel_rows = list(
        db.scalars(
            OrgScopedRepository(db, LLMTelemetry, org_id)
            .base_query()
            .order_by(desc(LLMTelemetry.created_at))
            .limit(50)
        ).all()
    )
    last_ok = next((t for t in tel_rows if t.success and not t.fallback_used), None)
    settings = get_settings()

    return {
        "kpis": {
            "documents": docs_count,
            "transactions": len(po_rows),
            "matched_cases": outcome_counts["MATCHED"] + outcome_counts["MATCHED_WITH_TOLERANCE"],
            "open_exceptions": len(open_excs),
            "pending_approvals": sum(
                1 for e in open_excs if e.status in {"OPEN", "IN_REVIEW", "ESCALATED"}
            ),
            "processing_jobs": job_counts["QUEUED"] + job_counts["PROCESSING"],
        },
        "ai_status": {
            "configured_provider": settings.llm_provider,
            "gemini_model": settings.gemini_model,
            "api_key_configured": bool(settings.gemini_api_key.strip()),
            "last_successful_provider": last_ok.actual_provider if last_ok else None,
            "successful_calls": sum(1 for t in tel_rows if t.success and not t.fallback_used),
            "fallback_count": sum(1 for t in tel_rows if t.fallback_used),
        },
        "outcome_breakdown": [{"outcome": k, "count": v} for k, v in outcome_counts.items()],
        "job_status": job_counts,
        "exception_queue": [
            {
                "id": str(e.id),
                "transaction_id": str(e.transaction_id),
                "type": e.type,
                "severity": e.severity,
                "status": e.status,
                "summary": e.summary,
            }
            for e in open_excs
        ],
        "recent_activity": [
            {
                "id": str(a.id),
                "action": a.action,
                "entity_type": a.entity_type,
                "actor_type": a.actor_type,
                "timestamp": a.timestamp.isoformat(),
            }
            for a in recent_audit
        ],
    }


@router.get("/graph/health")
def graph_health_endpoint(
    current_user: CurrentUserContext = Depends(require_permission("transactions:read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return get_graph_health(db, current_user.organization_id)


@router.get("/graph/sync/status")
def graph_sync_status_endpoint(
    current_user: CurrentUserContext = Depends(require_permission("transactions:read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return get_sync_status(db, current_user.organization_id)


@router.post("/graph/sync/backfill")
def graph_sync_backfill_endpoint(
    current_user: CurrentUserContext = Depends(require_permission("admin:config:write")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    res = backfill_organization_graph(db, organization_id=current_user.organization_id)
    record_audit_event(
        db,
        organization_id=current_user.organization_id,
        actor_type="USER",
        actor_id=str(current_user.id),
        action="GRAPH_BACKFILL_EXECUTED",
        entity_type="graph",
        entity_id=str(current_user.organization_id),
        after={"ok": res.get("ok"), "nodes_synchronized": res.get("nodes_synchronized", 0)},
    )
    db.commit()
    return res


@router.post("/graph/sync/rebuild/{transaction_id}")
def graph_sync_rebuild_tx_endpoint(
    transaction_id: UUID,
    current_user: CurrentUserContext = Depends(require_permission("admin:config:write")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    _ensure_org_transaction(db, current_user.organization_id, transaction_id)
    ok = sync_transaction_to_neo4j(
        db, organization_id=current_user.organization_id, transaction_id=transaction_id
    )
    return {"ok": ok, "transaction_id": str(transaction_id)}


@router.post("/graph/sync/retry-failed")
def graph_sync_retry_failed_endpoint(
    current_user: CurrentUserContext = Depends(require_permission("admin:config:write")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return retry_failed_outbox_events(db, organization_id=current_user.organization_id)


@router.get("/graph/obligations/vendor/{vendor_id}")
def get_vendor_obligation_network(
    vendor_id: UUID,
    current_user: CurrentUserContext = Depends(require_permission("vendors:read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return query_vendor_network(
        db, organization_id=current_user.organization_id, vendor_id=vendor_id
    )


@router.get("/graph/obligations/path")
def get_obligation_relationship_path(
    source_graph_key: str = Query(..., min_length=3, max_length=256),
    target_graph_key: str = Query(..., min_length=3, max_length=256),
    current_user: CurrentUserContext = Depends(require_permission("transactions:read")),
) -> dict[str, Any]:
    return query_relationship_path(
        organization_id=current_user.organization_id,
        source_graph_key=source_graph_key,
        target_graph_key=target_graph_key,
    )


@router.get("/graph/obligations/search")
def search_obligation_nodes(
    q: str = Query(..., min_length=1, max_length=100),
    current_user: CurrentUserContext = Depends(require_permission("transactions:read")),
) -> dict[str, Any]:
    return {
        "items": search_obligation_graph(
            organization_id=current_user.organization_id, q=q
        )
    }


@router.get("/graph/risk-discovery")
def get_graph_risk_discovery(
    current_user: CurrentUserContext = Depends(require_permission("transactions:read")),
) -> dict[str, Any]:
    return query_graph_risk_discovery(organization_id=current_user.organization_id)


@router.get("/graph/agents/investigations")
def get_agent_graph_investigations(
    current_user: CurrentUserContext = Depends(require_permission("exceptions:read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return query_agent_investigations(db, organization_id=current_user.organization_id)


@router.get("/graph/agents/investigations/{investigation_id}")
def get_agent_graph_execution(
    investigation_id: UUID,
    current_user: CurrentUserContext = Depends(require_permission("exceptions:read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return query_agent_execution_graph(
        db, organization_id=current_user.organization_id, investigation_id=investigation_id
    )


@router.get("/graph/agents/analytics")
def get_agent_graph_analytics(
    current_user: CurrentUserContext = Depends(require_permission("exceptions:read")),
) -> dict[str, Any]:
    return query_cross_investigation_analytics(organization_id=current_user.organization_id)


@router.get("/graph/transactions/{transaction_id}")
def get_transaction_graph(
    transaction_id: UUID,
    include_history: bool = Query(default=True),
    current_user: CurrentUserContext = Depends(require_permission("transactions:read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if not get_settings().feature_evidence_graph:
        raise AppError(
            "FEATURE_DISABLED",
            "Financial Evidence Graph feature flag is disabled.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    _ensure_org_transaction(db, current_user.organization_id, transaction_id)
    if neo4j_manager.is_enabled() and neo4j_manager.verify_connectivity()[0]:
        return query_obligation_graph(
            db,
            organization_id=current_user.organization_id,
            transaction_id=transaction_id,
            view="overview",
        )
    return build_transaction_evidence_graph(
        db,
        organization_id=current_user.organization_id,
        transaction_id=transaction_id,
        include_history=include_history,
    )


@router.post("/graph/transactions/{transaction_id}/rebuild")
def rebuild_transaction_graph(
    transaction_id: UUID,
    current_user: CurrentUserContext = Depends(require_permission("transactions:read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if not get_settings().feature_evidence_graph:
        raise AppError(
            "FEATURE_DISABLED",
            "Financial Evidence Graph feature flag is disabled.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    _ensure_org_transaction(db, current_user.organization_id, transaction_id)
    if neo4j_manager.is_enabled() and neo4j_manager.verify_connectivity()[0]:
        sync_transaction_to_neo4j(
            db, organization_id=current_user.organization_id, transaction_id=transaction_id
        )
        graph = query_obligation_graph(
            db,
            organization_id=current_user.organization_id,
            transaction_id=transaction_id,
            view="overview",
        )
        record_audit_event(
            db,
            organization_id=current_user.organization_id,
            actor_type="USER",
            actor_id=str(current_user.id),
            action="GRAPH_REBUILT",
            entity_type="evidence_graph",
            entity_id=str(transaction_id),
            after={
                "node_count": len(graph.get("nodes", [])),
                "edge_count": len(graph.get("edges", [])),
                "source": "neo4j",
            },
        )
        db.commit()
        return graph
    return rebuild_transaction_evidence_graph(
        db,
        organization_id=current_user.organization_id,
        transaction_id=transaction_id,
        actor_id=str(current_user.id),
    )


@router.get("/graph/obligations/{transaction_id}")
def get_transaction_obligation_graph(
    transaction_id: UUID,
    view: str = Query(default="overview", pattern="^(overview|evidence|vendor|fulfilment)$"),
    current_user: CurrentUserContext = Depends(require_permission("transactions:read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if not get_settings().feature_evidence_graph:
        raise AppError(
            "FEATURE_DISABLED",
            "Financial Evidence Graph feature flag is disabled.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    _ensure_org_transaction(db, current_user.organization_id, transaction_id)
    return query_obligation_graph(
        db,
        organization_id=current_user.organization_id,
        transaction_id=transaction_id,
        view=view,
    )


@router.get("/intelligence/agent-harness")
def get_agent_harness_overview(
    current_user: CurrentUserContext = Depends(require_permission("exceptions:read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    settings = get_settings()
    org_id = current_user.organization_id
    invs = list(
        db.scalars(
            OrgScopedRepository(db, Investigation, org_id)
            .base_query()
            .order_by(desc(Investigation.created_at))
            .limit(20)
        ).all()
    )
    case_ids = [i.case_id for i in invs]
    cases = (
        {
            c.id: c
            for c in db.scalars(
                OrgScopedRepository(db, ExceptionCase, org_id)
                .base_query()
                .where(ExceptionCase.id.in_(case_ids))
            ).all()
        }
        if case_ids
        else {}
    )

    active_model = {
        "gemini": settings.gemini_model,
        "groq": settings.groq_model,
        "ollama": settings.ollama_model,
    }.get(settings.llm_provider, "mock-deterministic-v1")

    configured_agents = [
        {
            "id": "DocumentAgent",
            "order": 1,
            "name": "Document Agent",
            "category": "ingestion",
            "purpose": (
                "Classify and process financial documents and expose structured information."
            ),
            "input_context": "transaction_id, linked Document rows",
            "processing": (
                "Retrieves transaction bundle and inspects NEEDS_REVIEW document statuses."
            ),
            "tools": ["get_transaction_bundle", "search_related_documents"],
            "output": "bundle + linked_documents count + needs_review_files",
            "execution_mode": "Deterministic DB retrieval + PyMuPDF/RapidOCR metadata",
            "failure_recovery": "Records FAILED step in execution_trace and aborts safely.",
        },
        {
            "id": "MatchingAgent",
            "order": 2,
            "name": "Matching Agent",
            "category": "reconciliation",
            "purpose": (
                "Invoke the deterministic three-way reconciliation engine and inspect results."
            ),
            "input_context": "PO, GoodsReceipts, and Invoices from transaction bundle",
            "processing": (
                "Verifies 3-way completeness and identifies missing PO/GRN/Invoice records."
            ),
            "tools": ["run_reconciliation", "get_transaction_bundle"],
            "output": "has_po, grn_count, invoice_count, missing_information",
            "execution_mode": "Deterministic decimal.Decimal rule engine (zero floats)",
            "failure_recovery": (
                "Missing documents recorded explicitly as unknown/missing_information."
            ),
        },
        {
            "id": "RiskAgent",
            "order": 3,
            "name": "Risk Agent",
            "category": "risk",
            "purpose": "Evaluate anomaly indicators and identify transactions requiring scrutiny.",
            "input_context": "transaction_id + organization invoice/vendor corpus",
            "processing": (
                "Runs duplicate, split-invoice, MAD price-spike, shared-bank, "
                "and IsolationForest checks."
            ),
            "tools": ["evaluate_risks"],
            "output": "Persisted RiskSignal list with reason codes and non-fraud disclaimer",
            "execution_mode": "Deterministic rules + scikit-learn IsolationForest (when N>=15)",
            "failure_recovery": "Falls back to transparent rules with limited_confidence if N<15.",
        },
        {
            "id": "VendorIntelligenceAgent",
            "order": 4,
            "name": "Vendor Intelligence Agent",
            "category": "vendor",
            "purpose": "Retrieve historical vendor behaviour and contextual supplier metrics.",
            "input_context": "vendor_id from transaction bundle",
            "processing": "Computes mismatch_rate, avg_delivery_days, on_time_rate, small-N guard.",
            "tools": ["get_vendor_history"],
            "output": "Vendor profile summary and dispute history",
            "execution_mode": "Deterministic DB aggregation (small-sample guard for N<5)",
            "failure_recovery": "Omits reliability score when sample size N<5.",
        },
        {
            "id": "EvidenceGraphAgent",
            "order": 5,
            "name": "Evidence Graph Agent",
            "category": "graph",
            "purpose": "Retrieve related suppliers, POs, GRNs, invoices, and historical links.",
            "input_context": "transaction_id + include_history=True",
            "processing": (
                "Traverses relational PostgreSQL/SQLite graph including prior vendor POs."
            ),
            "tools": ["build_transaction_evidence_graph"],
            "output": "graph_context (nodes, edges, historical POs)",
            "execution_mode": "Relational graph traversal (PostgreSQL/SQLite)",
            "failure_recovery": "Core reconciliation remains unaffected if graph flag is disabled.",
        },
        {
            "id": "InvestigationAgent",
            "order": 6,
            "name": "Investigation Agent",
            "category": "llm",
            "purpose": (
                "Combine validated findings, identify hypotheses, and recommend resolutions."
            ),
            "input_context": "Verified facts, fenced untrusted text, vendor & graph context",
            "processing": (
                "Calls LLMProvider.explain() and validates every evidence_ref against DB."
            ),
            "tools": ["LLMProvider.explain", "validate_evidence_refs"],
            "output": "InvestigationOutputSchema (human_approval_required=True)",
            "execution_mode": "LLM-assisted explanation + strict Pydantic & DB post-validation",
            "failure_recovery": (
                "Falls back to deterministic template if LLM fails; 422 on bad refs."
            ),
        },
        {
            "id": "AuditAgent",
            "order": 7,
            "name": "Audit Agent",
            "category": "audit",
            "purpose": "Record execution details and maintain traceability.",
            "input_context": "tool_trace, execution_trace, validated InvestigationOutputSchema",
            "processing": "Persists DRAFT_READY Investigation and immutable audit_event entries.",
            "tools": ["create_investigation_draft", "record_audit_event"],
            "output": "Persisted investigation_id + complete execution_trace",
            "execution_mode": "Deterministic persistence + DB immutability triggers",
            "failure_recovery": "Append-only audit trail prevents silent deletion or tampering.",
        },
    ]

    harness_components = [
        {"name": "Orchestrator", "role": "Coordinates 7-stage DAG order in FinanceOrchestrator."},
        {
            "name": "Shared Context Manager",
            "role": "Passes typed OrchestrationContext across stages.",
        },
        {"name": "Tool Registry", "role": "Enforces ALLOWLISTED_AGENT_TOOLS (no SQL/pay/approve)."},
        {"name": "Permission & Policy Layer", "role": "Enforces JWT RBAC and org-scoping."},
        {
            "name": "LLM Provider Adapter",
            "role": "Routes mock / gemini / groq / ollama with fallback.",
        },
        {"name": "Evidence Validator", "role": "Rejects unresolvable UUIDs or unknown rule_ids."},
        {
            "name": "Execution Tracer",
            "role": "Captures per-stage status, duration_ms, and summary.",
        },
        {
            "name": "Human Approval Gate",
            "role": "Requires authorized human decision with rationale.",
        },
    ]

    recent_traces = []
    for i in invs:
        out = i.structured_output_json or {}
        c = cases.get(i.case_id)
        recent_traces.append(
            {
                "investigation_id": str(i.id),
                "case_id": str(i.case_id),
                "case_type": c.type if c else "UNKNOWN",
                "case_severity": c.severity if c else "MEDIUM",
                "transaction_id": str(c.transaction_id) if c else None,
                "status": i.status,
                "model_provider": i.model_provider,
                "model_name": i.model_name,
                "confidence": float(i.confidence),
                "created_at": i.created_at.isoformat(),
                "summary": out.get("summary", ""),
                "human_approval_required": out.get("human_approval_required", True),
                "configured_provider": out.get("configured_provider", i.model_provider),
                "actual_provider": out.get("actual_provider", i.model_provider),
                "llm_succeeded": out.get("llm_succeeded", i.model_provider != "mock"),
                "fallback_used": out.get("fallback_used", False),
                "operation_type": out.get("operation_type", "explain"),
                "latency_ms": out.get("latency_ms", 0.0),
                "evidence_refs": out.get("evidence_refs", []),
                "execution_trace": out.get("execution_trace", []),
                "tool_trace": out.get("tool_trace", []),
            }
        )

    tel_rows = list(
        db.scalars(
            OrgScopedRepository(db, LLMTelemetry, org_id)
            .base_query()
            .order_by(desc(LLMTelemetry.created_at))
            .limit(100)
        ).all()
    )
    gemini_rows = [t for t in tel_rows if t.configured_provider == "gemini"]
    last_gemini_ok = next((t for t in gemini_rows if t.success and not t.fallback_used), None)
    last_any_ok = next((t for t in tel_rows if t.success and not t.fallback_used), None)
    avg_lat = (
        round(sum(t.latency_ms for t in gemini_rows) / len(gemini_rows), 2)
        if gemini_rows
        else 0.0
    )

    return {
        "system_status": {
            "configured_agents": len(configured_agents),
            "active_provider": settings.llm_provider,
            "active_model": active_model,
            "graph_available": settings.feature_evidence_graph,
            "graph_sync": get_sync_status(db, org_id),
            "total_investigations": len(recent_traces),
            "successful_investigations": sum(
                1 for t in recent_traces if t["status"] in ("DRAFT_READY", "COMPLETED")
            ),
        },
        "gemini_telemetry": {
            "configured_provider": settings.llm_provider,
            "gemini_model": settings.gemini_model,
            "api_key_configured": bool(settings.gemini_api_key.strip()),
            "last_successful_provider": last_any_ok.actual_provider if last_any_ok else None,
            "last_successful_at": (
                last_gemini_ok.created_at.isoformat() if last_gemini_ok else None
            ),
            "invocation_count": len(gemini_rows),
            "successful_calls": sum(
                1 for t in gemini_rows if t.success and not t.fallback_used
            ),
            "failed_calls": sum(1 for t in gemini_rows if not t.success),
            "fallback_count": sum(1 for t in gemini_rows if t.fallback_used),
            "avg_latency_ms": avg_lat,
            "token_usage_available": False,
        },
        "configured_agents": configured_agents,
        "harness_components": harness_components,
        "recent_traces": recent_traces,
    }


@router.post("/intelligence/gemini/test")
def test_gemini_endpoint(
    current_user: CurrentUserContext = Depends(require_permission("admin:config:write")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    res = test_gemini_connection()
    tel = res.pop("telemetry", None)
    if tel is not None:
        record_llm_telemetry(db, organization_id=current_user.organization_id, telemetry=tel)
        db.commit()
    return res


@router.post("/copilot/query")
def copilot_query(
    payload: CopilotQueryRequest,
    current_user: CurrentUserContext = Depends(require_permission("copilot:read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if not get_settings().feature_finance_copilot:
        raise AppError(
            "FEATURE_DISABLED",
            "Finance copilot feature flag is disabled.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return answer_copilot_query(db, question=payload.question, current_user=current_user)


@router.get("/analytics/cash-obligations")
def get_cash_obligations(
    current_user: CurrentUserContext = Depends(require_permission("transactions:read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if not get_settings().feature_cash_view:
        raise AppError(
            "FEATURE_DISABLED",
            "Cash obligations feature flag is disabled.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    org_id = current_user.organization_id
    today = date.today()
    invs = list(
        db.scalars(
            OrgScopedRepository(db, Invoice, org_id)
            .base_query()
            .where(Invoice.status != "REJECTED")
        ).all()
    )
    vendors = {
        v.id: v.legal_name
        for v in db.scalars(OrgScopedRepository(db, Vendor, org_id).base_query()).all()
    }

    buckets: dict[str, Decimal] = {
        "OVERDUE": Decimal("0"),
        "DUE_0_30": Decimal("0"),
        "DUE_31_60": Decimal("0"),
        "DUE_60_PLUS": Decimal("0"),
    }
    by_vendor: dict[str, Decimal] = {}
    for inv in invs:
        days = (inv.due_date - today).days
        if days < 0:
            buckets["OVERDUE"] += inv.total_amount
        elif days <= 30:
            buckets["DUE_0_30"] += inv.total_amount
        elif days <= 60:
            buckets["DUE_31_60"] += inv.total_amount
        else:
            buckets["DUE_60_PLUS"] += inv.total_amount
        vname = vendors.get(inv.vendor_id, "Unknown")
        by_vendor[vname] = by_vendor.get(vname, Decimal("0")) + inv.total_amount

    # Predictive 30/60/90-day cash-flow forecast combining scheduled open obligations
    # and historical 30-day average invoice run-rate (deterministic Decimal math).
    historical_total = sum((inv.total_amount for inv in invs), Decimal("0"))
    inv_dates = [inv.invoice_date for inv in invs]
    span_raw = (max(inv_dates, default=today) - min(inv_dates, default=today)).days
    date_span_days = max(30, span_raw or 30)
    daily_run_rate = historical_total / Decimal(str(date_span_days))
    b_overdue_30 = buckets["OVERDUE"] + buckets["DUE_0_30"]
    b_overdue_60 = b_overdue_30 + buckets["DUE_31_60"]
    b_overdue_90 = b_overdue_60 + buckets["DUE_60_PLUS"]
    forecast_30_60_90 = [
        {
            "horizon_days": 30,
            "scheduled_amount": str(b_overdue_30.quantize(Decimal("0.01"))),
            "projected_total": str(
                (b_overdue_30 + daily_run_rate * Decimal("15")).quantize(Decimal("0.01"))
            ),
        },
        {
            "horizon_days": 60,
            "scheduled_amount": str(b_overdue_60.quantize(Decimal("0.01"))),
            "projected_total": str(
                (b_overdue_60 + daily_run_rate * Decimal("30")).quantize(Decimal("0.01"))
            ),
        },
        {
            "horizon_days": 90,
            "scheduled_amount": str(b_overdue_90.quantize(Decimal("0.01"))),
            "projected_total": str(
                (b_overdue_90 + daily_run_rate * Decimal("45")).quantize(Decimal("0.01"))
            ),
        },
    ]

    return {
        "buckets": [{"bucket": k, "amount": str(v)} for k, v in buckets.items()],
        "by_vendor": [
            {"vendor": k, "amount": str(v)}
            for k, v in sorted(by_vendor.items(), key=lambda kv: kv[1], reverse=True)
        ],
        "forecast_30_60_90": forecast_30_60_90,
        "forecast_methodology": (
            f"Scheduled due-date obligations + historical daily run-rate "
            f"({daily_run_rate.quantize(Decimal('0.01'))}/day over {len(invs)} invoice(s))."
        ),
        "note": (
            "Aggregation of non-rejected invoices by due date "
            "with deterministic run-rate projection."
        ),
    }


@router.get("/reports/export")
def export_report(
    format: str = Query(default="csv", pattern="^(csv|pdf)$"),
    current_user: CurrentUserContext = Depends(require_permission("reports:export")),
    db: Session = Depends(get_db),
) -> Response:
    if not get_settings().feature_report_exports:
        raise AppError(
            "FEATURE_DISABLED",
            "Report exports feature flag is disabled.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    org_id = current_user.organization_id
    pos = list(
        db.scalars(
            OrgScopedRepository(db, PurchaseOrder, org_id)
            .base_query()
            .order_by(desc(PurchaseOrder.issue_date))
        ).all()
    )
    if format == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            ["PO Number", "Issue Date", "Currency", "Total Amount", "Status", "Scenario"]
        )
        for p in pos:
            writer.writerow(
                [
                    p.po_number,
                    str(p.issue_date),
                    p.currency,
                    str(p.total_amount),
                    p.status,
                    p.scenario_label or "",
                ]
            )
        return Response(
            content=buf.getvalue().encode("utf-8"),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="reconx_report.csv"'},
        )

    pdf_buf = io.BytesIO()
    c = canvas.Canvas(pdf_buf, pagesize=A4)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, 800, "ReconX AI — Reconciliation Report")
    c.setFont("Helvetica", 10)
    y = 770
    for p in pos[:35]:
        line_txt = f"{p.po_number} | {p.issue_date} | {p.currency} {p.total_amount} | {p.status}"
        c.drawString(40, y, line_txt)
        y -= 18
        if y < 50:
            break
    c.save()
    return Response(
        content=pdf_buf.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="reconx_report.pdf"'},
    )
