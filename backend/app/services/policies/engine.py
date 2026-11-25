import hashlib
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.domain import (
    ExceptionCase,
    GoodsReceipt,
    Invoice,
    PurchaseOrder,
    Vendor,
    VendorBankChange,
)
from app.models.policy import Policy, PolicyAuditRun, PolicyEvaluation, PolicyVersion
from app.repositories.base import OrgScopedRepository
from app.services.audit.service import record_audit_event
from app.services.policies.dsl import (
    PolicyDefinition,
    compute_definition_hash,
    evaluate_condition_tree,
)


def build_transaction_facts(
    db: Session,
    *,
    organization_id: UUID,
    transaction_id: UUID,
) -> tuple[PurchaseOrder | None, list[GoodsReceipt], list[Invoice], dict[str, Any]]:
    """Build deterministic Decimal-safe allowlisted facts for a transaction."""
    po = OrgScopedRepository(db, PurchaseOrder, organization_id).get_by_id(transaction_id)
    grn_repo = OrgScopedRepository(db, GoodsReceipt, organization_id)
    inv_repo = OrgScopedRepository(db, Invoice, organization_id)

    if po is not None:
        grns = list(db.scalars(grn_repo.base_query().where(GoodsReceipt.po_id == po.id)).all())
        invoices = list(db.scalars(inv_repo.base_query().where(Invoice.po_id == po.id)).all())
        vendor = OrgScopedRepository(db, Vendor, organization_id).get_by_id(po.vendor_id)
    else:
        single_inv = inv_repo.get_by_id(transaction_id)
        if not single_inv:
            return None, [], [], {}
        grns = []
        invoices = [single_inv]
        vendor = OrgScopedRepository(db, Vendor, organization_id).get_by_id(single_inv.vendor_id)

    ordered_qty = (
        sum((Decimal(str(ln.quantity)) for ln in po.lines), Decimal("0")) if po else Decimal("0")
    )
    accepted_qty = sum(
        (Decimal(str(gl.accepted_qty)) for g in grns for gl in g.lines),
        Decimal("0"),
    )
    rejected_qty = sum(
        (Decimal(str(gl.rejected_qty)) for g in grns for gl in g.lines),
        Decimal("0"),
    )
    received_qty = sum(
        (Decimal(str(gl.received_qty)) for g in grns for gl in g.lines),
        Decimal("0"),
    )
    invoiced_qty = sum(
        (Decimal(str(il.quantity)) for inv in invoices for il in inv.lines),
        Decimal("0"),
    )
    inv_total = sum((Decimal(str(inv.total_amount)) for inv in invoices), Decimal("0"))
    inv_tax = sum((Decimal(str(inv.tax_amount)) for inv in invoices), Decimal("0"))
    inv_sub = inv_total - inv_tax
    unit_price_max = max(
        (Decimal(str(il.unit_price)) for inv in invoices for il in inv.lines),
        default=Decimal("0"),
    )

    po_total = Decimal(str(po.total_amount)) if po else Decimal("0")
    po_sub = Decimal(str(po.subtotal_amount)) if po else Decimal("0")
    po_tax = Decimal(str(po.tax_amount)) if po else Decimal("0")
    po_unit_max = (
        max((Decimal(str(ln.unit_price)) for ln in po.lines), default=Decimal("0"))
        if po
        else Decimal("0")
    )

    price_diff_pct = Decimal("0")
    if po_unit_max > 0 and unit_price_max > po_unit_max:
        price_diff_pct = ((unit_price_max - po_unit_max) / po_unit_max * Decimal("100")).quantize(
            Decimal("0.01")
        )

    has_pending_bank = False
    dispute_count = 0
    if vendor:
        pending_bc = db.scalar(
            OrgScopedRepository(db, VendorBankChange, organization_id)
            .base_query()
            .where(
                VendorBankChange.vendor_id == vendor.id,
                VendorBankChange.verification_status == "ENHANCED_VERIFICATION_REQUIRED",
            )
        )
        has_pending_bank = pending_bc is not None
        dispute_count = len(
            list(
                db.scalars(
                    OrgScopedRepository(db, ExceptionCase, organization_id)
                    .base_query()
                    .where(ExceptionCase.transaction_id == transaction_id)
                ).all()
            )
        )

    facts: dict[str, Any] = {
        "purchase_order.total_amount": po_total,
        "purchase_order.subtotal_amount": po_sub,
        "purchase_order.tax_amount": po_tax,
        "purchase_order.ordered_qty": ordered_qty,
        "purchase_order.currency": po.currency if po else None,
        "purchase_order.status": po.status if po else None,
        "goods_receipt.accepted_qty": accepted_qty,
        "goods_receipt.rejected_qty": rejected_qty,
        "goods_receipt.received_qty": received_qty,
        "goods_receipt.grn_count": Decimal(len(grns)),
        "invoice.total_amount": inv_total,
        "invoice.subtotal_amount": inv_sub,
        "invoice.tax_amount": inv_tax,
        "invoice.invoiced_qty": invoiced_qty,
        "invoice.unit_price_max": unit_price_max,
        "invoice.currency": invoices[0].currency if invoices else None,
        "invoice.is_duplicate": any(i.duplicate_of_invoice_id is not None for i in invoices),
        "invoice.invoice_count": Decimal(len(invoices)),
        "variance.qty_diff": invoiced_qty - accepted_qty,
        "variance.amount_diff": inv_total - po_total,
        "variance.price_diff_pct": price_diff_pct,
        "vendor.status": vendor.status if vendor else None,
        "vendor.has_pending_bank_change": has_pending_bank,
        "vendor.dispute_count": Decimal(dispute_count),
    }
    return po, grns, invoices, facts


