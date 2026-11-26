"""Deterministic synthetic seed generator for ReconX AI.

Usage:
    python scripts/seed.py --reset
"""
import argparse
import hashlib
import random
import sys
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from uuid import UUID, uuid5

# Ensure backend/ is on sys.path when invoked as `python scripts/seed.py`
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import delete, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

import app.models.audit  # noqa: E402, F401
from app.core.database import Base, SessionLocal, engine, ensure_sqlite_audit_triggers  # noqa: E402
from app.models.auth import Organization, RefreshToken, User, UserRole  # noqa: E402
from app.models.config import AppConfig  # noqa: E402
from app.models.domain import (  # noqa: E402
    Approval,
    Document,
    ExceptionCase,
    ExceptionComment,
    ExtractionField,
    GoodsReceipt,
    GRNLine,
    Investigation,
    Invoice,
    InvoiceLine,
    Job,
    MatchResult,
    Notification,
    POLine,
    PurchaseOrder,
    ReconciliationRun,
    RiskSignal,
    ToleranceConfig,
    Vendor,
    VendorBankChange,
)
from app.services.bootstrap import seed_foundation_users  # noqa: E402
from app.services.transactions.bundle import normalize_invoice_number, normalize_name  # noqa: E402

SEED_NAMESPACE = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
Q4 = Decimal("0.0001")


def _det_uuid(key: str) -> UUID:
    return uuid5(SEED_NAMESPACE, key)


def _q(val: Decimal) -> Decimal:
    return val.quantize(Q4, rounding=ROUND_HALF_UP)


def reset_domain_data(db: Session) -> None:
    """Delete domain records (preserving append-only audit_event in Postgres if triggered)."""
    for model in [
        Notification,
        Approval,
        RiskSignal,
        Investigation,
        ExceptionComment,
        ExceptionCase,
        MatchResult,
        ReconciliationRun,
        Job,
        ToleranceConfig,
        InvoiceLine,
        Invoice,
        GRNLine,
        GoodsReceipt,
        POLine,
        PurchaseOrder,
        ExtractionField,
        Document,
        VendorBankChange,
        Vendor,
    ]:
        db.execute(delete(model))
    db.commit()


def full_reset_for_demo(db: Session) -> None:
    """Clean all tables in SQLite/local reset mode; in Postgres audit_event stays append-only."""
    reset_domain_data(db)
    db.execute(delete(RefreshToken))
    db.execute(delete(AppConfig))
    db.execute(delete(UserRole))
    db.execute(delete(User))
    db.execute(delete(Organization))
    db.commit()


