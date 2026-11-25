import csv
import io
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.models.policy import ExecutiveBrief


def _csv_safe(val: Any) -> str:
    s = str(val if val is not None else "")
    if s.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + s
    return s


def render_brief_markdown(brief: ExecutiveBrief, org_name: str) -> str:
    m = brief.metrics_json or {}
    e = brief.exposure_json or {}
    tops: list[dict[str, Any]] = brief.top_exceptions_json or []
    cits: list[dict[str, Any]] = brief.citations_json or []
    pdiff: dict[str, Any] = brief.policy_diff_json or {}
    lims: list[str] = brief.limitations_json or []

    lines = [
        "# ReconX AI — Executive Reconciliation & Risk Brief",
        f"- **Organization:** {org_name}",
        f"- **Report ID:** `{brief.id}`",
        f"- **Generated At:** {brief.created_at.isoformat()}",
        f"- **Scope:** `{brief.scope}`",
        f"- **Checksum:** `{brief.content_checksum}`",
        "",
        "## 1. Executive Summary",
        "| Metric | Value |",
        "|---|---|",
        f"| Documents Processed | {m.get('total_documents_processed', 0)} |",
        f"| Transactions Evaluated | {m.get('total_transactions_evaluated', 0)} |",
        f"| Matched | {m.get('matched_transactions', 0)} |",
        f"| Matched Within Tolerance | {m.get('matched_within_tolerance', 0)} |",
        f"| Review Required | {m.get('review_required', 0)} |",
        f"| Exception Transactions | {m.get('exception_transactions', 0)} |",
        f"| Open Exceptions | {m.get('total_open_exceptions', 0)} |",
        f"| High / Critical Exceptions | {m.get('high_and_critical_exceptions', 0)} |",
        "",
        "## 2. Financial Exposure",
        f"- **Currency:** {e.get('currency', 'INR')}",
        f"- **Total Affected Invoice Value:** {e.get('total_affected_invoice_value', '0.00')}",
        f"- **Open Exception Exposure (Deduplicated):** {e.get('open_exception_exposure', '0.00')}",
        f"- **Quantity Variance Exposure:** {e.get('quantity_variance_exposure', '0.00')}",
        f"- **Price Variance Exposure:** {e.get('price_variance_exposure', '0.00')}",
        f"- **Methodology:** {e.get('methodology', '')}",
        "",
        "## 3. Top Three Urgent Exceptions",
    ]
    if not tops:
        lines.append("No open exceptions found in the selected scope.")
    else:
        for idx, t in enumerate(tops, 1):
            lines.extend(
                [
                    f"### {idx}. {t['po_number']} — {t['category']} ({t['severity']})",
                    f"- **Exception ID:** `{t['exception_id']}` | **Rule:** `{t['rule_id']}`",
                    f"- **Vendor:** {t['vendor_name']} | **Invoice:** {t['invoice_number']}",
                    f"- **Exposure:** {t['currency']} {t['financial_exposure']}",
                    f"- **Why Flagged:** {t['why_flagged']}",
                    f"- **Citations:** {', '.join(t.get('citation_ids', []))}",
                    "",
                ]
            )

    lines.extend(
        [
            "## 4. Verified Evidence Citations",
            "| Citation ID | Type | Record | Field | Observed Value |",
            "|---|---|---|---|---|",
        ]
    )
    for c in cits:
        lines.append(
            f"| {c['citation_id']} | {c['source_type']} | {c['source_display_id']} | "
            f"{c['source_field']} | {c['observed_value']} |"
        )

    if pdiff:
        lines.extend(
            [
                "",
                "## 5. Policy Re-Audit Impact",
                f"- **Audit Run ID:** `{pdiff.get('audit_run_id')}` ({pdiff.get('status')})",
                f"- **Transactions Scanned:** {pdiff.get('transactions_scanned', 0)}",
                f"- **New Exceptions:** {pdiff.get('new_exceptions', 0)} | "
                f"**Existing:** {pdiff.get('existing_exceptions', 0)} | "
                f"**No Longer Triggered:** {pdiff.get('resolved_exceptions', 0)}",
            ]
        )

    lines.extend(["", "## 6. Limitations & Governance"])
    for lim in lims:
        lines.append(f"- {lim}")
    return "\n".join(lines) + "\n"


