from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.auth import Organization
from app.models.domain import Invoice, InvoiceLine, PurchaseOrder, Vendor
from scripts.seed import seed_synthetic_dataset


def _login_headers(client: TestClient, email: str) -> dict[str, str]:
    settings = get_settings()
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": settings.seed_default_password},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_duplicate_invoice_constraint_enforced(test_db_session: Session) -> None:
    org = test_db_session.query(Organization).first()
    assert org is not None
    vendor = Vendor(
        organization_id=org.id,
        legal_name="Constraint Vendor Ltd",
        normalized_name="constraintvendorltd",
        tax_identifier="29AAAAA0000A1Z5",
        bank_account_masked="XXXX-1111",
    )
    test_db_session.add(vendor)
    test_db_session.flush()

    inv1 = Invoice(
        organization_id=org.id,
        vendor_id=vendor.id,
        invoice_number="INV-900",
        normalized_invoice_number="INV900",
        invoice_date=date(2026, 9, 10),
        due_date=date(2026, 10, 10),
        currency="INR",
        subtotal_amount=Decimal("100.0000"),
        tax_amount=Decimal("18.0000"),
        total_amount=Decimal("118.0000"),
    )
    inv2 = Invoice(
        organization_id=org.id,
        vendor_id=vendor.id,
        invoice_number="inv 900",
        normalized_invoice_number="INV900",
        invoice_date=date(2026, 9, 11),
        due_date=date(2026, 10, 11),
        currency="INR",
        subtotal_amount=Decimal("100.0000"),
        tax_amount=Decimal("18.0000"),
        total_amount=Decimal("118.0000"),
    )
    test_db_session.add(inv1)
    test_db_session.commit()

    test_db_session.add(inv2)
    with pytest.raises(IntegrityError):
        test_db_session.commit()
    test_db_session.rollback()


def test_seed_determinism_and_named_scenarios(test_db_session: Session) -> None:
    s1 = seed_synthetic_dataset(test_db_session, reset=True)
    s2 = seed_synthetic_dataset(test_db_session, reset=True)
    assert s1["checksum"] == s2["checksum"]
    assert s1["vendors"] == 8
    assert s1["purchase_orders"] >= 39
    assert s1["invoices"] >= 40

    labels = {
        row[0]
        for row in test_db_session.query(PurchaseOrder.scenario_label)
        .filter(PurchaseOrder.scenario_label.isnot(None))
        .all()
    }
    inv_labels = {
        row[0]
        for row in test_db_session.query(Invoice.scenario_label)
        .filter(Invoice.scenario_label.isnot(None))
        .all()
    }
    all_labels = labels | inv_labels
    for expected in [
        "AT-01",
        "AT-02",
        "AT-03",
        "AT-04",
        "AT-05",
        "AT-06",
        "SUPPLIER_MISMATCH",
        "TAX_VARIANCE",
        "SPLIT_INVOICE",
        "REJECTED_QUANTITY",
    ]:
        assert expected in all_labels


def test_transaction_bundle_and_org_scoping(
    client: TestClient, test_db_session: Session
) -> None:
    seed_synthetic_dataset(test_db_session, reset=True)
    headers = _login_headers(client, "operator@reconx-demo.com")

    tx_list = client.get("/api/v1/transactions?scenario_label=AT-03", headers=headers)
    assert tx_list.status_code == 200
    items = tx_list.json()["items"]
    assert len(items) == 1
    tx_id = items[0]["transaction_id"]

    bundle = client.get(f"/api/v1/transactions/{tx_id}", headers=headers)
    assert bundle.status_code == 200
    data = bundle.json()
    assert data["purchase_order"]["po_number"] == "PO-2026-0003"
    assert len(data["goods_receipts"]) == 2
    assert len(data["invoices"]) == 1

    # Org isolation: another org cannot fetch this transaction bundle
    other_org = Organization(
        name="Isolated Org", base_currency="USD", timezone="UTC", settings_json={}
    )
    test_db_session.add(other_org)
    test_db_session.flush()
    other_vendor = Vendor(
        organization_id=other_org.id,
        legal_name="Foreign Vendor",
        normalized_name="foreignvendor",
    )
    test_db_session.add(other_vendor)
    test_db_session.flush()
    other_inv = Invoice(
        organization_id=other_org.id,
        vendor_id=other_vendor.id,
        invoice_number="FOR-1",
        normalized_invoice_number="FOR1",
        invoice_date=date(2026, 9, 1),
        due_date=date(2026, 10, 1),
        currency="USD",
        subtotal_amount=Decimal("10.0000"),
        tax_amount=Decimal("0.0000"),
        total_amount=Decimal("10.0000"),
        lines=[
            InvoiceLine(
                organization_id=other_org.id,
                description="Item",
                uom="EA",
                quantity=Decimal("1.0000"),
                unit_price=Decimal("10.0000"),
                line_total=Decimal("10.0000"),
            )
        ],
    )
    test_db_session.add(other_inv)
    test_db_session.commit()

    # Org 1 user requesting Org 2 invoice transaction_id gets 404
    not_found = client.get(f"/api/v1/transactions/{other_inv.id}", headers=headers)
    assert not_found.status_code == 404

    # Creating tolerance config via admin works and audits
    admin_headers = _login_headers(client, "admin@reconx-demo.com")
    tol_resp = client.post(
        "/api/v1/admin/tolerances",
        headers=admin_headers,
        json={
            "price_abs_tolerance": "5.00",
            "price_pct_tolerance": "0.03",
            "qty_abs_tolerance": "0",
            "qty_pct_tolerance": "0",
            "tax_abs_tolerance": "1.00",
            "allow_partial_billing": True,
        },
    )
    assert tol_resp.status_code == 201
    assert tol_resp.json()["version"] == 2
