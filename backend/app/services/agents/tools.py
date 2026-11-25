from datetime import date
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.permissions import CurrentUserContext
from app.models.domain import Document, ExceptionCase, ExceptionComment, Investigation
from app.repositories.base import OrgScopedRepository
from app.services.audit.service import record_audit_event
from app.services.reconciliation_adapter import execute_reconciliation
from app.services.risk.engine import compute_vendor_profile, evaluate_transaction_risk
from app.services.transactions.bundle import get_transaction_bundle

# Strict allowlist per SRS 7.3 — NO SQL tool, NO payment tool, NO approval tool
ALLOWLISTED_AGENT_TOOLS = (
    "get_transaction_bundle",
    "search_related_documents",
    "get_vendor_history",
    "run_reconciliation",
    "create_investigation_draft",
    "assign_case",
    "request_clarification",
)


class SearchDocsArgs(BaseModel):
    document_type: str | None = None
    limit: int = 10


class AgentToolbox:
    """Scoped, audited, typed tool layer for the investigation agent (SRS 7.3/7.4)."""

    def __init__(self, db: Session, current_user: CurrentUserContext) -> None:
        self.db = db
        self.user = current_user
        self.tool_trace: list[dict[str, Any]] = []

    def _log_tool(self, tool_name: str, args: dict[str, Any], ok: bool, summary: str) -> None:
        assert tool_name in ALLOWLISTED_AGENT_TOOLS
        self.tool_trace.append({"tool": tool_name, "args": args, "ok": ok, "summary": summary})
        record_audit_event(
            self.db,
            organization_id=self.user.organization_id,
            actor_type="AGENT",
            actor_id="investigation_agent",
            action=f"AGENT_TOOL_{tool_name.upper()}",
            entity_type="agent_tool",
            entity_id=tool_name,
            after={"args": args, "ok": ok, "summary": summary},
        )

    def get_transaction_bundle(self, transaction_id: UUID) -> dict[str, Any]:
        try:
            bundle = get_transaction_bundle(self.db, self.user.organization_id, transaction_id)
            data = bundle.model_dump(mode="json")
            self._log_tool(
                "get_transaction_bundle",
                {"transaction_id": str(transaction_id)},
                True,
                f"Retrieved bundle: {len(bundle.goods_receipts)} GRNs, {len(bundle.invoices)} invs",
            )
            return data
        except Exception as exc:
            self._log_tool(
                "get_transaction_bundle",
                {"transaction_id": str(transaction_id)},
                False,
                str(exc),
            )
            return {}

    def search_related_documents(self, filters: SearchDocsArgs) -> list[dict[str, Any]]:
        stmt = OrgScopedRepository(self.db, Document, self.user.organization_id).base_query()
        if filters.document_type:
            stmt = stmt.where(Document.document_type == filters.document_type.upper())
        docs = list(self.db.scalars(stmt.limit(min(25, max(1, filters.limit)))).all())
        out = [
            {
                "document_id": str(d.id),
                "file_name": d.file_name,
                "document_type": d.document_type,
                "status": d.status,
                "transaction_id": str(d.transaction_id) if d.transaction_id else None,
            }
            for d in docs
        ]
        self._log_tool(
            "search_related_documents",
            filters.model_dump(),
            True,
            f"Found {len(out)} documents",
        )
        return out

    def get_vendor_history(
        self, vendor_id: UUID, date_from: date | None = None, date_to: date | None = None
    ) -> dict[str, Any]:
        profile = compute_vendor_profile(
            self.db,
            organization_id=self.user.organization_id,
            vendor_id=vendor_id,
            date_from=date_from,
            date_to=date_to,
        )
        self._log_tool(
            "get_vendor_history",
            {"vendor_id": str(vendor_id)},
            bool(profile),
            f"tx_count={profile.get('transaction_count', 0)}" if profile else "not_found",
        )
        return profile

    def run_reconciliation(self, transaction_id: UUID) -> dict[str, Any]:
        if "reconciliation:run" not in self.user.permissions:
            self._log_tool(
                "run_reconciliation",
                {"transaction_id": str(transaction_id)},
                False,
                "Permission denied",
            )
            return {"error": "FORBIDDEN"}
        res = execute_reconciliation(
            self.db,
            organization_id=self.user.organization_id,
            transaction_id=transaction_id,
            actor_type="AGENT",
            actor_id="investigation_agent",
        )
        self._log_tool(
            "run_reconciliation",
            {"transaction_id": str(transaction_id)},
            True,
            f"outcome={res['outcome']}",
        )
        return res

    def create_investigation_draft(
        self,
        *,
        case_id: UUID,
        structured_findings: dict[str, Any],
        provider_name: str,
        model_name: str,
        confidence: float,
    ) -> Investigation:
        inv = Investigation(
            organization_id=self.user.organization_id,
            case_id=case_id,
            agent_version="1.0.0",
            model_provider=provider_name,
            model_name=model_name,
            prompt_version="srs75-v1",
            structured_output_json=structured_findings,
            confidence=confidence,
            status="DRAFT_READY",
        )
        self.db.add(inv)
        self.db.flush()
        self._log_tool(
            "create_investigation_draft",
            {"case_id": str(case_id)},
            True,
            f"Saved investigation {inv.id}",
        )
        return inv

    def assign_case(self, case_id: UUID, user_id: UUID) -> dict[str, Any]:
        if "exceptions:manage" not in self.user.permissions:
            self._log_tool("assign_case", {"case_id": str(case_id)}, False, "FORBIDDEN")
            return {"error": "FORBIDDEN"}
        case = OrgScopedRepository(
            self.db, ExceptionCase, self.user.organization_id
        ).get_by_id(case_id)
        if not case:
            self._log_tool("assign_case", {"case_id": str(case_id)}, False, "NOT_FOUND")
            return {"error": "NOT_FOUND"}
        case.owner_id = user_id
        self._log_tool(
            "assign_case", {"case_id": str(case_id), "user_id": str(user_id)}, True, "assigned"
        )
        return {"assigned": True}

    def request_clarification(self, case_id: UUID, draft_text: str) -> dict[str, Any]:
        """Creates an internal draft comment only; never sends external email unattended."""
        case = OrgScopedRepository(
            self.db, ExceptionCase, self.user.organization_id
        ).get_by_id(case_id)
        if not case:
            self._log_tool("request_clarification", {"case_id": str(case_id)}, False, "NOT_FOUND")
            return {"error": "NOT_FOUND"}
        comment = ExceptionComment(
            organization_id=self.user.organization_id,
            case_id=case.id,
            author_id=self.user.id,
            body=f"[DRAFT CLARIFICATION - REQUIRES USER APPROVAL BEFORE SEND]\n{draft_text}",
            is_clarification_request=True,
        )
        self.db.add(comment)
        self.db.flush()
        self._log_tool(
            "request_clarification",
            {"case_id": str(case_id)},
            True,
            "draft_created_no_external_send",
        )
        return {"draft_comment_id": str(comment.id), "sent_externally": False}

    def evaluate_risks(self, transaction_id: UUID) -> list[dict[str, Any]]:
        return evaluate_transaction_risk(
            self.db,
            organization_id=self.user.organization_id,
            transaction_id=transaction_id,
            persist=True,
        )