def _violation_fingerprint(
    organization_id: UUID, policy_id: UUID, policy_version_id: UUID, transaction_id: UUID
) -> str:
    raw = f"{organization_id}:{policy_id}:{policy_version_id}:{transaction_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _create_or_reuse_exception(
    db: Session,
    *,
    organization_id: UUID,
    policy: Policy,
    version: PolicyVersion,
    definition: PolicyDefinition,
    transaction_id: UUID,
    reconciliation_run_id: UUID | None,
    matched_traces: list[dict[str, Any]],
    po: PurchaseOrder | None,
    invoices: list[Invoice],
) -> tuple[ExceptionCase, bool]:
    """Idempotently create an ExceptionCase for a policy violation without duplicate open cases."""
    existing = db.scalar(
        OrgScopedRepository(db, ExceptionCase, organization_id)
        .base_query()
        .where(
            ExceptionCase.transaction_id == transaction_id,
            ExceptionCase.rule_id == policy.policy_key,
            ExceptionCase.status.in_(["OPEN", "IN_REVIEW", "ESCALATED"]),
        )
    )
    if existing:
        return existing, False

    refs: list[dict[str, str]] = []
    if po:
        refs.append({"type": "purchase_order", "id": str(po.id), "label": po.po_number})
    for inv in invoices[:2]:
        refs.append({"type": "invoice", "id": str(inv.id), "label": inv.invoice_number})

    cond_text = "; ".join(
        f"{t.get('field')} {t.get('operator')} {t.get('threshold')} (actual={t.get('actual')})"
        for t in matched_traces
        if t.get("matched")
    )
    summary = (
        f"Policy {policy.policy_key} v{version.version_number} ({policy.name}) triggered: "
        f"{cond_text or policy.description}"
    )

    exc_row = ExceptionCase(
        organization_id=organization_id,
        transaction_id=transaction_id,
        run_id=reconciliation_run_id,
        type=definition.action.exception_type,
        severity=policy.severity,
        status="OPEN",
        summary=summary,
        affected_fields_json=[t["field"] for t in matched_traces if "field" in t],
        values_json={
            "policy_id": str(policy.id),
            "policy_key": policy.policy_key,
            "policy_version": version.version_number,
            "content_hash": version.content_hash,
            "traces": matched_traces,
        },
        rule_id=policy.policy_key,
        evidence_refs_json=refs,
        version=1,
    )
    db.add(exc_row)
    db.flush()
    return exc_row, True


