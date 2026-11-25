from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from math import ceil
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import asc, desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import AppError
from app.core.permissions import CurrentUserContext, require_permission
from app.models.domain import (
    ExceptionCase,
    GoodsReceipt,
    GRNLine,
    Invoice,
    InvoiceLine,
    POLine,
    PurchaseOrder,
    ReconciliationRun,
    RiskSignal,
    Vendor,
)
from app.repositories.base import OrgScopedRepository
from app.schemas.common import PaginatedResponse, paginate_params
from app.schemas.domain import (
    GoodsReceiptCreateRequest,
    GoodsReceiptResponse,
    InvoiceCreateRequest,
    InvoiceResponse,
    PurchaseOrderCreateRequest,
    PurchaseOrderResponse,
    TransactionBundleResponse,
    TransactionListItem,
)
from app.services.audit.service import record_audit_event
from app.services.transactions.bundle import (
    get_transaction_bundle,
    grn_to_response,
    invoice_to_response,
    normalize_invoice_number,
    po_to_response,
)

router = APIRouter(tags=["transactions"])

Q4 = Decimal("0.0001")


def _q(val: Decimal) -> Decimal:
    return val.quantize(Q4, rounding=ROUND_HALF_UP)


@router.get("/purchase-orders", response_model=PaginatedResponse[PurchaseOrderResponse])
def list_purchase_orders(
    vendor_id: UUID | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    current_user: CurrentUserContext = Depends(require_permission("transactions:read")),
    db: Session = Depends(get_db),
) -> PaginatedResponse[PurchaseOrderResponse]:
    safe_page, safe_size, offset = paginate_params(page, page_size)
    repo = OrgScopedRepository(db, PurchaseOrder, current_user.organization_id)
    stmt = repo.base_query()
    if vendor_id:
        stmt = stmt.where(PurchaseOrder.vendor_id == vendor_id)
    if status_filter:
        stmt = stmt.where(PurchaseOrder.status == status_filter)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        db.scalars(
            stmt.order_by(desc(PurchaseOrder.issue_date), asc(PurchaseOrder.id))
            .offset(offset)
            .limit(safe_size)
        ).all()
    )
    return PaginatedResponse(
        items=[po_to_response(p) for p in rows],
        total=total,
        page=safe_page,
        page_size=safe_size,
        total_pages=max(1, ceil(total / safe_size)) if total else 1,
    )