def seed_synthetic_dataset(
    db: Session,
    *,
    reset: bool = False,
    seed_baseline_reconciliation: bool = False,
) -> dict[str, str | int]:
    if reset:
        reset_domain_data(db)

    org = seed_foundation_users(db)

    # Default organization tolerance config
    existing_tol = db.scalar(
        select(ToleranceConfig).where(
            ToleranceConfig.organization_id == org.id,
            ToleranceConfig.vendor_id.is_(None),
            ToleranceConfig.is_active.is_(True),
        )
    )
    if not existing_tol:
        db.add(
            ToleranceConfig(
                id=_det_uuid("tol-default"),
                organization_id=org.id,
                vendor_id=None,
                item_code=None,
                price_abs_tolerance=Decimal("0.0000"),
                price_pct_tolerance=Decimal("0.0200"),
                qty_abs_tolerance=Decimal("0.0000"),
                qty_pct_tolerance=Decimal("0.0000"),
                tax_abs_tolerance=Decimal("1.0000"),
                allow_partial_billing=True,
                allow_service_advance_billing=False,
                version=1,
                is_active=True,
                updated_by="system_seed",
            )
        )

    vendor_defs = [
        ("Bharat Precision Components Pvt Ltd", "29AABCB1234F1Z5", "XXXX-4821"),
        ("Sahyadri Industrial Fasteners LLP", "27AADFS5678K1Z2", "XXXX-9104"),
        ("Deccan Packaging & Corrugates Ltd", "36AABCD9012M1Z9", "XXXX-3317"),
        ("Kaveri Polymers & Seals Pvt Ltd", "33AABCK3456P1Z4", "XXXX-7742"),
        ("Vindhya Electricals & Cables Ltd", "24AABCV7890R1Z1", "XXXX-5509"),
        ("Narmada Bearings & Hydraulics Pvt Ltd", "23AABCN2345T1Z8", "XXXX-6190"),
        ("Godavari Logistics & Freight Services", "36AABCG6789W1Z3", "XXXX-1488"),
        ("Aravalli Metals & Alloys Corp", "08AABCA4567Y1Z6", "XXXX-8235"),
    ]
    vendors: list[Vendor] = []
    for idx, (legal, gstin, bank) in enumerate(vendor_defs):
        v = Vendor(
            id=_det_uuid(f"vendor-{idx}"),
            organization_id=org.id,
            legal_name=legal,
            normalized_name=normalize_name(legal),
            tax_identifier=gstin,
            bank_account_masked=bank,
            status="ACTIVE",
        )
        db.merge(v)
        vendors.append(v)
    db.flush()

    base_date = date(2026, 9, 1)
    rng = random.Random(20260101)

    def _add_po_bundle(
        key: str,
        po_num: str,
        vendor: Vendor,
        issue_offset_days: int,
        item_code: str,
        desc: str,
        uom: str,
        po_qty: Decimal,
        po_price: Decimal,
        tax_rate: Decimal,
        grn_batches: list[tuple[str, Decimal, Decimal]],  # (grn_num, accepted, rejected)
        invoices_spec: list[
            tuple[str, Vendor, Decimal, Decimal, Decimal | None, str]
        ],  # (inv_num, inv_vendor, qty, price, tax_override, status)
        scenario_label: str,
        currency: str = "INR",
    ) -> None:
        po_id = _det_uuid(f"po-{key}")
        po_line_id = _det_uuid(f"poline-{key}-1")
        sub = _q(po_qty * po_price)
        tax = _q(sub * tax_rate)
        tot = _q(sub + tax)
        issue_dt = base_date + timedelta(days=issue_offset_days)

        po = PurchaseOrder(
            id=po_id,
            organization_id=org.id,
            vendor_id=vendor.id,
            po_number=po_num,
            issue_date=issue_dt,
            currency=currency,
            status="OPEN",
            subtotal_amount=sub,
            tax_amount=tax,
            discount_amount=Decimal("0.0000"),
            freight_amount=Decimal("0.0000"),
            total_amount=tot,
            scenario_label=scenario_label,
        )
        db.add(po)
        db.add(
            POLine(
                id=po_line_id,
                organization_id=org.id,
                po_id=po_id,
                line_number=1,
                item_code=item_code,
                description=desc,
                uom=uom,
                quantity=_q(po_qty),
                unit_price=_q(po_price),
                tax_rate=_q(tax_rate),
                tax_amount=tax,
                discount_amount=Decimal("0.0000"),
                line_total=tot,
            )
        )
        db.flush()

        for g_idx, (grn_num, acc_qty, rej_qty) in enumerate(grn_batches):
            grn_id = _det_uuid(f"grn-{key}-{g_idx}")
            rec_dt = datetime.combine(
                issue_dt + timedelta(days=5 + g_idx * 3), datetime.min.time(), tzinfo=UTC
            )
            db.add(
                GoodsReceipt(
                    id=grn_id,
                    organization_id=org.id,
                    vendor_id=vendor.id,
                    grn_number=grn_num,
                    po_id=po_id,
                    received_at=rec_dt,
                    status="ACCEPTED" if acc_qty > 0 else "REJECTED",
                    scenario_label=scenario_label,
                )
            )
            db.add(
                GRNLine(
                    id=_det_uuid(f"grnline-{key}-{g_idx}"),
                    organization_id=org.id,
                    grn_id=grn_id,
                    po_line_id=po_line_id,
                    item_code=item_code,
                    description=desc,
                    received_qty=_q(acc_qty + rej_qty),
                    accepted_qty=_q(acc_qty),
                    rejected_qty=_q(rej_qty),
                    uom=uom,
                )
            )

        for i_idx, (inv_num, inv_vendor, inv_qty, inv_price, tax_ovr, inv_status) in enumerate(
            invoices_spec
        ):
            inv_id = _det_uuid(f"inv-{key}-{i_idx}")
            inv_sub = _q(inv_qty * inv_price)
            inv_tax = _q(tax_ovr if tax_ovr is not None else inv_sub * tax_rate)
            inv_tot = _q(inv_sub + inv_tax)
            inv_dt = issue_dt + timedelta(days=10 + i_idx * 4)
            db.add(
                Invoice(
                    id=inv_id,
                    organization_id=org.id,
                    vendor_id=inv_vendor.id,
                    invoice_number=inv_num,
                    normalized_invoice_number=normalize_invoice_number(inv_num),
                    po_id=po_id,
                    invoice_date=inv_dt,
                    due_date=inv_dt + timedelta(days=30),
                    currency=currency,
                    subtotal_amount=inv_sub,
                    tax_amount=inv_tax,
                    discount_amount=Decimal("0.0000"),
                    freight_amount=Decimal("0.0000"),
                    total_amount=inv_tot,
                    status=inv_status,
                    scenario_label=scenario_label,
                )
            )
            db.add(
                InvoiceLine(
                    id=_det_uuid(f"invline-{key}-{i_idx}"),
                    organization_id=org.id,
                    invoice_id=inv_id,
                    po_line_id=po_line_id,
                    item_code=item_code,
                    description=desc,
                    uom=uom,
                    quantity=_q(inv_qty),
                    unit_price=_q(inv_price),
                    tax_rate=_q(tax_rate),
                    tax_amount=inv_tax,
                    discount_amount=Decimal("0.0000"),
                    line_total=inv_tot,
                )
            )

    # 1. Named Acceptance Scenarios (AT-01 .. AT-06 + edge scenarios)
    _add_po_bundle(
        key="at01",
        po_num="PO-2026-0001",
        vendor=vendors[0],
        issue_offset_days=0,
        item_code="CNC-SHAFT-12",
        desc="Precision CNC Steel Shaft 12mm",
        uom="EA",
        po_qty=Decimal("100"),
        po_price=Decimal("450.00"),
        tax_rate=Decimal("0.18"),
        grn_batches=[("GRN-2026-0001", Decimal("100"), Decimal("0"))],
        invoices_spec=[
            ("INV-BPC-1001", vendors[0], Decimal("100"), Decimal("450.00"), None, "PENDING")
        ],
        scenario_label="AT-01",
    )

    _add_po_bundle(
        key="at02",
        po_num="PO-2026-0002",
        vendor=vendors[1],
        issue_offset_days=1,
        item_code="HEX-BOLT-M10",
        desc="High Tensile Hex Bolt M10x50",
        uom="EA",
        po_qty=Decimal("100"),
        po_price=Decimal("120.00"),
        tax_rate=Decimal("0.18"),
        grn_batches=[("GRN-2026-0002", Decimal("90"), Decimal("0"))],
        invoices_spec=[
            ("INV-SIF-2001", vendors[1], Decimal("100"), Decimal("120.00"), None, "PENDING")
        ],
        scenario_label="AT-02",
    )

    _add_po_bundle(
        key="at03",
        po_num="PO-2026-0003",
        vendor=vendors[0],
        issue_offset_days=2,
        item_code="FLANGE-SS-40",
        desc="Stainless Steel Flange 40mm",
        uom="EA",
        po_qty=Decimal("100"),
        po_price=Decimal("800.00"),
        tax_rate=Decimal("0.18"),
        grn_batches=[
            ("GRN-2026-0003A", Decimal("60"), Decimal("0")),
            ("GRN-2026-0003B", Decimal("40"), Decimal("0")),
        ],
        invoices_spec=[
            ("INV-BPC-1003", vendors[0], Decimal("100"), Decimal("800.00"), None, "PENDING")
        ],
        scenario_label="AT-03",
    )

    _add_po_bundle(
        key="at04",
        po_num="PO-2026-0004",
        vendor=vendors[2],
        issue_offset_days=3,
        item_code="BOX-CORR-5PLY",
        desc="Heavy Duty 5-Ply Corrugated Box",
        uom="EA",
        po_qty=Decimal("200"),
        po_price=Decimal("100.00"),
        tax_rate=Decimal("0.12"),
        grn_batches=[("GRN-2026-0004", Decimal("200"), Decimal("0"))],
        invoices_spec=[
            ("INV-DPC-3001", vendors[2], Decimal("200"), Decimal("112.00"), None, "PENDING")
        ],
        scenario_label="AT-04",
    )

    # AT-05: Duplicate invoice number scenario (canonical + duplicate flagged for review)
    _add_po_bundle(
        key="at05-orig",
        po_num="PO-2026-0005",
        vendor=vendors[3],
        issue_offset_days=4,
        item_code="SEAL-VITON-25",
        desc="Viton O-Ring Seal 25mm",
        uom="EA",
        po_qty=Decimal("50"),
        po_price=Decimal("300.00"),
        tax_rate=Decimal("0.18"),
        grn_batches=[("GRN-2026-0005", Decimal("50"), Decimal("0"))],
        invoices_spec=[
            ("INV-KPS-4001", vendors[3], Decimal("50"), Decimal("300.00"), None, "PENDING")
        ],
        scenario_label="AT-05-ORIGINAL",
    )
    # Second PO referencing same vendor invoice number pattern via duplicate submission record
    dup_po_id = _det_uuid("po-at05-dup")
    dup_pol_id = _det_uuid("poline-at05-dup")
    db.add(
        PurchaseOrder(
            id=dup_po_id,
            organization_id=org.id,
            vendor_id=vendors[3].id,
            po_number="PO-2026-0005B",
            issue_date=base_date + timedelta(days=5),
            currency="INR",
            status="OPEN",
            subtotal_amount=Decimal("15000.0000"),
            tax_amount=Decimal("2700.0000"),
            discount_amount=Decimal("0.0000"),
            freight_amount=Decimal("0.0000"),
            total_amount=Decimal("17700.0000"),
            scenario_label="AT-05",
        )
    )
    db.add(
        POLine(
            id=dup_pol_id,
            organization_id=org.id,
            po_id=dup_po_id,
            line_number=1,
            item_code="SEAL-VITON-25",
            description="Viton O-Ring Seal 25mm",
            uom="EA",
            quantity=Decimal("50.0000"),
            unit_price=Decimal("300.0000"),
            tax_rate=Decimal("0.1800"),
            tax_amount=Decimal("2700.0000"),
            discount_amount=Decimal("0.0000"),
            line_total=Decimal("17700.0000"),
        )
    )
    db.flush()
    db.add(
        GoodsReceipt(
            id=_det_uuid("grn-at05-dup"),
            organization_id=org.id,
            vendor_id=vendors[3].id,
            grn_number="GRN-2026-0005B",
            po_id=dup_po_id,
            received_at=datetime.combine(
                base_date + timedelta(days=7), datetime.min.time(), tzinfo=UTC
            ),
            status="ACCEPTED",
            scenario_label="AT-05",
        )
    )
    db.add(
        GRNLine(
            id=_det_uuid("grnline-at05-dup"),
            organization_id=org.id,
            grn_id=_det_uuid("grn-at05-dup"),
            po_line_id=dup_pol_id,
            item_code="SEAL-VITON-25",
            description="Viton O-Ring Seal 25mm",
            received_qty=Decimal("50.0000"),
            accepted_qty=Decimal("50.0000"),
            rejected_qty=Decimal("0.0000"),
            uom="EA",
        )
    )
    dup_inv_id = _det_uuid("inv-at05-dup")
    db.add(
        Invoice(
            id=dup_inv_id,
            organization_id=org.id,
            vendor_id=vendors[3].id,
            invoice_number="INV-KPS-4001",
            normalized_invoice_number="INVKPS4001__DUP__1",
            po_id=dup_po_id,
            invoice_date=base_date + timedelta(days=9),
            due_date=base_date + timedelta(days=39),
            currency="INR",
            subtotal_amount=Decimal("15000.0000"),
            tax_amount=Decimal("2700.0000"),
            discount_amount=Decimal("0.0000"),
            freight_amount=Decimal("0.0000"),
            total_amount=Decimal("17700.0000"),
            status="REVIEW_REQUIRED",
            scenario_label="AT-05",
            duplicate_of_invoice_id=_det_uuid("inv-at05-orig-0"),
        )
    )
    db.add(
        InvoiceLine(
            id=_det_uuid("invline-at05-dup"),
            organization_id=org.id,
            invoice_id=dup_inv_id,
            po_line_id=dup_pol_id,
            item_code="SEAL-VITON-25",
            description="Viton O-Ring Seal 25mm",
            uom="EA",
            quantity=Decimal("50.0000"),
            unit_price=Decimal("300.0000"),
            tax_rate=Decimal("0.1800"),
            tax_amount=Decimal("2700.0000"),
            discount_amount=Decimal("0.0000"),
            line_total=Decimal("17700.0000"),
        )
    )

    # AT-06: Standalone invoice with no PO
    standalone_inv_id = _det_uuid("inv-at06")
    db.add(
        Invoice(
            id=standalone_inv_id,
            organization_id=org.id,
            vendor_id=vendors[4].id,
            invoice_number="INV-VEC-6001",
            normalized_invoice_number="INVVEC6001",
            po_id=None,
            invoice_date=base_date + timedelta(days=8),
            due_date=base_date + timedelta(days=38),
            currency="INR",
            subtotal_amount=Decimal("25000.0000"),
            tax_amount=Decimal("4500.0000"),
            discount_amount=Decimal("0.0000"),
            freight_amount=Decimal("0.0000"),
            total_amount=Decimal("29500.0000"),
            status="INCOMPLETE",
            scenario_label="AT-06",
        )
    )
    db.add(
        InvoiceLine(
            id=_det_uuid("invline-at06"),
            organization_id=org.id,
            invoice_id=standalone_inv_id,
            po_line_id=None,
            item_code="CABLE-ARM-16MM",
            description="Armoured Copper Cable 16sqmm",
            uom="MTR",
            quantity=Decimal("100.0000"),
            unit_price=Decimal("250.0000"),
            tax_rate=Decimal("0.1800"),
            tax_amount=Decimal("4500.0000"),
            discount_amount=Decimal("0.0000"),
            line_total=Decimal("29500.0000"),
        )
    )

    # Extra scenarios: SUPPLIER_MISMATCH, TAX_VARIANCE, SPLIT_INVOICE, REJECTED_QUANTITY, TOLERANCE
    _add_po_bundle(
        key="supplier-mismatch",
        po_num="PO-2026-0007",
        vendor=vendors[5],
        issue_offset_days=6,
        item_code="BRG-SKF-6205",
        desc="Deep Groove Ball Bearing 6205",
        uom="EA",
        po_qty=Decimal("40"),
        po_price=Decimal("650.00"),
        tax_rate=Decimal("0.18"),
        grn_batches=[("GRN-2026-0007", Decimal("40"), Decimal("0"))],
        invoices_spec=[
            ("INV-GLF-7001", vendors[6], Decimal("40"), Decimal("650.00"), None, "PENDING")
        ],
        scenario_label="SUPPLIER_MISMATCH",
    )

    _add_po_bundle(
        key="tax-variance",
        po_num="PO-2026-0008",
        vendor=vendors[7],
        issue_offset_days=7,
        item_code="AL-SHEET-3MM",
        desc="Aluminium Alloy Sheet 3mm",
        uom="KG",
        po_qty=Decimal("150"),
        po_price=Decimal("320.00"),
        tax_rate=Decimal("0.18"),
        grn_batches=[("GRN-2026-0008", Decimal("150"), Decimal("0"))],
        invoices_spec=[
            (
                "INV-AMA-8001",
                vendors[7],
                Decimal("150"),
                Decimal("320.00"),
                Decimal("11520.00"),  # Wrong GST charged (24% instead of 18%)
                "PENDING",
            )
        ],
        scenario_label="TAX_VARIANCE",
    )

    _add_po_bundle(
        key="split-invoice",
        po_num="PO-2026-0009",
        vendor=vendors[0],
        issue_offset_days=8,
        item_code="VALVE-SS-50",
        desc="Stainless Control Valve 50mm",
        uom="EA",
        po_qty=Decimal("20"),
        po_price=Decimal("2500.00"),
        tax_rate=Decimal("0.18"),
        grn_batches=[("GRN-2026-0009", Decimal("20"), Decimal("0"))],
        invoices_spec=[
            ("INV-BPC-9001A", vendors[0], Decimal("12"), Decimal("2500.00"), None, "PENDING"),
            ("INV-BPC-9001B", vendors[0], Decimal("8"), Decimal("2500.00"), None, "PENDING"),
        ],
        scenario_label="SPLIT_INVOICE",
    )

    _add_po_bundle(
        key="rejected-qty",
        po_num="PO-2026-0010",
        vendor=vendors[1],
        issue_offset_days=9,
        item_code="NUT-LOCK-M12",
        desc="Nylock Nut M12 Stainless",
        uom="EA",
        po_qty=Decimal("500"),
        po_price=Decimal("25.00"),
        tax_rate=Decimal("0.18"),
        grn_batches=[("GRN-2026-0010", Decimal("420"), Decimal("80"))],
        invoices_spec=[
            ("INV-SIF-1010", vendors[1], Decimal("500"), Decimal("25.00"), None, "PENDING")
        ],
        scenario_label="REJECTED_QUANTITY",
    )

    _add_po_bundle(
        key="tolerance-pass",
        po_num="PO-2026-0011",
        vendor=vendors[2],
        issue_offset_days=10,
        item_code="TAPE-PKG-48",
        desc="BOPP Industrial Packing Tape 48mm",
        uom="ROLL",
        po_qty=Decimal("100"),
        po_price=Decimal("100.00"),
        tax_rate=Decimal("0.18"),
        grn_batches=[("GRN-2026-0011", Decimal("100"), Decimal("0"))],
        invoices_spec=[
            ("INV-DPC-1101", vendors[2], Decimal("100"), Decimal("101.50"), None, "PENDING")
        ],
        scenario_label="TOLERANCE_PASS",
    )

    # Generate remaining ~29 synthetic transactions to reach ~40 transactions total
    catalog = [
        ("BRKT-MS-04", "Mild Steel Mounting Bracket", "EA", Decimal("210.00")),
        ("GSKT-EPDM-80", "EPDM Flange Gasket 80mm", "EA", Decimal("95.00")),
        ("MOTOR-IE2-2HP", "3-Phase Induction Motor 2HP", "EA", Decimal("14500.00")),
        ("SENSOR-IND-M12", "Inductive Proximity Sensor M12", "EA", Decimal("1250.00")),
        ("HOSE-HYD-1M", "Braided Hydraulic Hose 1m", "EA", Decimal("890.00")),
        ("OIL-GEAR-20L", "Synthetic Gear Oil 20L Drum", "DRUM", Decimal("4800.00")),
    ]
    for idx in range(12, 41):
        vendor = vendors[rng.randrange(len(vendors))]
        item_code, desc, uom, base_price = catalog[rng.randrange(len(catalog))]
        qty = Decimal(str(rng.choice([10, 20, 25, 50, 75, 100])))
        # Deterministic mix of exact, partial GRN, missing GRN, or slight price variance
        variant = idx % 5
        grns = [(f"GRN-2026-{idx:04d}", qty, Decimal("0"))]
        inv_qty = qty
        inv_price = base_price
        if variant == 1:
            grns = [
                (f"GRN-2026-{idx:04d}A", qty * Decimal("0.5"), Decimal("0")),
                (f"GRN-2026-{idx:04d}B", qty * Decimal("0.5"), Decimal("0")),
            ]
        elif variant == 2:
            # Price variance slightly above 2%
            inv_price = _q(base_price * Decimal("1.04"))
        elif variant == 3:
            # Missing GRN (incomplete)
            grns = []

        _add_po_bundle(
            key=f"syn-{idx}",
            po_num=f"PO-2026-{idx:04d}",
            vendor=vendor,
            issue_offset_days=idx % 28,
            item_code=item_code,
            desc=desc,
            uom=uom,
            po_qty=qty,
            po_price=base_price,
            tax_rate=Decimal("0.18"),
            grn_batches=grns,
            invoices_spec=[
                (
                    f"INV-SYN-{idx:04d}",
                    vendor,
                    inv_qty,
                    inv_price,
                    None,
                    "PENDING",
                )
            ],
            scenario_label=f"SYNTHETIC-{idx:02d}",
        )

    db.commit()

    # Compute deterministic checksum of seeded PO + GRN + Invoice totals for verification
    from app.models.policy import Policy
    from app.services.policies.engine import activate_policy, create_policy

    if not db.scalar(
        select(Policy).where(Policy.organization_id == org.id, Policy.policy_key == "POL-SYS-DUP")
    ):
        p1, _ = create_policy(
            db,
            organization_id=org.id,
            actor_id="system_seed",
            policy_key="POL-SYS-DUP",
            name="Duplicate Invoice Review Gate",
            description=(
                "Flags transactions where an invoice matches an existing duplicate fingerprint."
            ),
            category="DUPLICATE",
            severity="CRITICAL",
            is_system_policy=True,
            definition_dict={
                "scope": {"document_types": ["INVOICE"]},
                "condition": {
                    "field": "invoice.is_duplicate",
                    "operator": "eq",
                    "value": True,
                },
                "action": {
                    "type": "CREATE_EXCEPTION",
                    "exception_type": "POLICY_DUPLICATE_GATE",
                    "instructions": "Verify invoice uniqueness before approval.",
                },
            },
            change_summary="Seeded system duplicate policy",
        )
        activate_policy(db, organization_id=org.id, policy_id=p1.id, actor_id="system_seed")

    if not db.scalar(
        select(Policy).where(
            Policy.organization_id == org.id, Policy.policy_key == "POL-CUSTOM-QTY"
        )
    ):
        create_policy(
            db,
            organization_id=org.id,
            actor_id="system_seed",
            policy_key="POL-CUSTOM-QTY",
            name="Critical Quantity Variance (>5 EA)",
            description="Flags invoices exceeding accepted GRN quantity by more than 5 units.",
            category="FINANCIAL",
            severity="HIGH",
            definition_dict={
                "scope": {"document_types": ["PURCHASE_ORDER", "GOODS_RECEIPT", "INVOICE"]},
                "condition": {
                    "field": "variance.qty_diff",
                    "operator": "gt",
                    "value": "5",
                },
                "action": {
                    "type": "CREATE_EXCEPTION",
                    "exception_type": "POLICY_QTY_VARIANCE",
                    "instructions": "Confirm short-receipt or credit note with warehouse.",
                },
            },
            change_summary="Seeded draft policy for Donut Challenge 1 demo",
        )

    po_rows = list(
        db.scalars(
            select(PurchaseOrder)
            .where(PurchaseOrder.organization_id == org.id)
            .order_by(PurchaseOrder.po_number)
        ).all()
    )
    if seed_baseline_reconciliation:
        from app.services.reconciliation_adapter import execute_reconciliation

        first_po = po_rows[0] if po_rows else None
        seed_uploader = db.scalar(
            select(User).where(User.organization_id == org.id).limit(1)
        )
        if first_po and seed_uploader:
            for d_idx, (fname, dtype) in enumerate(
                [
                    (f"{first_po.po_number}.pdf", "PO"),
                    ("GRN-2026-0001.pdf", "GRN"),
                    ("INV-BPC-1001.pdf", "INVOICE"),
                ]
            ):
                doc_id = _det_uuid(f"seed-doc-{d_idx}")
                if not db.get(Document, doc_id):
                    db.add(
                        Document(
                            id=doc_id,
                            organization_id=org.id,
                            uploaded_by=seed_uploader.id,
                            file_name=fname,
                            mime_type="application/pdf",
                            file_size_bytes=12400 + d_idx * 350,
                            checksum=hashlib.sha256(fname.encode("utf-8")).hexdigest(),
                            storage_key=f"seed/{fname}",
                            document_type=dtype,
                            classification_confidence=Decimal("0.9800"),
                            status="VERIFIED",
                            transaction_id=first_po.id,
                        )
                    )
            db.flush()

        for po_row in po_rows[:20]:
            execute_reconciliation(
                db,
                organization_id=org.id,
                transaction_id=po_row.id,
                actor_type="SYSTEM",
                actor_id="seed_baseline",
            )
        from app.services.neo4j.backfill import backfill_organization_graph

        backfill_organization_graph(db, organization_id=org.id)
    inv_rows = list(
        db.scalars(
            select(Invoice)
            .where(Invoice.organization_id == org.id)
            .order_by(Invoice.invoice_number, Invoice.normalized_invoice_number)
        ).all()
    )
    digest_src = "|".join(
        [f"{p.po_number}:{p.total_amount}" for p in po_rows]
        + [f"{i.invoice_number}:{i.normalized_invoice_number}:{i.total_amount}" for i in inv_rows]
    )
    checksum = hashlib.sha256(digest_src.encode("utf-8")).hexdigest()
    return {
        "organization_id": str(org.id),
        "vendors": len(vendors),
        "purchase_orders": len(po_rows),
        "invoices": len(inv_rows),
        "checksum": checksum,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed synthetic ReconX AI dataset")
    parser.add_argument("--reset", action="store_true", help="Reset domain records before seeding")
    parser.add_argument(
        "--no-baseline",
        action="store_true",
        help="Skip baseline reconciliation & sample documents",
    )
    args = parser.parse_args()

    if str(engine.url).startswith("sqlite"):
        Base.metadata.create_all(bind=engine)
        ensure_sqlite_audit_triggers(engine)

    with SessionLocal() as db:
        summary = seed_synthetic_dataset(
            db,
            reset=args.reset,
            seed_baseline_reconciliation=not args.no_baseline,
        )
        print(f"Seed complete: {summary}")


if __name__ == "__main__":
    main()