def evaluate_active_policies_for_transaction(
    db: Session,
    *,
    organization_id: UUID,
    transaction_id: UUID,
    reconciliation_run_id: UUID | None = None,
    audit_run_id: UUID | None = None,
    policy_ids: list[UUID] | None = None,
    categories: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Evaluate all currently ACTIVE policies from DB for a single transaction."""
    stmt = (
        OrgScopedRepository(db, Policy, organization_id)
        .base_query()
        .where(Policy.status == "ACTIVE", Policy.active_version_id.is_not(None))
    )
    if policy_ids:
        stmt = stmt.where(Policy.id.in_(policy_ids))
    if categories:
        stmt = stmt.where(Policy.category.in_([c.upper() for c in categories]))

    active_policies = list(db.scalars(stmt).all())
    if not active_policies:
        return []

    po, _, invoices, facts = build_transaction_facts(
        db, organization_id=organization_id, transaction_id=transaction_id
    )
    if not facts:
        return []

    results: list[dict[str, Any]] = []
    for pol in active_policies:
        if pol.active_version_id is None:
            continue
        ver = db.get(PolicyVersion, pol.active_version_id)
        if not ver or ver.organization_id != organization_id:
            continue
        definition = PolicyDefinition.model_validate(ver.definition_json)
        matched, traces = evaluate_condition_tree(definition.condition, facts)
        fp = _violation_fingerprint(organization_id, pol.id, ver.id, transaction_id)

        exc_id: UUID | None = None
        is_new_exc = False
        if matched:
            exc_row, is_new_exc = _create_or_reuse_exception(
                db,
                organization_id=organization_id,
                policy=pol,
                version=ver,
                definition=definition,
                transaction_id=transaction_id,
                reconciliation_run_id=reconciliation_run_id,
                matched_traces=traces,
                po=po,
                invoices=invoices,
            )
            exc_id = exc_row.id

        ev = PolicyEvaluation(
            organization_id=organization_id,
            policy_id=pol.id,
            policy_version_id=ver.id,
            audit_run_id=audit_run_id,
            reconciliation_run_id=reconciliation_run_id,
            transaction_id=transaction_id,
            status="VIOLATION" if matched else "PASS",
            matched_conditions_json=traces,
            result_summary=(
                f"{'VIOLATION' if matched else 'PASS'} under {pol.policy_key} v{ver.version_number}"
            ),
            violation_fingerprint=fp,
            exception_id=exc_id,
        )
        db.add(ev)
        db.flush()
        results.append(
            {
                "evaluation_id": str(ev.id),
                "policy_id": str(pol.id),
                "policy_key": pol.policy_key,
                "policy_version": ver.version_number,
                "status": ev.status,
                "exception_id": str(exc_id) if exc_id else None,
                "is_new_exception": is_new_exc,
                "matched_conditions": traces,
            }
        )
    return results


def preview_policy_impact(
    db: Session,
    *,
    organization_id: UUID,
    definition_dict: dict[str, Any],
    severity: str = "MEDIUM",
    policy_key: str = "DRAFT_PREVIEW",
) -> dict[str, Any]:
    """Dry-run evaluation of a draft policy without mutating DB or creating exceptions."""
    definition = PolicyDefinition.model_validate(definition_dict)
    content_hash = compute_definition_hash(definition.model_dump())

    pos = list(
        db.scalars(
            OrgScopedRepository(db, PurchaseOrder, organization_id)
            .base_query()
            .order_by(desc(PurchaseOrder.issue_date))
            .limit(200)
        ).all()
    )
    matching: list[dict[str, Any]] = []
    existing_exc_count = 0
    for po in pos:
        _, _, _, facts = build_transaction_facts(
            db, organization_id=organization_id, transaction_id=po.id
        )
        matched, traces = evaluate_condition_tree(definition.condition, facts)
        if matched:
            has_open_exc = (
                db.scalar(
                    OrgScopedRepository(db, ExceptionCase, organization_id)
                    .base_query()
                    .where(
                        ExceptionCase.transaction_id == po.id,
                        ExceptionCase.status.in_(["OPEN", "IN_REVIEW", "ESCALATED"]),
                    )
                )
                is not None
            )
            if has_open_exc:
                existing_exc_count += 1
            matching.append(
                {
                    "transaction_id": str(po.id),
                    "po_number": po.po_number,
                    "total_amount": str(po.total_amount),
                    "currency": po.currency,
                    "already_has_open_exception": has_open_exc,
                    "matched_conditions": traces,
                }
            )

    return {
        "dry_run": True,
        "policy_key": policy_key,
        "content_hash": content_hash,
        "severity": severity,
        "records_scanned": len(pos),
        "records_matching": len(matching),
        "existing_exceptions": existing_exc_count,
        "potential_new_exceptions": len(matching) - existing_exc_count,
        "severity_breakdown": {severity: len(matching)},
        "affected_transactions": matching[:25],
    }


def create_policy(
    db: Session,
    *,
    organization_id: UUID,
    actor_id: str,
    policy_key: str,
    name: str,
    description: str,
    category: str,
    severity: str,
    definition_dict: dict[str, Any],
    is_system_policy: bool = False,
    change_summary: str = "Initial draft",
) -> tuple[Policy, PolicyVersion]:
    existing = db.scalar(
        OrgScopedRepository(db, Policy, organization_id)
        .base_query()
        .where(Policy.policy_key == policy_key)
    )
    if existing:
        raise AppError(
            "POLICY_KEY_EXISTS",
            f"Policy key '{policy_key}' already exists in organization.",
            status.HTTP_409_CONFLICT,
        )

    definition = PolicyDefinition.model_validate(definition_dict)
    norm_def = definition.model_dump()
    content_hash = compute_definition_hash(norm_def)

    pol = Policy(
        organization_id=organization_id,
        policy_key=policy_key.strip().upper(),
        name=name.strip(),
        description=description.strip(),
        category=category.strip().upper(),
        status="DRAFT",
        severity=severity.strip().upper(),
        is_system_policy=is_system_policy,
        created_by=actor_id,
        updated_by=actor_id,
    )
    db.add(pol)
    db.flush()

    ver = PolicyVersion(
        policy_id=pol.id,
        organization_id=organization_id,
        version_number=1,
        definition_json=norm_def,
        content_hash=content_hash,
        change_summary=change_summary,
        is_validated=True,
        created_by=actor_id,
    )
    db.add(ver)
    db.flush()

    record_audit_event(
        db,
        organization_id=organization_id,
        actor_type="USER",
        actor_id=actor_id,
        action="POLICY_CREATED",
        entity_type="policy",
        entity_id=str(pol.id),
        after={"policy_key": pol.policy_key, "version": 1, "content_hash": content_hash},
    )
    db.commit()
    return pol, ver


def update_policy_draft(
    db: Session,
    *,
    organization_id: UUID,
    policy_id: UUID,
    actor_id: str,
    name: str | None = None,
    description: str | None = None,
    category: str | None = None,
    severity: str | None = None,
    definition_dict: dict[str, Any] | None = None,
    change_summary: str = "Updated policy definition",
) -> tuple[Policy, PolicyVersion]:
    pol = OrgScopedRepository(db, Policy, organization_id).get_by_id(policy_id)
    if not pol:
        raise AppError("POLICY_NOT_FOUND", "Policy not found.", status.HTTP_404_NOT_FOUND)

    latest_ver = db.scalar(
        OrgScopedRepository(db, PolicyVersion, organization_id)
        .base_query()
        .where(PolicyVersion.policy_id == pol.id)
        .order_by(desc(PolicyVersion.version_number))
    )
    if not latest_ver:
        raise AppError("POLICY_VERSION_NOT_FOUND", "No version found.", status.HTTP_404_NOT_FOUND)

    if name is not None:
        pol.name = name.strip()
    if description is not None:
        pol.description = description.strip()
    if category is not None:
        pol.category = category.strip().upper()
    if severity is not None:
        pol.severity = severity.strip().upper()
    pol.updated_by = actor_id

    norm_def = (
        PolicyDefinition.model_validate(definition_dict).model_dump()
        if definition_dict is not None
        else latest_ver.definition_json
    )
    content_hash = compute_definition_hash(norm_def)

    # Always create a new immutable PolicyVersion if latest was already activated
    if latest_ver.activated_at is not None or pol.status == "ACTIVE":
        new_ver = PolicyVersion(
            policy_id=pol.id,
            organization_id=organization_id,
            version_number=latest_ver.version_number + 1,
            definition_json=norm_def,
            content_hash=content_hash,
            change_summary=change_summary,
            is_validated=True,
            created_by=actor_id,
        )
        db.add(new_ver)
        db.flush()
        target_ver = new_ver
    else:
        latest_ver.definition_json = norm_def
        latest_ver.content_hash = content_hash
        latest_ver.change_summary = change_summary
        latest_ver.is_validated = True
        target_ver = latest_ver

    record_audit_event(
        db,
        organization_id=organization_id,
        actor_type="USER",
        actor_id=actor_id,
        action="POLICY_UPDATED",
        entity_type="policy",
        entity_id=str(pol.id),
        after={
            "policy_key": pol.policy_key,
            "latest_version": target_ver.version_number,
            "content_hash": target_ver.content_hash,
        },
    )
    db.commit()
    return pol, target_ver


def activate_policy(
    db: Session,
    *,
    organization_id: UUID,
    policy_id: UUID,
    actor_id: str,
    version_number: int | None = None,
) -> tuple[Policy, PolicyVersion]:
    pol = OrgScopedRepository(db, Policy, organization_id).get_by_id(policy_id)
    if not pol:
        raise AppError("POLICY_NOT_FOUND", "Policy not found.", status.HTTP_404_NOT_FOUND)

    stmt = (
        OrgScopedRepository(db, PolicyVersion, organization_id)
        .base_query()
        .where(PolicyVersion.policy_id == pol.id)
    )
    if version_number is not None:
        stmt = stmt.where(PolicyVersion.version_number == version_number)
    else:
        stmt = stmt.order_by(desc(PolicyVersion.version_number))
    ver = db.scalar(stmt)
    if not ver:
        raise AppError(
            "POLICY_VERSION_NOT_FOUND", "Policy version not found.", status.HTTP_404_NOT_FOUND
        )

    # Validate schema strictly before activation
    PolicyDefinition.model_validate(ver.definition_json)
    ver.is_validated = True
    if ver.activated_at is None:
        ver.activated_at = datetime.now(UTC)

    prev_ver_id = str(pol.active_version_id) if pol.active_version_id else None
    pol.active_version_id = ver.id
    pol.status = "ACTIVE"
    pol.updated_by = actor_id

    record_audit_event(
        db,
        organization_id=organization_id,
        actor_type="USER",
        actor_id=actor_id,
        action="POLICY_ACTIVATED",
        entity_type="policy",
        entity_id=str(pol.id),
        before={"active_version_id": prev_ver_id},
        after={
            "active_version_id": str(ver.id),
            "version_number": ver.version_number,
            "content_hash": ver.content_hash,
        },
    )
    db.commit()
    return pol, ver


def deactivate_policy(
    db: Session,
    *,
    organization_id: UUID,
    policy_id: UUID,
    actor_id: str,
) -> Policy:
    pol = OrgScopedRepository(db, Policy, organization_id).get_by_id(policy_id)
    if not pol:
        raise AppError("POLICY_NOT_FOUND", "Policy not found.", status.HTTP_404_NOT_FOUND)
    if pol.is_system_policy:
        raise AppError(
            "SYSTEM_POLICY_PROTECTED",
            "Required system policies cannot be deactivated.",
            status.HTTP_409_CONFLICT,
        )
    prev_status = pol.status
    pol.status = "INACTIVE"
    pol.updated_by = actor_id

    record_audit_event(
        db,
        organization_id=organization_id,
        actor_type="USER",
        actor_id=actor_id,
        action="POLICY_DEACTIVATED",
        entity_type="policy",
        entity_id=str(pol.id),
        before={"status": prev_status},
        after={"status": "INACTIVE"},
    )
    db.commit()
    return pol


def run_policy_audit(
    db: Session,
    *,
    organization_id: UUID,
    triggered_by: str,
    policy_ids: list[UUID] | None = None,
    categories: list[str] | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> PolicyAuditRun:
    """Re-Audit historical organization transactions against active policies."""
    stmt = (
        OrgScopedRepository(db, Policy, organization_id)
        .base_query()
        .where(Policy.status == "ACTIVE", Policy.active_version_id.is_not(None))
    )
    if policy_ids:
        stmt = stmt.where(Policy.id.in_(policy_ids))
    if categories:
        stmt = stmt.where(Policy.category.in_([c.upper() for c in categories]))
    active_policies = list(db.scalars(stmt).all())

    selected_versions: list[dict[str, Any]] = []
    for p in active_policies:
        if p.active_version_id:
            v = db.get(PolicyVersion, p.active_version_id)
            if v:
                selected_versions.append(
                    {
                        "policy_id": str(p.id),
                        "policy_key": p.policy_key,
                        "name": p.name,
                        "version_id": str(v.id),
                        "version_number": v.version_number,
                        "content_hash": v.content_hash,
                    }
                )

    audit_run = PolicyAuditRun(
        organization_id=organization_id,
        triggered_by=triggered_by,
        status="PROCESSING",
        selected_policy_versions_json=selected_versions,
        scope_json={
            "policy_ids": [str(x) for x in (policy_ids or [])],
            "categories": categories or [],
            "date_from": str(date_from) if date_from else None,
            "date_to": str(date_to) if date_to else None,
        },
    )
    db.add(audit_run)
    db.flush()

    record_audit_event(
        db,
        organization_id=organization_id,
        actor_type="USER",
        actor_id=triggered_by,
        action="POLICY_AUDIT_STARTED",
        entity_type="policy_audit_run",
        entity_id=str(audit_run.id),
        after={"selected_policies": len(selected_versions)},
    )

    po_stmt = OrgScopedRepository(db, PurchaseOrder, organization_id).base_query()
    if date_from:
        po_stmt = po_stmt.where(PurchaseOrder.issue_date >= date_from)
    if date_to:
        po_stmt = po_stmt.where(PurchaseOrder.issue_date <= date_to)
    pos = list(db.scalars(po_stmt.order_by(desc(PurchaseOrder.issue_date))).all())

    newly_flagged: list[dict[str, Any]] = []
    existing_violations: list[dict[str, Any]] = []
    no_longer_triggered: list[dict[str, Any]] = []
    eval_count = 0
    errors = 0

    for po in pos:
        try:
            # Check prior violation fingerprints for this tx before evaluating
            prior_viol_keys = {
                ev.policy_id
                for ev in db.scalars(
                    OrgScopedRepository(db, PolicyEvaluation, organization_id)
                    .base_query()
                    .where(
                        PolicyEvaluation.transaction_id == po.id,
                        PolicyEvaluation.status == "VIOLATION",
                    )
                ).all()
            }

            tx_results = evaluate_active_policies_for_transaction(
                db,
                organization_id=organization_id,
                transaction_id=po.id,
                audit_run_id=audit_run.id,
                policy_ids=policy_ids,
                categories=categories,
            )
            eval_count += len(tx_results)
            for res in tx_results:
                pid = UUID(res["policy_id"])
                item = {
                    "transaction_id": str(po.id),
                    "po_number": po.po_number,
                    "policy_id": res["policy_id"],
                    "policy_key": res["policy_key"],
                    "policy_version": res["policy_version"],
                    "exception_id": res["exception_id"],
                    "matched_conditions": res["matched_conditions"],
                }
                if res["status"] == "VIOLATION":
                    if res["is_new_exception"]:
                        newly_flagged.append(item)
                    else:
                        existing_violations.append(item)
                elif pid in prior_viol_keys:
                    no_longer_triggered.append(item)
        except Exception:
            errors += 1

    audit_run.transactions_scanned = len(pos)
    audit_run.evaluations_performed = eval_count
    audit_run.new_exceptions = len(newly_flagged)
    audit_run.existing_exceptions = len(existing_violations)
    audit_run.resolved_exceptions = len(no_longer_triggered)
    audit_run.error_count = errors
    audit_run.status = (
        "SUCCEEDED"
        if errors == 0
        else ("PARTIALLY_SUCCEEDED" if eval_count > 0 else "FAILED")
    )
    audit_run.completed_at = datetime.now(UTC)
    audit_run.summary_json = {
        "newly_flagged": newly_flagged[:50],
        "existing_violations": existing_violations[:50],
        "no_longer_triggered": no_longer_triggered[:50],
    }

    record_audit_event(
        db,
        organization_id=organization_id,
        actor_type="USER",
        actor_id=triggered_by,
        action="POLICY_AUDIT_COMPLETED",
        entity_type="policy_audit_run",
        entity_id=str(audit_run.id),
        after={
            "status": audit_run.status,
            "transactions_scanned": audit_run.transactions_scanned,
            "new_exceptions": audit_run.new_exceptions,
            "existing_exceptions": audit_run.existing_exceptions,
            "resolved_exceptions": audit_run.resolved_exceptions,
        },
    )
    db.commit()
    return audit_run