@router.post(
    "/purchase-orders",
    response_model=PurchaseOrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_purchase_order(
    payload: PurchaseOrderCreateRequest,
    current_user: CurrentUserContext = Depends(require_permission("transactions:write")),
    db: Session = Depends(get_db),
) -> PurchaseOrderResponse:
    vendor_repo = OrgScopedRepository(db, Vendor, current_user.organization_id)
    if not vendor_repo.get_by_id(payload.vendor_id):
        raise AppError("VENDOR_NOT_FOUND", "Vendor not found.", status.HTTP_404_NOT_FOUND)

    subtotal = Decimal("0")
    tax_total = Decimal("0")
    disc_total = Decimal("0")
    line_objs: list[POLine] = []
    for ln in payload.lines:
        ext = _q(ln.quantity * ln.unit_price)
        ln_tax = _q(ln.tax_amount if ln.tax_amount else ext * ln.tax_rate)
        ln_total = _q(
            ln.line_total if ln.line_total is not None else ext - ln.discount_amount + ln_tax
        )
        subtotal += ext
        tax_total += ln_tax
        disc_total += ln.discount_amount
        line_objs.append(
            POLine(
                organization_id=current_user.organization_id,
                line_number=ln.line_number,
                item_code=ln.item_code,
                description=ln.description,
                uom=ln.uom,
                quantity=_q(ln.quantity),
                unit_price=_q(ln.unit_price),
                tax_rate=_q(ln.tax_rate),
                tax_amount=ln_tax,
                discount_amount=_q(ln.discount_amount),
                line_total=ln_total,
            )
        )

    total = _q(subtotal - disc_total + tax_total + payload.freight_amount)
    po = PurchaseOrder(
        organization_id=current_user.organization_id,
        vendor_id=payload.vendor_id,
        po_number=payload.po_number,
        issue_date=payload.issue_date,
        currency=payload.currency.upper(),
        status="OPEN",
        subtotal_amount=_q(subtotal),
        tax_amount=_q(tax_total),
        discount_amount=_q(disc_total),
        freight_amount=_q(payload.freight_amount),
        total_amount=total,
        scenario_label=payload.scenario_label,
        lines=line_objs,
    )
    db.add(po)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(
            "PO_EXISTS", "PO number already exists in organization.", status.HTTP_409_CONFLICT
        ) from exc

    record_audit_event(
        db,
        organization_id=current_user.organization_id,
        actor_type="USER",
        actor_id=str(current_user.id),
        action="PO_CREATED",
        entity_type="purchase_order",
        entity_id=str(po.id),
        after={"po_number": po.po_number, "total": str(po.total_amount)},
    )
    db.commit()
    db.refresh(po)
    return po_to_response(po)


@router.get("/goods-receipts", response_model=PaginatedResponse[GoodsReceiptResponse])
def list_goods_receipts(
    po_id: UUID | None = Query(default=None),
    vendor_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    current_user: CurrentUserContext = Depends(require_permission("transactions:read")),
    db: Session = Depends(get_db),
) -> PaginatedResponse[GoodsReceiptResponse]:
    safe_page, safe_size, offset = paginate_params(page, page_size)
    repo = OrgScopedRepository(db, GoodsReceipt, current_user.organization_id)
    stmt = repo.base_query()
    if po_id:
        stmt = stmt.where(GoodsReceipt.po_id == po_id)
    if vendor_id:
        stmt = stmt.where(GoodsReceipt.vendor_id == vendor_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        db.scalars(
            stmt.order_by(desc(GoodsReceipt.received_at), asc(GoodsReceipt.id))
            .offset(offset)
            .limit(safe_size)
        ).all()
    )
    return PaginatedResponse(
        items=[grn_to_response(g) for g in rows],
        total=total,
        page=safe_page,
        page_size=safe_size,
        total_pages=max(1, ceil(total / safe_size)) if total else 1,
    )


@router.post(
    "/goods-receipts",
    response_model=GoodsReceiptResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_goods_receipt(
    payload: GoodsReceiptCreateRequest,
    current_user: CurrentUserContext = Depends(require_permission("receiving:write")),
    db: Session = Depends(get_db),
) -> GoodsReceiptResponse:
    vendor_repo = OrgScopedRepository(db, Vendor, current_user.organization_id)
    if not vendor_repo.get_by_id(payload.vendor_id):
        raise AppError("VENDOR_NOT_FOUND", "Vendor not found.", status.HTTP_404_NOT_FOUND)
    if payload.po_id:
        po_repo = OrgScopedRepository(db, PurchaseOrder, current_user.organization_id)
        if not po_repo.get_by_id(payload.po_id):
            raise AppError("PO_NOT_FOUND", "Purchase order not found.", status.HTTP_404_NOT_FOUND)

    grn = GoodsReceipt(
        organization_id=current_user.organization_id,
        vendor_id=payload.vendor_id,
        grn_number=payload.grn_number,
        po_id=payload.po_id,
        received_at=payload.received_at,
        status="ACCEPTED",
        scenario_label=payload.scenario_label,
        lines=[
            GRNLine(
                organization_id=current_user.organization_id,
                po_line_id=ln.po_line_id,
                item_code=ln.item_code,
                description=ln.description,
                received_qty=_q(ln.received_qty),
                accepted_qty=_q(ln.accepted_qty),
                rejected_qty=_q(ln.rejected_qty),
                uom=ln.uom,
            )
            for ln in payload.lines
        ],
    )
    db.add(grn)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(
            "GRN_EXISTS", "GRN number already exists in organization.", status.HTTP_409_CONFLICT
        ) from exc

    record_audit_event(
        db,
        organization_id=current_user.organization_id,
        actor_type="USER",
        actor_id=str(current_user.id),
        action="GRN_CREATED",
        entity_type="goods_receipt",
        entity_id=str(grn.id),
        after={"grn_number": grn.grn_number},
    )
    db.commit()
    db.refresh(grn)
    return grn_to_response(grn)


@router.get("/invoices", response_model=PaginatedResponse[InvoiceResponse])
def list_invoices(
    po_id: UUID | None = Query(default=None),
    vendor_id: UUID | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    current_user: CurrentUserContext = Depends(require_permission("transactions:read")),
    db: Session = Depends(get_db),
) -> PaginatedResponse[InvoiceResponse]:
    safe_page, safe_size, offset = paginate_params(page, page_size)
    repo = OrgScopedRepository(db, Invoice, current_user.organization_id)
    stmt = repo.base_query()
    if po_id:
        stmt = stmt.where(Invoice.po_id == po_id)
    if vendor_id:
        stmt = stmt.where(Invoice.vendor_id == vendor_id)
    if status_filter:
        stmt = stmt.where(Invoice.status == status_filter)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        db.scalars(
            stmt.order_by(desc(Invoice.invoice_date), asc(Invoice.id))
            .offset(offset)
            .limit(safe_size)
        ).all()
    )
    return PaginatedResponse(
        items=[invoice_to_response(i) for i in rows],
        total=total,
        page=safe_page,
        page_size=safe_size,
        total_pages=max(1, ceil(total / safe_size)) if total else 1,
    )


@router.post("/invoices", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
def create_invoice(
    payload: InvoiceCreateRequest,
    current_user: CurrentUserContext = Depends(require_permission("transactions:write")),
    db: Session = Depends(get_db),
) -> InvoiceResponse:
    vendor_repo = OrgScopedRepository(db, Vendor, current_user.organization_id)
    if not vendor_repo.get_by_id(payload.vendor_id):
        raise AppError("VENDOR_NOT_FOUND", "Vendor not found.", status.HTTP_404_NOT_FOUND)
    if payload.po_id:
        po_repo = OrgScopedRepository(db, PurchaseOrder, current_user.organization_id)
        if not po_repo.get_by_id(payload.po_id):
            raise AppError("PO_NOT_FOUND", "Purchase order not found.", status.HTTP_404_NOT_FOUND)

    inv_repo = OrgScopedRepository(db, Invoice, current_user.organization_id)
    if payload.idempotency_key:
        idem_match = db.scalar(
            inv_repo.base_query().where(Invoice.idempotency_key == payload.idempotency_key)
        )
        if idem_match:
            return invoice_to_response(idem_match)

    norm_num = normalize_invoice_number(payload.invoice_number)
    existing_dup = db.scalar(
        inv_repo.base_query().where(
            Invoice.vendor_id == payload.vendor_id,
            Invoice.normalized_invoice_number == norm_num,
        )
    )
    if existing_dup:
        raise AppError(
            code="DUPLICATE_INVOICE",
            message="Duplicate invoice number for this vendor within organization.",
            status_code=status.HTTP_409_CONFLICT,
            details={"existing_invoice_id": str(existing_dup.id), "normalized_number": norm_num},
        )

    subtotal = Decimal("0")
    tax_total = Decimal("0")
    disc_total = Decimal("0")
    line_objs: list[InvoiceLine] = []
    for ln in payload.lines:
        ext = _q(ln.quantity * ln.unit_price)
        ln_tax = _q(ln.tax_amount if ln.tax_amount else ext * ln.tax_rate)
        ln_total = _q(
            ln.line_total if ln.line_total is not None else ext - ln.discount_amount + ln_tax
        )
        subtotal += ext
        tax_total += ln_tax
        disc_total += ln.discount_amount
        line_objs.append(
            InvoiceLine(
                organization_id=current_user.organization_id,
                po_line_id=ln.po_line_id,
                item_code=ln.item_code,
                description=ln.description,
                uom=ln.uom,
                quantity=_q(ln.quantity),
                unit_price=_q(ln.unit_price),
                tax_rate=_q(ln.tax_rate),
                tax_amount=ln_tax,
                discount_amount=_q(ln.discount_amount),
                line_total=ln_total,
            )
        )

    sub_val = _q(payload.subtotal_amount if payload.subtotal_amount is not None else subtotal)
    tax_val = _q(payload.tax_amount if payload.tax_amount is not None else tax_total)
    tot_val = _q(
        payload.total_amount
        if payload.total_amount is not None
        else sub_val - disc_total + tax_val + payload.freight_amount
    )

    inv = Invoice(
        organization_id=current_user.organization_id,
        vendor_id=payload.vendor_id,
        invoice_number=payload.invoice_number,
        normalized_invoice_number=norm_num,
        po_id=payload.po_id,
        invoice_date=payload.invoice_date,
        due_date=payload.due_date,
        currency=payload.currency.upper(),
        subtotal_amount=sub_val,
        tax_amount=tax_val,
        discount_amount=_q(disc_total),
        freight_amount=_q(payload.freight_amount),
        total_amount=tot_val,
        status="PENDING",
        scenario_label=payload.scenario_label,
        idempotency_key=payload.idempotency_key,
        lines=line_objs,
    )
    db.add(inv)
    db.flush()

    record_audit_event(
        db,
        organization_id=current_user.organization_id,
        actor_type="USER",
        actor_id=str(current_user.id),
        action="INVOICE_CREATED",
        entity_type="invoice",
        entity_id=str(inv.id),
        after={"invoice_number": inv.invoice_number, "total": str(inv.total_amount)},
    )
    db.commit()
    db.refresh(inv)
    return invoice_to_response(inv)


@router.get("/transactions", response_model=PaginatedResponse[TransactionListItem])
def list_transactions(
    vendor_id: UUID | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    min_amount: Decimal | None = Query(default=None),
    max_amount: Decimal | None = Query(default=None),
    exception_type: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    scenario_label: str | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    current_user: CurrentUserContext = Depends(require_permission("transactions:read")),
    db: Session = Depends(get_db),
) -> PaginatedResponse[TransactionListItem]:
    safe_page, safe_size, offset = paginate_params(page, page_size)
    org_id = current_user.organization_id

    vendors = {
        v.id: v
        for v in db.scalars(OrgScopedRepository(db, Vendor, org_id).base_query()).all()
    }
    pos = list(
        db.scalars(
            OrgScopedRepository(db, PurchaseOrder, org_id)
            .base_query()
            .order_by(desc(PurchaseOrder.issue_date), asc(PurchaseOrder.id))
        ).all()
    )
    standalone_invs = list(
        db.scalars(
            OrgScopedRepository(db, Invoice, org_id)
            .base_query()
            .where(Invoice.po_id.is_(None))
            .order_by(desc(Invoice.invoice_date), asc(Invoice.id))
        ).all()
    )

    runs = list(
        db.scalars(
            OrgScopedRepository(db, ReconciliationRun, org_id)
            .base_query()
            .order_by(desc(ReconciliationRun.completed_at))
        ).all()
    )
    latest_run_by_tx: dict[UUID, ReconciliationRun] = {}
    for r in runs:
        if r.transaction_id not in latest_run_by_tx:
            latest_run_by_tx[r.transaction_id] = r

    excs = list(
        db.scalars(OrgScopedRepository(db, ExceptionCase, org_id).base_query()).all()
    )
    excs_by_tx: dict[UUID, list[ExceptionCase]] = {}
    for e in excs:
        excs_by_tx.setdefault(e.transaction_id, []).append(e)

    risks = list(
        db.scalars(OrgScopedRepository(db, RiskSignal, org_id).base_query()).all()
    )
    risks_by_tx: dict[UUID, list[RiskSignal]] = {}
    for s in risks:
        risks_by_tx.setdefault(s.transaction_id, []).append(s)

    combined: list[TransactionListItem] = []

    def _risk_level_for(tx_id: UUID) -> str:
        sigs = risks_by_tx.get(tx_id, [])
        if any(s.severity == "HIGH" for s in sigs):
            return "HIGH"
        if any(s.severity == "MEDIUM" for s in sigs):
            return "MEDIUM"
        if sigs:
            return "LOW"
        return "NONE"

    for po in pos:
        tx_excs = excs_by_tx.get(po.id, [])
        run = latest_run_by_tx.get(po.id)
        combined.append(
            TransactionListItem(
                transaction_id=po.id,
                transaction_type="PO_BUNDLE",
                po_number=po.po_number,
                vendor_id=po.vendor_id,
                vendor_name=vendors[po.vendor_id].legal_name if po.vendor_id in vendors else "",
                currency=po.currency,
                total_amount=po.total_amount,
                document_date=po.issue_date,
                status=po.status,
                latest_outcome=run.outcome if run else None,
                exception_count=len(tx_excs),
                risk_level=_risk_level_for(po.id),
                scenario_label=po.scenario_label,
            )
        )

    for inv in standalone_invs:
        tx_excs = excs_by_tx.get(inv.id, [])
        run = latest_run_by_tx.get(inv.id)
        combined.append(
            TransactionListItem(
                transaction_id=inv.id,
                transaction_type="STANDALONE_INVOICE",
                po_number=None,
                vendor_id=inv.vendor_id,
                vendor_name=vendors[inv.vendor_id].legal_name if inv.vendor_id in vendors else "",
                currency=inv.currency,
                total_amount=inv.total_amount,
                document_date=inv.invoice_date,
                status=inv.status,
                latest_outcome=run.outcome if run else None,
                exception_count=len(tx_excs),
                risk_level=_risk_level_for(inv.id),
                scenario_label=inv.scenario_label,
            )
        )

    filtered: list[TransactionListItem] = []
    for item in combined:
        if vendor_id and item.vendor_id != vendor_id:
            continue
        if status_filter and item.status != status_filter and item.latest_outcome != status_filter:
            continue
        if date_from and item.document_date < date_from:
            continue
        if date_to and item.document_date > date_to:
            continue
        if min_amount is not None and item.total_amount < min_amount:
            continue
        if max_amount is not None and item.total_amount > max_amount:
            continue
        if scenario_label and item.scenario_label != scenario_label:
            continue
        if search:
            q_low = search.lower().strip()
            if (
                q_low not in (item.po_number or "").lower()
                and q_low not in item.vendor_name.lower()
                and q_low not in (item.scenario_label or "").lower()
            ):
                continue
        if risk_level and item.risk_level != risk_level:
            continue
        if exception_type:
            tx_types = {e.type for e in excs_by_tx.get(item.transaction_id, [])}
            if exception_type not in tx_types:
                continue
        filtered.append(item)

    filtered.sort(key=lambda x: (x.document_date, str(x.transaction_id)), reverse=True)
    total = len(filtered)
    page_items = filtered[offset : offset + safe_size]
    return PaginatedResponse(
        items=page_items,
        total=total,
        page=safe_page,
        page_size=safe_size,
        total_pages=max(1, ceil(total / safe_size)) if total else 1,
    )


@router.get("/transactions/{transaction_id}", response_model=TransactionBundleResponse)
def get_transaction(
    transaction_id: UUID,
    current_user: CurrentUserContext = Depends(require_permission("transactions:read")),
    db: Session = Depends(get_db),
) -> TransactionBundleResponse:
    return get_transaction_bundle(db, current_user.organization_id, transaction_id)