def render_brief_csv(brief: ExecutiveBrief, org_name: str) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["SECTION", "KEY_OR_ID", "COL_1", "COL_2", "COL_3", "COL_4"])
    w.writerow(
        [
            "METADATA",
            str(brief.id),
            _csv_safe(org_name),
            brief.scope,
            brief.created_at.isoformat(),
            brief.content_checksum,
        ]
    )
    for k, v in (brief.metrics_json or {}).items():
        w.writerow(["EXECUTIVE_METRICS", k, _csv_safe(v), "", "", ""])
    for k, v in (brief.exposure_json or {}).items():
        w.writerow(["FINANCIAL_EXPOSURE", k, _csv_safe(v), "", "", ""])
    for t in brief.top_exceptions_json or []:
        w.writerow([
            "TOP_EXCEPTIONS",
            t["exception_id"],
            _csv_safe(t["po_number"]),
            _csv_safe(t["severity"]),
            _csv_safe(t["financial_exposure"]),
            _csv_safe(t["why_flagged"]),
        ])
    for c in brief.citations_json or []:
        w.writerow([
            "EVIDENCE_CITATIONS",
            c["citation_id"],
            _csv_safe(c["source_type"]),
            _csv_safe(c["source_display_id"]),
            _csv_safe(c["source_field"]),
            _csv_safe(c["observed_value"]),
        ])
    return buf.getvalue().encode("utf-8")


def render_brief_pdf(brief: ExecutiveBrief, org_name: str) -> bytes:
    pdf_buf = io.BytesIO()
    c = canvas.Canvas(pdf_buf, pagesize=A4)
    page_num = 1

    def _footer() -> None:
        c.setFont("Helvetica", 8)
        c.drawString(40, 28, f"ReconX AI Confidential | Report {brief.id} | Page {page_num}")

    def _new_page() -> int:
        nonlocal page_num
        _footer()
        c.showPage()
        page_num += 1
        c.setFont("Helvetica", 10)
        return 800

    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, 800, "ReconX AI — Executive Reconciliation & Risk Brief")
    c.setFont("Helvetica", 10)
    c.drawString(40, 780, f"Organization: {org_name} | Scope: {brief.scope}")
    c.drawString(40, 765, f"Report ID: {brief.id} | Generated: {brief.created_at.isoformat()}")

    y = 735
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "1. Executive Summary & Financial Exposure")
    y -= 18
    c.setFont("Helvetica", 10)
    m = brief.metrics_json or {}
    e = brief.exposure_json or {}
    summary_lines = [
        f"Documents: {m.get('total_documents_processed', 0)} | "
        f"Txns Evaluated: {m.get('total_transactions_evaluated', 0)} | "
        f"Matched: {m.get('matched_transactions', 0)}",
        f"Open Exceptions: {m.get('total_open_exceptions', 0)} "
        f"(High/Critical: {m.get('high_and_critical_exceptions', 0)})",
        f"Open Exposure: {e.get('currency', 'INR')} {e.get('open_exception_exposure', '0.00')} "
        f"(Qty: {e.get('quantity_variance_exposure', '0.00')}, "
        f"Price: {e.get('price_variance_exposure', '0.00')})",
    ]
    for ln in summary_lines:
        c.drawString(40, y, ln[:95])
        y -= 16

    y -= 10
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "2. Top Urgent Exceptions & Evidence Citations")
    y -= 18
    c.setFont("Helvetica", 9)
    for idx, t in enumerate(brief.top_exceptions_json or [], 1):
        if y < 100:
            y = _new_page()
        c.setFont("Helvetica-Bold", 10)
        c.drawString(
            40,
            y,
            f"{idx}. {t['po_number']} | {t['category']} ({t['severity']}) | "
            f"Exposure: {t['currency']} {t['financial_exposure']}",
        )
        y -= 14
        c.setFont("Helvetica", 9)
        c.drawString(50, y, f"Why Flagged: {t['why_flagged'][:95]}")
        y -= 14
        c.drawString(50, y, f"Citations: {', '.join(t.get('citation_ids', []))}")
        y -= 18

    y -= 6
    c.setFont("Helvetica-Bold", 12)
    if y < 100:
        y = _new_page()
    c.drawString(40, y, "3. Verified Source Citations")
    y -= 16
    c.setFont("Helvetica", 8)
    for cit in (brief.citations_json or [])[:25]:
        if y < 60:
            y = _new_page()
        row_txt = (
            f"{cit['citation_id']} | {cit['source_type']} | "
            f"{cit['source_display_id']} | {cit['source_field']}={cit['observed_value']}"
        )
        c.drawString(40, y, row_txt[:105])
        y -= 13

    _footer()
    c.save()
    return pdf_buf.getvalue()
