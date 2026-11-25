from datetime import date, timedelta
from decimal import Decimal
from statistics import median
from typing import Any
from uuid import UUID

import numpy as np
from rapidfuzz import fuzz
from sklearn.ensemble import IsolationForest
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.domain import (
    ExceptionCase,
    GoodsReceipt,
    Invoice,
    PurchaseOrder,
    ReconciliationRun,
    RiskSignal,
    Vendor,
    VendorBankChange,
)
from app.repositories.base import OrgScopedRepository

DISCLAIMER = "Risk indicator for human review, not proof of fraud."


def compute_vendor_profile(
    db: Session,
    *,
    organization_id: UUID,
    vendor_id: UUID,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict[str, Any]:
    vendor = OrgScopedRepository(db, Vendor, organization_id).get_by_id(vendor_id)
    if not vendor:
        return {}

    po_stmt = OrgScopedRepository(db, PurchaseOrder, organization_id).base_query().where(
        PurchaseOrder.vendor_id == vendor_id
    )
    inv_stmt = OrgScopedRepository(db, Invoice, organization_id).base_query().where(
        Invoice.vendor_id == vendor_id
    )
    grn_stmt = OrgScopedRepository(db, GoodsReceipt, organization_id).base_query().where(
        GoodsReceipt.vendor_id == vendor_id
    )
    if date_from:
        po_stmt = po_stmt.where(PurchaseOrder.issue_date >= date_from)
        inv_stmt = inv_stmt.where(Invoice.invoice_date >= date_from)
    if date_to:
        po_stmt = po_stmt.where(PurchaseOrder.issue_date <= date_to)
        inv_stmt = inv_stmt.where(Invoice.invoice_date <= date_to)

    pos = list(db.scalars(po_stmt).all())
    invs = list(db.scalars(inv_stmt).all())
    grns = list(db.scalars(grn_stmt).all())

    tx_ids = {p.id for p in pos} | {i.id for i in invs if i.po_id is None}
    runs = (
        list(
            db.scalars(
                OrgScopedRepository(db, ReconciliationRun, organization_id)
                .base_query()
                .where(ReconciliationRun.transaction_id.in_(list(tx_ids)))
            ).all()
        )
        if tx_ids
        else []
    )
    excs = (
        list(
            db.scalars(
                OrgScopedRepository(db, ExceptionCase, organization_id)
                .base_query()
                .where(ExceptionCase.transaction_id.in_(list(tx_ids)))
            ).all()
        )
        if tx_ids
        else []
    )

    sample_n = len(tx_ids)
    exception_txs = {e.transaction_id for e in excs}
    mismatch_rate = round(len(exception_txs) / sample_n, 4) if sample_n > 0 else 0.0

    # Delivery timeliness: average days between PO issue_date and GRN received_at
    po_map = {p.id: p for p in pos}
    lead_days: list[int] = []
    for g in grns:
        if g.po_id and g.po_id in po_map:
            delta = (g.received_at.date() - po_map[g.po_id].issue_date).days
            lead_days.append(max(0, delta))
    avg_lead_days = round(sum(lead_days) / len(lead_days), 2) if lead_days else None
    on_time_rate = (
        round(sum(1 for d in lead_days if d <= 14) / len(lead_days), 4) if lead_days else None
    )
    price_variance_count = sum(1 for e in excs if e.rule_id == "R-PRC-01")

    bank_changes = list(
        db.scalars(
            OrgScopedRepository(db, VendorBankChange, organization_id)
            .base_query()
            .where(VendorBankChange.vendor_id == vendor_id)
            .order_by(desc(VendorBankChange.created_at))
        ).all()
    )

    all_dates = [p.issue_date for p in pos] + [i.invoice_date for i in invs]
    period_start = str(date_from or (min(all_dates) if all_dates else date.today()))
    period_end = str(date_to or (max(all_dates) if all_dates else date.today()))

    # FR-VEN-04: avoid presenting an objective/definitive reliability score when N is small
    small_sample = sample_n < 5
    reliability_indicator: float | None = None
    if not small_sample:
        reliability_indicator = round(max(0.0, 1.0 - mismatch_rate), 4)

    return {
        "vendor_id": str(vendor.id),
        "legal_name": vendor.legal_name,
        "tax_identifier": vendor.tax_identifier,
        "bank_account_masked": vendor.bank_account_masked,
        "status": vendor.status,
        "date_range": {"from": period_start, "to": period_end},
        "transaction_count": sample_n,
        "reconciliation_runs_count": len(runs),
        "mismatch_rate": mismatch_rate,
        "dispute_count": len(excs),
        "price_variance_count": price_variance_count,
        "avg_delivery_days": avg_lead_days,
        "on_time_delivery_rate": on_time_rate,
        "reliability_indicator": reliability_indicator,
        "small_sample_warning": (
            f"Sample size N={sample_n} is small (<5); no definitive vendor score computed."
            if small_sample
            else None
        ),
        "pending_bank_verifications": sum(
            1 for bc in bank_changes if bc.verification_status == "ENHANCED_VERIFICATION_REQUIRED"
        ),
        "dispute_history": [
            {
                "case_id": str(e.id),
                "transaction_id": str(e.transaction_id),
                "type": e.type,
                "severity": e.severity,
                "status": e.status,
                "created_at": e.created_at.isoformat(),
            }
            for e in excs[:20]
        ],
    }


def evaluate_transaction_risk(
    db: Session,
    *,
    organization_id: UUID,
    transaction_id: UUID,
    persist: bool = True,
) -> list[dict[str, Any]]:
    """Compute explainable deterministic risk indicators (and optional ML score)."""
    po = OrgScopedRepository(db, PurchaseOrder, organization_id).get_by_id(transaction_id)
    inv_repo = OrgScopedRepository(db, Invoice, organization_id)
    if po is not None:
        invoices = list(db.scalars(inv_repo.base_query().where(Invoice.po_id == po.id)).all())
        vendor_id = po.vendor_id
    else:
        single_inv = inv_repo.get_by_id(transaction_id)
        if not single_inv:
            return []
        invoices = [single_inv]
        vendor_id = single_inv.vendor_id

    all_org_invs = list(db.scalars(inv_repo.base_query()).all())
    signals: list[dict[str, Any]] = []

    # 1. Near-duplicate detection (SRS 6.6: review signal, never auto-reject)
    for inv in invoices:
        for other in all_org_invs:
            if other.id == inv.id:
                continue
            if other.vendor_id != inv.vendor_id:
                continue
            amt_diff = abs(other.total_amount - inv.total_amount)
            amt_close = (
                amt_diff <= max(Decimal("5.00"), inv.total_amount * Decimal("0.01"))
                if inv.total_amount > 0
                else False
            )
            days_apart = abs((other.invoice_date - inv.invoice_date).days)
            num_sim = (
                fuzz.ratio(other.normalized_invoice_number, inv.normalized_invoice_number) / 100.0
            )
            score = 0.0
            reasons: list[str] = []
            if (
                other.invoice_number == inv.invoice_number
                or inv.duplicate_of_invoice_id == other.id
            ):
                score = 0.95
                reasons.append("EXACT_DUPLICATE_INVOICE_NUMBER")
            elif amt_close and days_apart <= 7 and num_sim >= 0.70:
                score = round(0.45 + 0.30 * num_sim + 0.20, 4)
                reasons.extend(["NEAR_DUPLICATE_AMOUNT_DATE", "INVOICE_NUMBER_SIMILARITY"])
            if reasons:
                signals.append(
                    {
                        "signal_type": "EXACT_DUPLICATE_INVOICE"
                        if "EXACT_DUPLICATE_INVOICE_NUMBER" in reasons
                        else "NEAR_DUPLICATE_INVOICE",
                        "severity": "HIGH" if score >= 0.85 else "MEDIUM",
                        "score": Decimal(str(round(min(1.0, score), 4))),
                        "reason_json": {
                            "reason_codes": reasons,
                            "contributing_signals": [
                                f"Compared {inv.invoice_number} with {other.invoice_number} "
                                f"(days apart: {days_apart}, amount diff: {amt_diff})"
                            ],
                            "limited_confidence": False,
                            "disclaimer": DISCLAIMER,
                        },
                        "model_version": "rules-v1",
                    }
                )

    # 2. Price deviation vs historical prices using median + MAD (robust z-score)
    for inv in invoices:
        for il in inv.lines:
            hist_prices = [
                float(other_line.unit_price)
                for other_inv in all_org_invs
                if other_inv.id != inv.id and other_inv.vendor_id == vendor_id
                for other_line in other_inv.lines
                if other_line.item_code and other_line.item_code == il.item_code
            ]
            if len(hist_prices) >= 3:
                med = median(hist_prices)
                deviations = [abs(p - med) for p in hist_prices]
                mad = median(deviations) or max(1.0, med * 0.02)
                robust_z = abs(float(il.unit_price) - med) / (1.4826 * mad)
                if robust_z >= 3.0:
                    signals.append(
                        {
                            "signal_type": "HISTORICAL_PRICE_DEVIATION",
                            "severity": "HIGH" if robust_z >= 5.0 else "MEDIUM",
                            "score": Decimal(str(round(min(0.99, robust_z / 10.0), 4))),
                            "reason_json": {
                                "reason_codes": ["ROBUST_ZSCORE_PRICE_SPIKE"],
                                "contributing_signals": [
                                    f"Item {il.item_code} unit_price {il.unit_price} vs "
                                    f"median {round(med, 2)} (N={len(hist_prices)}, "
                                    f"z={round(robust_z, 2)})"
                                ],
                                "limited_confidence": False,
                                "disclaimer": DISCLAIMER,
                            },
                            "model_version": "mad-zscore-v1",
                        }
                    )

    # 3. Vendor pattern signals (repeated mismatches or pending bank change)
    vendor_excs = list(
        db.scalars(
            OrgScopedRepository(db, ExceptionCase, organization_id)
            .base_query()
            .where(ExceptionCase.transaction_id != transaction_id)
        ).all()
    )
    vendor_pos = {
        p.id
        for p in db.scalars(
            OrgScopedRepository(db, PurchaseOrder, organization_id)
            .base_query()
            .where(PurchaseOrder.vendor_id == vendor_id)
        ).all()
    }
    prior_vendor_excs = [e for e in vendor_excs if e.transaction_id in vendor_pos]
    if len(prior_vendor_excs) >= 3:
        signals.append(
            {
                "signal_type": "REPEATED_VENDOR_MISMATCHES",
                "severity": "MEDIUM",
                "score": Decimal("0.6500"),
                "reason_json": {
                    "reason_codes": ["REPEATED_MISMATCH_HISTORY"],
                    "contributing_signals": [
                        f"Vendor has {len(prior_vendor_excs)} historical exception cases."
                    ],
                    "limited_confidence": False,
                    "disclaimer": DISCLAIMER,
                },
                "model_version": "rules-v1",
            }
        )

    pending_bank = list(
        db.scalars(
            OrgScopedRepository(db, VendorBankChange, organization_id)
            .base_query()
            .where(
                VendorBankChange.vendor_id == vendor_id,
                VendorBankChange.verification_status == "ENHANCED_VERIFICATION_REQUIRED",
            )
        ).all()
    )
    if pending_bank:
        signals.append(
            {
                "signal_type": "BANK_DETAIL_CHANGE",
                "severity": "HIGH",
                "score": Decimal("0.9000"),
                "reason_json": {
                    "reason_codes": ["UNVERIFIED_BANK_DETAIL_CHANGE"],
                    "contributing_signals": [
                        "Vendor has an unverified bank-detail change requiring enhanced review."
                    ],
                    "limited_confidence": False,
                    "disclaimer": DISCLAIMER,
                },
                "model_version": "rules-v1",
            }
        )

    # 3b. Split-invoice pattern detection (multiple invoices in 7-day window)
    if invoices:
        anchor_inv = invoices[0]
        window_start = anchor_inv.invoice_date - timedelta(days=7)
        window_end = anchor_inv.invoice_date + timedelta(days=7)
        nearby_vendor_invs = [
            i
            for i in all_org_invs
            if i.vendor_id == vendor_id and window_start <= i.invoice_date <= window_end
        ]
        same_po_invs = (
            [i for i in nearby_vendor_invs if i.po_id == po.id] if po is not None else []
        )
        if po is not None and len(same_po_invs) >= 2:
            combined = sum((i.total_amount for i in same_po_invs), Decimal("0"))
            if po.total_amount > 0 and combined >= po.total_amount * Decimal("0.90"):
                signals.append(
                    {
                        "signal_type": "SPLIT_INVOICE_PATTERN",
                        "severity": "MEDIUM",
                        "score": Decimal("0.7200"),
                        "reason_json": {
                            "reason_codes": ["SPLIT_INVOICE_SAME_PO_WINDOW"],
                            "contributing_signals": [
                                f"{len(same_po_invs)} invoices against {po.po_number} "
                                f"within 7 days (combined={combined} vs PO={po.total_amount})."
                            ],
                            "limited_confidence": False,
                            "disclaimer": DISCLAIMER,
                        },
                        "model_version": "rules-v2",
                    }
                )
        elif len(nearby_vendor_invs) >= 4:
            signals.append(
                {
                    "signal_type": "ABNORMAL_INVOICE_FREQUENCY",
                    "severity": "MEDIUM",
                    "score": Decimal("0.6800"),
                    "reason_json": {
                        "reason_codes": ["HIGH_SHORT_WINDOW_INVOICE_FREQUENCY"],
                        "contributing_signals": [
                            f"Vendor submitted {len(nearby_vendor_invs)} invoices within +/-7 days."
                        ],
                        "limited_confidence": False,
                        "disclaimer": DISCLAIMER,
                    },
                    "model_version": "rules-v2",
                }
            )

    # 3c. Relationship anomaly: shared bank account across distinct vendors in org
    current_vendor = OrgScopedRepository(db, Vendor, organization_id).get_by_id(vendor_id)
    if current_vendor and current_vendor.bank_account_masked:
        shared_vendors = [
            v
            for v in db.scalars(
                OrgScopedRepository(db, Vendor, organization_id)
                .base_query()
                .where(
                    Vendor.id != vendor_id,
                    Vendor.bank_account_masked == current_vendor.bank_account_masked,
                )
            ).all()
        ]
        if shared_vendors:
            names = ", ".join(v.legal_name for v in shared_vendors[:3])
            signals.append(
                {
                    "signal_type": "SHARED_BANK_ACCOUNT",
                    "severity": "HIGH",
                    "score": Decimal("0.8800"),
                    "reason_json": {
                        "reason_codes": ["CROSS_VENDOR_SHARED_BANK_ACCOUNT"],
                        "contributing_signals": [
                            f"Masked bank account {current_vendor.bank_account_masked} "
                            f"shared with distinct vendor(s): {names}."
                        ],
                        "limited_confidence": False,
                        "disclaimer": DISCLAIMER,
                    },
                    "model_version": "graph-rel-v1",
                }
            )

    # 4. Optional IsolationForest anomaly check (FR-RISK-07: fallback/limited when thin)
    settings = get_settings()
    if settings.feature_anomaly_ml and invoices:
        if len(all_org_invs) >= 15:
            features = np.array(
                [
                    [float(i.total_amount), float(i.tax_amount), float(len(i.lines))]
                    for i in all_org_invs
                ]
            )
            iso = IsolationForest(contamination=0.1, random_state=42)
            iso.fit(features)
            for inv in invoices:
                feat = [[float(inv.total_amount), float(inv.tax_amount), float(len(inv.lines))]]
                pred = iso.predict(feat)[0]
                if pred == -1:
                    signals.append(
                        {
                            "signal_type": "ML_ANOMALY_OUTLIER",
                            "severity": "LOW",
                            "score": Decimal("0.5500"),
                            "reason_json": {
                                "reason_codes": ["ISOLATION_FOREST_OUTLIER"],
                                "contributing_signals": [
                                    f"Outlier across N={len(all_org_invs)} org invoices."
                                ],
                                "limited_confidence": len(all_org_invs) < 30,
                                "disclaimer": DISCLAIMER,
                            },
                            "model_version": "isoforest-v1",
                        }
                    )

    if persist:
        # Refresh persisted risk signals for this transaction cleanly
        existing = list(
            db.scalars(
                OrgScopedRepository(db, RiskSignal, organization_id)
                .base_query()
                .where(RiskSignal.transaction_id == transaction_id)
            ).all()
        )
        for old in existing:
            db.delete(old)
        db.flush()
        for sig in signals:
            db.add(
                RiskSignal(
                    organization_id=organization_id,
                    transaction_id=transaction_id,
                    signal_type=sig["signal_type"],
                    severity=sig["severity"],
                    score=sig["score"],
                    reason_json=sig["reason_json"],
                    model_version=sig["model_version"],
                )
            )
        db.commit()

    return [
        {
            "signal_type": s["signal_type"],
            "severity": s["severity"],
            "score": str(s["score"]),
            "reason": s["reason_json"],
            "model_version": s["model_version"],
            "label": DISCLAIMER,
        }
        for s in signals
    ]
