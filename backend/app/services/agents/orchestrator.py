import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.permissions import CurrentUserContext
from app.models.domain import Document, ExceptionCase
from app.repositories.base import OrgScopedRepository
from app.services.agents.tools import AgentToolbox
from app.services.graph.builder import build_transaction_evidence_graph


@dataclass
class AgentStepTrace:
    agent: str
    status: str
    duration_ms: float
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "summary": self.summary,
        }


@dataclass
class OrchestrationContext:
    db: Session
    current_user: CurrentUserContext
    case: ExceptionCase
    toolbox: AgentToolbox
    bundle: dict[str, Any] = field(default_factory=dict)
    document_findings: dict[str, Any] = field(default_factory=dict)
    matching_findings: dict[str, Any] = field(default_factory=dict)
    risks: list[dict[str, Any]] = field(default_factory=list)
    vendor_history: dict[str, Any] = field(default_factory=dict)
    graph_context: dict[str, Any] = field(default_factory=dict)
    execution_trace: list[AgentStepTrace] = field(default_factory=list)


class FinanceOrchestrator:
    """Deterministic multi-agent DAG orchestrator for exception investigations (SRS 7.2)."""

    def _run_node(
        self,
        ctx: OrchestrationContext,
        agent_name: str,
        fn: Callable[[OrchestrationContext], str],
    ) -> None:
        start = time.perf_counter()
        try:
            summary = fn(ctx)
            elapsed = round((time.perf_counter() - start) * 1000, 2)
            ctx.execution_trace.append(
                AgentStepTrace(
                    agent=agent_name, status="SUCCEEDED", duration_ms=elapsed, summary=summary
                )
            )
        except Exception as exc:
            elapsed = round((time.perf_counter() - start) * 1000, 2)
            ctx.execution_trace.append(
                AgentStepTrace(
                    agent=agent_name, status="FAILED", duration_ms=elapsed, summary=str(exc)
                )
            )
            raise

    def run_document_agent(self, ctx: OrchestrationContext) -> str:
        ctx.bundle = ctx.toolbox.get_transaction_bundle(ctx.case.transaction_id)
        docs = list(
            ctx.db.scalars(
                OrgScopedRepository(ctx.db, Document, ctx.current_user.organization_id)
                .base_query()
                .where(Document.transaction_id == ctx.case.transaction_id)
            ).all()
        )
        low_conf = [d.file_name for d in docs if d.status == "NEEDS_REVIEW"]
        ctx.document_findings = {
            "linked_documents": len(docs),
            "needs_review_files": low_conf,
        }
        return f"Inspected {len(docs)} linked document(s); {len(low_conf)} need review."

    def run_matching_agent(self, ctx: OrchestrationContext) -> str:
        po = ctx.bundle.get("purchase_order")
        grns = ctx.bundle.get("goods_receipts") or []
        invs = ctx.bundle.get("invoices") or []
        missing: list[str] = []
        if not po:
            missing.append("No linked Purchase Order found for this transaction.")
        if not grns:
            missing.append("No Goods Receipt Note (GRN) recorded against this PO.")
        if not invs:
            missing.append("No Supplier Invoice linked to this PO.")
        ctx.matching_findings = {
            "has_po": bool(po),
            "grn_count": len(grns),
            "invoice_count": len(invs),
            "missing_information": missing,
        }
        return f"Evaluated 3-way match bundle (PO={bool(po)}, GRNs={len(grns)}, INVs={len(invs)})."

    def run_risk_agent(self, ctx: OrchestrationContext) -> str:
        ctx.risks = ctx.toolbox.evaluate_risks(ctx.case.transaction_id)
        return f"Evaluated {len(ctx.risks)} risk indicator signal(s)."

    def run_vendor_intelligence_agent(self, ctx: OrchestrationContext) -> str:
        vendor_id_str = (ctx.bundle.get("vendor") or {}).get("id")
        if vendor_id_str:
            ctx.vendor_history = ctx.toolbox.get_vendor_history(UUID(vendor_id_str))
            tx_n = ctx.vendor_history.get("transaction_count", 0)
            return f"Loaded vendor profile (tx_count={tx_n})."
        ctx.vendor_history = {}
        return "No vendor linked to transaction."

    def run_graph_context_agent(self, ctx: OrchestrationContext) -> str:
        ctx.graph_context = build_transaction_evidence_graph(
            ctx.db,
            organization_id=ctx.current_user.organization_id,
            transaction_id=ctx.case.transaction_id,
            include_history=True,
        )
        n_nodes = len(ctx.graph_context.get("nodes", []))
        n_edges = len(ctx.graph_context.get("edges", []))
        return f"Traversed evidence graph ({n_nodes} nodes, {n_edges} edges)."

    def run_pipeline(self, ctx: OrchestrationContext) -> OrchestrationContext:
        self._run_node(ctx, "DocumentAgent", self.run_document_agent)
        self._run_node(ctx, "MatchingAgent", self.run_matching_agent)
        self._run_node(ctx, "RiskAgent", self.run_risk_agent)
        self._run_node(ctx, "VendorIntelligenceAgent", self.run_vendor_intelligence_agent)
        self._run_node(ctx, "EvidenceGraphAgent", self.run_graph_context_agent)
        return ctx
