from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.auth import Organization
from app.models.domain import (
    Approval,
    Document,
    ExceptionCase,
    GoodsReceipt,
    Investigation,
    Invoice,
    PurchaseOrder,
    ReconciliationRun,
    RiskSignal,
    Vendor,
)
from app.models.policy import GraphOutboxEvent, Policy, PolicyEvaluation, PolicyVersion
from app.repositories.base import OrgScopedRepository
from app.services.neo4j.repository import run_write


def _gkey(org_id: UUID | str, entity_type: str, source_id: UUID | str) -> str:
    return f"{org_id}:{entity_type}:{source_id}"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def enqueue_graph_event(
    db: Session,
    *,
    organization_id: UUID,
    event_type: str,
    entity_type: str,
    entity_id: str | UUID,
    payload: dict[str, Any] | None = None,
) -> GraphOutboxEvent | None:
    """Record a graph sync outbox event inside the caller's PostgreSQL transaction."""
    if not get_settings().graph_sync_enabled:
        return None
    evt = GraphOutboxEvent(
        organization_id=organization_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=str(entity_id),
        payload_json=payload or {},
        status="PENDING",
        attempts=0,
    )
    db.add(evt)
    db.flush()
    return evt


def sync_transaction_to_neo4j(
    db: Session,
    *,
    organization_id: UUID,
    transaction_id: UUID,
) -> bool:
    """Idempotently project a transaction bundle and its governance records into Neo4j."""
    org = db.get(Organization, organization_id)
    org_name = org.name if org else "Organization"
    org_id_str = str(organization_id)
    synced_at = _now_iso()

    po = OrgScopedRepository(db, PurchaseOrder, organization_id).get_by_id(transaction_id)
    inv_repo = OrgScopedRepository(db, Invoice, organization_id)
    grn_repo = OrgScopedRepository(db, GoodsReceipt, organization_id)

    if po is not None:
        vendor = OrgScopedRepository(db, Vendor, organization_id).get_by_id(po.vendor_id)
        grns = list(db.scalars(grn_repo.base_query().where(GoodsReceipt.po_id == po.id)).all())
        invoices = list(db.scalars(inv_repo.base_query().where(Invoice.po_id == po.id)).all())
    else:
        single_inv = inv_repo.get_by_id(transaction_id)
        if not single_inv:
            return False
        vendor = OrgScopedRepository(db, Vendor, organization_id).get_by_id(single_inv.vendor_id)
        grns = []
        invoices = [single_inv]

    # Organization node
    run_write(
        """
        MERGE (o:Organization {graph_key: $gk})
        SET o.source_id = $org_id, o.organization_id = $org_id, o.entity_type = 'Organization',
            o.name = $name, o.source_system = 'postgresql', o.last_synced_at = $synced_at
        """,
        {"gk": _gkey(org_id_str, "Organization", org_id_str), "org_id": org_id_str, "name": org_name, "synced_at": synced_at},
    )

    if vendor:
        v_gk = _gkey(org_id_str, "Vendor", vendor.id)
        run_write(
            """
            MATCH (o:Organization {graph_key: $org_gk})
            MERGE (v:Vendor {graph_key: $v_gk})
            SET v.source_id = $vid, v.organization_id = $org_id, v.entity_type = 'Vendor',
                v.label = $name, v.tax_identifier = $tax_id, v.status = $status,
                v.source_system = 'postgresql', v.last_synced_at = $synced_at
            MERGE (o)-[:HAS_VENDOR]->(v)
            """,
            {
                "org_gk": _gkey(org_id_str, "Organization", org_id_str),
                "v_gk": v_gk,
                "vid": str(vendor.id),
                "org_id": org_id_str,
                "name": vendor.legal_name,
                "tax_id": vendor.tax_identifier or "",
                "status": vendor.status,
                "synced_at": synced_at,
            },
        )

    po_lines_by_code: dict[str, str] = {}
    po_lines_by_id: dict[str, str] = {}
    if po:
        po_gk = _gkey(org_id_str, "PurchaseOrder", po.id)
        run_write(
            """
            MERGE (p:PurchaseOrder {graph_key: $po_gk})
            SET p.source_id = $pid, p.organization_id = $org_id, p.entity_type = 'PurchaseOrder',
                p.label = $po_num, p.po_number = $po_num, p.total_amount = $total,
                p.currency = $currency, p.status = $status, p.issue_date = $issue_date,
                p.source_system = 'postgresql', p.last_synced_at = $synced_at
            """,
            {
                "po_gk": po_gk,
                "pid": str(po.id),
                "org_id": org_id_str,
                "po_num": po.po_number,
                "total": str(po.total_amount),
                "currency": po.currency,
                "status": po.status,
                "issue_date": po.issue_date.isoformat(),
                "synced_at": synced_at,
            },
        )
        if vendor:
            run_write(
                """
                MATCH (v:Vendor {graph_key: $v_gk}), (p:PurchaseOrder {graph_key: $po_gk})
                MERGE (v)-[:ISSUED]->(p)
                """,
                {"v_gk": _gkey(org_id_str, "Vendor", vendor.id), "po_gk": po_gk},
            )
        for ln in po.lines:
            pl_gk = _gkey(org_id_str, "POLine", ln.id)
            po_lines_by_id[str(ln.id)] = pl_gk
            if ln.item_code:
                po_lines_by_code[ln.item_code] = pl_gk
            run_write(
                """
                MATCH (p:PurchaseOrder {graph_key: $po_gk})
                MERGE (pl:POLine {graph_key: $pl_gk})
                SET pl.source_id = $lid, pl.organization_id = $org_id, pl.entity_type = 'POLine',
                    pl.label = $label, pl.item_code = $item_code, pl.quantity = $qty,
                    pl.unit_price = $price, pl.uom = $uom, pl.source_system = 'postgresql',
                    pl.last_synced_at = $synced_at
                MERGE (p)-[:CONTAINS]->(pl)
                """,
                {
                    "po_gk": po_gk,
                    "pl_gk": pl_gk,
                    "lid": str(ln.id),
                    "org_id": org_id_str,
                    "label": f"{ln.item_code or 'LINE'} ({ln.quantity} {ln.uom})",
                    "item_code": ln.item_code or "",
                    "qty": str(ln.quantity),
                    "price": str(ln.unit_price),
                    "uom": ln.uom,
                    "synced_at": synced_at,
                },
            )

    for g in grns:
        grn_gk = _gkey(org_id_str, "GoodsReceipt", g.id)
        acc_sum = sum((ln.accepted_qty for ln in g.lines), 0)
        rej_sum = sum((ln.rejected_qty for ln in g.lines), 0)
        run_write(
            """
            MERGE (grn:GoodsReceipt {graph_key: $grn_gk})
            SET grn.source_id = $gid, grn.organization_id = $org_id, grn.entity_type = 'GoodsReceipt',
                grn.label = $grn_num, grn.grn_number = $grn_num, grn.status = $status,
                grn.accepted_qty = $acc, grn.rejected_qty = $rej,
                grn.received_at = $received_at, grn.source_system = 'postgresql',
                grn.last_synced_at = $synced_at
            """,
            {
                "grn_gk": grn_gk,
                "gid": str(g.id),
                "org_id": org_id_str,
                "grn_num": g.grn_number,
                "status": g.status,
                "acc": str(acc_sum),
                "rej": str(rej_sum),
                "received_at": g.received_at.isoformat(),
                "synced_at": synced_at,
            },
        )
        if po:
            run_write(
                """
                MATCH (p:PurchaseOrder {graph_key: $po_gk}), (grn:GoodsReceipt {graph_key: $grn_gk})
                MERGE (p)-[:HAS_RECEIPT]->(grn)
                """,
                {"po_gk": _gkey(org_id_str, "PurchaseOrder", po.id), "grn_gk": grn_gk},
            )
        for gl in g.lines:
            gl_gk = _gkey(org_id_str, "GRNLine", gl.id)
            run_write(
                """
                MATCH (grn:GoodsReceipt {graph_key: $grn_gk})
                MERGE (gl:GRNLine {graph_key: $gl_gk})
                SET gl.source_id = $glid, gl.organization_id = $org_id, gl.entity_type = 'GRNLine',
                    gl.label = $label, gl.item_code = $item_code,
                    gl.received_qty = $rec, gl.accepted_qty = $acc, gl.rejected_qty = $rej,
                    gl.source_system = 'postgresql', gl.last_synced_at = $synced_at
                MERGE (grn)-[:CONTAINS]->(gl)
                """,
                {
                    "grn_gk": grn_gk,
                    "gl_gk": gl_gk,
                    "glid": str(gl.id),
                    "org_id": org_id_str,
                    "label": f"{gl.item_code or 'GRN-LINE'} (Acc {gl.accepted_qty})",
                    "item_code": gl.item_code or "",
                    "rec": str(gl.received_qty),
                    "acc": str(gl.accepted_qty),
                    "rej": str(gl.rejected_qty),
                    "synced_at": synced_at,
                },
            )
            target_pl_gk = (
                po_lines_by_id.get(str(gl.po_line_id))
                if gl.po_line_id
                else po_lines_by_code.get(gl.item_code or "")
            )
            if target_pl_gk:
                verified = gl.po_line_id is not None
                run_write(
                    """
                    MATCH (gl:GRNLine {graph_key: $gl_gk}), (pl:POLine {graph_key: $pl_gk})
                    MERGE (gl)-[r:FULFILLS]->(pl)
                    SET r.verified = $verified, r.method = $method, r.confidence = $conf
                    """,
                    {
                        "gl_gk": gl_gk,
                        "pl_gk": target_pl_gk,
                        "verified": verified,
                        "method": "po_line_id" if verified else "item_code_match",
                        "conf": 1.0 if verified else 0.85,
                    },
                )

    for inv in invoices:
        inv_gk = _gkey(org_id_str, "Invoice", inv.id)
        run_write(
            """
            MERGE (i:Invoice {graph_key: $inv_gk})
            SET i.source_id = $iid, i.organization_id = $org_id, i.entity_type = 'Invoice',
                i.label = $inv_num, i.invoice_number = $inv_num, i.total_amount = $total,
                i.tax_amount = $tax, i.currency = $currency, i.status = $status,
                i.invoice_date = $inv_date, i.source_system = 'postgresql',
                i.last_synced_at = $synced_at
            """,
            {
                "inv_gk": inv_gk,
                "iid": str(inv.id),
                "org_id": org_id_str,
                "inv_num": inv.invoice_number,
                "total": str(inv.total_amount),
                "tax": str(inv.tax_amount),
                "currency": inv.currency,
                "status": inv.status,
                "inv_date": inv.invoice_date.isoformat(),
                "synced_at": synced_at,
            },
        )
        if vendor:
            run_write(
                """
                MATCH (v:Vendor {graph_key: $v_gk}), (i:Invoice {graph_key: $inv_gk})
                MERGE (v)-[:SENT]->(i)
                """,
                {"v_gk": _gkey(org_id_str, "Vendor", vendor.id), "inv_gk": inv_gk},
            )
        if po:
            run_write(
                """
                MATCH (i:Invoice {graph_key: $inv_gk}), (p:PurchaseOrder {graph_key: $po_gk})
                MERGE (i)-[:BILLS_AGAINST]->(p)
                """,
                {"inv_gk": inv_gk, "po_gk": _gkey(org_id_str, "PurchaseOrder", po.id)},
            )
        for il in inv.lines:
            il_gk = _gkey(org_id_str, "InvoiceLine", il.id)
            run_write(
                """
                MATCH (i:Invoice {graph_key: $inv_gk})
                MERGE (il:InvoiceLine {graph_key: $il_gk})
                SET il.source_id = $ilid, il.organization_id = $org_id, il.entity_type = 'InvoiceLine',
                    il.label = $label, il.item_code = $item_code, il.quantity = $qty,
                    il.unit_price = $price, il.source_system = 'postgresql',
                    il.last_synced_at = $synced_at
                MERGE (i)-[:CONTAINS]->(il)
                """,
                {
                    "inv_gk": inv_gk,
                    "il_gk": il_gk,
                    "ilid": str(il.id),
                    "org_id": org_id_str,
                    "label": f"{il.item_code or 'INV-LINE'} ({il.quantity} @ {il.unit_price})",
                    "item_code": il.item_code or "",
                    "qty": str(il.quantity),
                    "price": str(il.unit_price),
                    "synced_at": synced_at,
                },
            )
            target_pl_gk = (
                po_lines_by_id.get(str(il.po_line_id))
                if il.po_line_id
                else po_lines_by_code.get(il.item_code or "")
            )
            if target_pl_gk:
                verified = il.po_line_id is not None
                run_write(
                    """
                    MATCH (il:InvoiceLine {graph_key: $il_gk}), (pl:POLine {graph_key: $pl_gk})
                    MERGE (il)-[r:CLAIMS_FOR]->(pl)
                    SET r.verified = $verified, r.method = $method, r.confidence = $conf
                    """,
                    {
                        "il_gk": il_gk,
                        "pl_gk": target_pl_gk,
                        "verified": verified,
                        "method": "po_line_id" if verified else "item_code_match",
                        "conf": 1.0 if verified else 0.85,
                    },
                )

    # Documents
    docs = list(
        db.scalars(
            OrgScopedRepository(db, Document, organization_id)
            .base_query()
            .where(Document.transaction_id == transaction_id)
        ).all()
    )
    for d in docs:
        d_gk = _gkey(org_id_str, "Document", d.id)
        run_write(
            """
            MERGE (doc:Document {graph_key: $d_gk})
            SET doc.source_id = $did, doc.organization_id = $org_id, doc.entity_type = 'Document',
                doc.label = $label, doc.document_type = $dtype, doc.status = $status,
                doc.checksum = $checksum, doc.source_system = 'postgresql',
                doc.last_synced_at = $synced_at
            """,
            {
                "d_gk": d_gk,
                "did": str(d.id),
                "org_id": org_id_str,
                "label": d.file_name,
                "dtype": d.document_type,
                "status": d.status,
                "checksum": d.checksum[:16],
                "synced_at": synced_at,
            },
        )
        if po:
            run_write(
                """
                MATCH (doc:Document {graph_key: $d_gk}), (p:PurchaseOrder {graph_key: $po_gk})
                MERGE (doc)-[:EVIDENCES]->(p)
                """,
                {"d_gk": d_gk, "po_gk": _gkey(org_id_str, "PurchaseOrder", po.id)},
            )

    # ReconciliationRun + Exceptions + RiskSignals + Approvals + Investigations
    latest_run = db.scalar(
        OrgScopedRepository(db, ReconciliationRun, organization_id)
        .base_query()
        .where(ReconciliationRun.transaction_id == transaction_id)
        .order_by(desc(ReconciliationRun.completed_at))
        .limit(1)
    )
    if latest_run:
        r_gk = _gkey(org_id_str, "ReconciliationRun", latest_run.id)
        run_write(
            """
            MERGE (r:ReconciliationRun {graph_key: $r_gk})
            SET r.source_id = $rid, r.organization_id = $org_id, r.entity_type = 'ReconciliationRun',
                r.label = $label, r.outcome = $outcome, r.rule_version = $ver,
                r.completed_at = $completed_at, r.source_system = 'postgresql',
                r.last_synced_at = $synced_at
            """,
            {
                "r_gk": r_gk,
                "rid": str(latest_run.id),
                "org_id": org_id_str,
                "label": f"Match {latest_run.outcome} (v{latest_run.rule_version})",
                "outcome": latest_run.outcome,
                "ver": latest_run.rule_version,
                "completed_at": latest_run.completed_at.isoformat(),
                "synced_at": synced_at,
            },
        )
        if po:
            run_write(
                """
                MATCH (p:PurchaseOrder {graph_key: $po_gk}), (r:ReconciliationRun {graph_key: $r_gk})
                MERGE (p)-[:EVALUATED_BY]->(r)
                """,
                {"po_gk": _gkey(org_id_str, "PurchaseOrder", po.id), "r_gk": r_gk},
            )
        for g in grns:
            run_write(
                """
                MATCH (grn:GoodsReceipt {graph_key: $grn_gk}), (r:ReconciliationRun {graph_key: $r_gk})
                MERGE (grn)-[:SUPPORTS]->(r)
                """,
                {"grn_gk": _gkey(org_id_str, "GoodsReceipt", g.id), "r_gk": r_gk},
            )

    excs = list(
        db.scalars(
            OrgScopedRepository(db, ExceptionCase, organization_id)
            .base_query()
            .where(ExceptionCase.transaction_id == transaction_id)
        ).all()
    )
    for exc in excs:
        e_gk = _gkey(org_id_str, "Exception", exc.id)
        run_write(
            """
            MERGE (e:Exception {graph_key: $e_gk})
            SET e.source_id = $eid, e.organization_id = $org_id, e.entity_type = 'Exception',
                e.label = $label, e.type = $etype, e.rule_id = $rule_id,
                e.severity = $sev, e.status = $status, e.summary = $summary,
                e.source_system = 'postgresql', e.last_synced_at = $synced_at
            """,
            {
                "e_gk": e_gk,
                "eid": str(exc.id),
                "org_id": org_id_str,
                "label": f"{exc.type} ({exc.rule_id})",
                "etype": exc.type,
                "rule_id": exc.rule_id,
                "sev": exc.severity,
                "status": exc.status,
                "summary": exc.summary,
                "synced_at": synced_at,
            },
        )
        if latest_run:
            run_write(
                """
                MATCH (r:ReconciliationRun {graph_key: $r_gk}), (e:Exception {graph_key: $e_gk})
                MERGE (r)-[:GENERATED]->(e)
                """,
                {"r_gk": _gkey(org_id_str, "ReconciliationRun", latest_run.id), "e_gk": e_gk},
            )
        elif po:
            run_write(
                """
                MATCH (p:PurchaseOrder {graph_key: $po_gk}), (e:Exception {graph_key: $e_gk})
                MERGE (p)-[:HAS_EXCEPTION]->(e)
                """,
                {"po_gk": _gkey(org_id_str, "PurchaseOrder", po.id), "e_gk": e_gk},
            )

    risks = list(
        db.scalars(
            OrgScopedRepository(db, RiskSignal, organization_id)
            .base_query()
            .where(RiskSignal.transaction_id == transaction_id)
        ).all()
    )
    for rs in risks:
        rs_gk = _gkey(org_id_str, "RiskSignal", rs.id)
        run_write(
            """
            MERGE (s:RiskSignal {graph_key: $rs_gk})
            SET s.source_id = $sid, s.organization_id = $org_id, s.entity_type = 'RiskSignal',
                s.label = $label, s.signal_type = $stype, s.severity = $sev,
                s.score = $score, s.source_system = 'postgresql', s.last_synced_at = $synced_at
            """,
            {
                "rs_gk": rs_gk,
                "sid": str(rs.id),
                "org_id": org_id_str,
                "label": f"{rs.signal_type} ({rs.severity})",
                "stype": rs.signal_type,
                "sev": rs.severity,
                "score": str(rs.score),
                "synced_at": synced_at,
            },
        )
        if excs:
            run_write(
                """
                MATCH (e:Exception {graph_key: $e_gk}), (s:RiskSignal {graph_key: $rs_gk})
                MERGE (e)-[:HAS_RISK_SIGNAL]->(s)
                """,
                {"e_gk": _gkey(org_id_str, "Exception", excs[0].id), "rs_gk": rs_gk},
            )
        elif po:
            run_write(
                """
                MATCH (p:PurchaseOrder {graph_key: $po_gk}), (s:RiskSignal {graph_key: $rs_gk})
                MERGE (p)-[:HAS_RISK_SIGNAL]->(s)
                """,
                {"po_gk": _gkey(org_id_str, "PurchaseOrder", po.id), "rs_gk": rs_gk},
            )

    approvals = list(
        db.scalars(
            OrgScopedRepository(db, Approval, organization_id)
            .base_query()
            .where(Approval.transaction_id == transaction_id)
        ).all()
    )
    for ap in approvals:
        ap_gk = _gkey(org_id_str, "Approval", ap.id)
        run_write(
            """
            MERGE (a:Approval {graph_key: $ap_gk})
            SET a.source_id = $aid, a.organization_id = $org_id, a.entity_type = 'Approval',
                a.label = $label, a.decision = $dec, a.decided_at = $dec_at,
                a.source_system = 'postgresql', a.last_synced_at = $synced_at
            """,
            {
                "ap_gk": ap_gk,
                "aid": str(ap.id),
                "org_id": org_id_str,
                "label": f"Decision: {ap.decision}",
                "dec": ap.decision,
                "dec_at": ap.decided_at.isoformat(),
                "synced_at": synced_at,
            },
        )
        if ap.case_id is not None:
            run_write(
                """
                MATCH (a:Approval {graph_key: $ap_gk}), (e:Exception {graph_key: $e_gk})
                MERGE (a)-[:DECIDES_ON]->(e)
                """,
                {"ap_gk": ap_gk, "e_gk": _gkey(org_id_str, "Exception", ap.case_id)},
            )

    # Policy evaluations for this transaction
    evals = list(
        db.scalars(
            OrgScopedRepository(db, PolicyEvaluation, organization_id)
            .base_query()
            .where(PolicyEvaluation.transaction_id == transaction_id)
            .limit(20)
        ).all()
    )
    for ev in evals:
        ev_gk = _gkey(org_id_str, "PolicyEvaluation", ev.id)
        pv = db.get(PolicyVersion, ev.policy_version_id)
        pol = db.get(Policy, ev.policy_id)
        ev_matched = bool(ev.matched_conditions_json) or str(ev.status).upper() not in (
            "PASS",
            "PASSED",
            "OK",
            "SKIPPED",
        )
        run_write(
            """
            MERGE (pe:PolicyEvaluation {graph_key: $ev_gk})
            SET pe.source_id = $evid, pe.organization_id = $org_id,
                pe.entity_type = 'PolicyEvaluation', pe.matched = $matched,
                pe.label = $label, pe.source_system = 'postgresql', pe.last_synced_at = $synced_at
            """,
            {
                "ev_gk": ev_gk,
                "evid": str(ev.id),
                "org_id": org_id_str,
                "matched": ev_matched,
                "label": f"{pol.policy_key if pol else 'POLICY'} ({ev.status})",
                "synced_at": synced_at,
            },
        )
        if pv:
            pv_gk = _gkey(org_id_str, "PolicyVersion", pv.id)
            run_write(
                """
                MERGE (pv:PolicyVersion {graph_key: $pv_gk})
                SET pv.source_id = $pvid, pv.organization_id = $org_id,
                    pv.entity_type = 'PolicyVersion', pv.version_number = $ver,
                    pv.label = $label, pv.source_system = 'postgresql', pv.last_synced_at = $synced_at
                WITH pv
                MATCH (pe:PolicyEvaluation {graph_key: $ev_gk})
                MERGE (pe)-[:EVALUATED_USING]->(pv)
                """,
                {
                    "pv_gk": pv_gk,
                    "pvid": str(pv.id),
                    "org_id": org_id_str,
                    "ver": pv.version_number,
                    "label": f"{pol.policy_key if pol else 'POL'} v{pv.version_number}",
                    "ev_gk": ev_gk,
                    "synced_at": synced_at,
                },
            )
        if ev.exception_id:
            run_write(
                """
                MATCH (pe:PolicyEvaluation {graph_key: $ev_gk}), (e:Exception {graph_key: $e_gk})
                MERGE (pe)-[:TRIGGERED]->(e)
                """,
                {"ev_gk": ev_gk, "e_gk": _gkey(org_id_str, "Exception", ev.exception_id)},
            )

    return True


def sync_investigation_to_neo4j(
    db: Session,
    *,
    organization_id: UUID,
    investigation_id: UUID,
) -> bool:
    """Idempotently project an Investigation, AgentRun, Stages, ToolCalls, and EvidenceReferences."""
    inv = OrgScopedRepository(db, Investigation, organization_id).get_by_id(investigation_id)
    if not inv:
        return False

    org_id_str = str(organization_id)
    synced_at = _now_iso()
    out = inv.structured_output_json or {}
    exec_trace: list[dict[str, Any]] = out.get("execution_trace") or []
    tool_trace: list[dict[str, Any]] = out.get("tool_trace") or []
    ev_refs: list[dict[str, Any]] = out.get("evidence_refs") or []

    run_gk = _gkey(org_id_str, "AgentRun", inv.id)
    inv_gk = _gkey(org_id_str, "Investigation", inv.id)
    case_gk = _gkey(org_id_str, "Exception", inv.case_id)

    run_write(
        """
        MERGE (ar:AgentRun {graph_key: $run_gk})
        SET ar.source_id = $inv_id, ar.investigation_id = $inv_id,
            ar.organization_id = $org_id, ar.case_id = $case_id,
            ar.entity_type = 'AgentRun', ar.label = $run_label,
            ar.model_provider = $provider, ar.actual_provider = $actual_provider,
            ar.model_name = $model_name, ar.status = $status,
            ar.fallback_used = $fallback_used, ar.latency_ms = $latency_ms,
            ar.created_at = $created_at, ar.source_system = 'postgresql',
            ar.last_synced_at = $synced_at
        MERGE (ig:Investigation {graph_key: $inv_gk})
        SET ig.source_id = $inv_id, ig.organization_id = $org_id,
            ig.entity_type = 'Investigation', ig.label = $inv_label,
            ig.model_provider = $actual_provider, ig.model_name = $model_name,
            ig.confidence = $confidence, ig.status = $status,
            ig.summary = $summary, ig.source_system = 'postgresql',
            ig.last_synced_at = $synced_at
        MERGE (ar)-[:PRODUCED_INVESTIGATION]->(ig)
        WITH ar, ig
        OPTIONAL MATCH (ex:Exception {graph_key: $case_gk})
        FOREACH (_ IN CASE WHEN ex IS NOT NULL THEN [1] ELSE [] END |
            MERGE (ar)-[:INVESTIGATES]->(ex)
            MERGE (ex)-[:INVESTIGATED_BY]->(ig)
        )
        """,
        {
            "run_gk": run_gk,
            "inv_gk": inv_gk,
            "case_gk": case_gk,
            "inv_id": str(inv.id),
            "org_id": org_id_str,
            "case_id": str(inv.case_id),
            "run_label": f"AgentRun {str(inv.id)[:8]}",
            "inv_label": f"Investigation ({out.get('actual_provider', inv.model_provider)})",
            "provider": out.get("configured_provider", inv.model_provider),
            "actual_provider": out.get("actual_provider", inv.model_provider),
            "model_name": inv.model_name,
            "status": inv.status,
            "fallback_used": bool(out.get("fallback_used", False)),
            "latency_ms": float(out.get("latency_ms", 0.0)),
            "confidence": float(inv.confidence),
            "summary": str(out.get("summary", ""))[:500],
            "created_at": inv.created_at.isoformat(),
            "synced_at": synced_at,
        },
    )

    prev_stage_gk: str | None = None
    stage_gk_by_agent: dict[str, str] = {}
    for idx, step in enumerate(exec_trace, start=1):
        agent_name = str(step.get("agent", f"Stage{idx}"))
        stage_gk = _gkey(org_id_str, "AgentStageExecution", f"{inv.id}:{idx}:{agent_name}")
        def_gk = _gkey(org_id_str, "AgentDefinition", agent_name)
        stage_gk_by_agent[agent_name] = stage_gk
        run_write(
            """
            MATCH (ar:AgentRun {graph_key: $run_gk})
            MERGE (ad:AgentDefinition {graph_key: $def_gk})
            SET ad.agent_id = $agent_name, ad.name = $agent_name,
                ad.organization_id = $org_id, ad.entity_type = 'AgentDefinition',
                ad.label = $agent_name, ad.source_system = 'postgresql',
                ad.last_synced_at = $synced_at
            MERGE (st:AgentStageExecution {graph_key: $stage_gk})
            SET st.execution_id = $exec_id, st.organization_id = $org_id,
                st.investigation_id = $inv_id, st.agent_name = $agent_name,
                st.stage_order = $order, st.status = $status,
                st.duration_ms = $dur, st.summary = $summary,
                st.entity_type = 'AgentStageExecution',
                st.label = $label, st.source_system = 'postgresql',
                st.last_synced_at = $synced_at
            MERGE (ar)-[:EXECUTED_STAGE]->(st)
            MERGE (st)-[:INSTANCE_OF]->(ad)
            """,
            {
                "run_gk": run_gk,
                "def_gk": def_gk,
                "stage_gk": stage_gk,
                "exec_id": f"{inv.id}:{idx}",
                "org_id": org_id_str,
                "inv_id": str(inv.id),
                "agent_name": agent_name,
                "order": idx,
                "status": str(step.get("status", "SUCCEEDED")),
                "dur": float(step.get("duration_ms", 0.0)),
                "summary": str(step.get("summary", ""))[:500],
                "label": f"{idx}. {agent_name}",
                "synced_at": synced_at,
            },
        )
        if prev_stage_gk:
            run_write(
                """
                MATCH (a:AgentStageExecution {graph_key: $prev_gk}),
                      (b:AgentStageExecution {graph_key: $cur_gk})
                MERGE (a)-[:NEXT_STAGE]->(b)
                """,
                {"prev_gk": prev_stage_gk, "cur_gk": stage_gk},
            )
        prev_stage_gk = stage_gk

    # Link tool calls to their corresponding stage
    tool_stage_map = {
        "get_transaction_bundle": "DocumentAgent",
        "search_related_documents": "DocumentAgent",
        "run_reconciliation": "MatchingAgent",
        "get_vendor_history": "VendorIntelligenceAgent",
        "create_investigation_draft": "AuditAgent",
    }
    for t_idx, tc in enumerate(tool_trace, start=1):
        tool_name = str(tc.get("tool", "unknown_tool"))
        tc_gk = _gkey(org_id_str, "ToolCall", f"{inv.id}:{t_idx}:{tool_name}")
        target_agent = tool_stage_map.get(tool_name, "AuditAgent")
        target_stage_gk = stage_gk_by_agent.get(target_agent) or prev_stage_gk
        run_write(
            """
            MERGE (tc:ToolCall {graph_key: $tc_gk})
            SET tc.tool_call_id = $tc_id, tc.tool_name = $tool_name,
                tc.status = $status, tc.summary = $summary,
                tc.investigation_id = $inv_id, tc.organization_id = $org_id,
                tc.entity_type = 'ToolCall', tc.label = $tool_name,
                tc.source_system = 'postgresql', tc.last_synced_at = $synced_at
            """,
            {
                "tc_gk": tc_gk,
                "tc_id": f"{inv.id}:tool:{t_idx}",
                "tool_name": tool_name,
                "status": "SUCCEEDED" if tc.get("ok", True) else "FAILED",
                "summary": str(tc.get("summary", ""))[:300],
                "inv_id": str(inv.id),
                "org_id": org_id_str,
                "synced_at": synced_at,
            },
        )
        if target_stage_gk:
            run_write(
                """
                MATCH (st:AgentStageExecution {graph_key: $st_gk}),
                      (tc:ToolCall {graph_key: $tc_gk})
                MERGE (st)-[:CALLED_TOOL]->(tc)
                """,
                {"st_gk": target_stage_gk, "tc_gk": tc_gk},
            )

    # Evidence references
    ev_stage_gk = stage_gk_by_agent.get("InvestigationAgent") or prev_stage_gk
    for e_idx, ref in enumerate(ev_refs, start=1):
        rtype = str(ref.get("type", "record"))
        rid = str(ref.get("id", f"ref-{e_idx}"))
        rlabel = str(ref.get("label") or f"{rtype}:{rid[:8]}")
        er_gk = _gkey(org_id_str, "EvidenceReference", f"{rtype}:{rid}")
        run_write(
            """
            MERGE (er:EvidenceReference {graph_key: $er_gk})
            SET er.reference_id = $rid, er.source_type = $rtype,
                er.source_record_id = $rid, er.label = $rlabel,
                er.validated = true, er.organization_id = $org_id,
                er.entity_type = 'EvidenceReference',
                er.source_system = 'postgresql', er.last_synced_at = $synced_at
            WITH er
            MATCH (ig:Investigation {graph_key: $inv_gk})
            MERGE (ig)-[:CITES]->(er)
            """,
            {
                "er_gk": er_gk,
                "rid": rid,
                "rtype": rtype,
                "rlabel": rlabel,
                "org_id": org_id_str,
                "inv_gk": inv_gk,
                "synced_at": synced_at,
            },
        )
        if ev_stage_gk:
            run_write(
                """
                MATCH (st:AgentStageExecution {graph_key: $st_gk}),
                      (er:EvidenceReference {graph_key: $er_gk})
                MERGE (st)-[:REFERENCED]->(er)
                """,
                {"st_gk": ev_stage_gk, "er_gk": er_gk},
            )

    return True
