import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { StatusBadge } from "../components/StatusBadge";
import { TransactionDetailPage } from "../pages/TransactionDetailPage";
import { DocumentsPage } from "../pages/DocumentsPage";
import { AuthProvider } from "../auth/AuthContext";
import { api } from "../api/client";

describe("ReconX Frontend Core Components", () => {
  it("renders StatusBadge with explicit text and styling", () => {
    render(<StatusBadge value="MATCHED_WITH_TOLERANCE" />);
    const badge = screen.getByTestId("status-badge");
    expect(badge).toHaveTextContent("MATCHED_WITH_TOLERANCE");
    expect(badge.className).toContain("bg-teal-50");
  });

  it("renders side-by-side diff table and rule breakdown on TransactionDetailPage", async () => {
    vi.spyOn(api, "me").mockResolvedValue({
      id: "u1",
      organization_id: "org1",
      organization_name: "Acme",
      email: "operator@reconx-demo.com",
      full_name: "Asha Operator",
      status: "ACTIVE",
      roles: ["finance_operator"],
      permissions: ["transactions:read", "reconciliation:run"],
    });
    vi.spyOn(api, "getTransaction").mockResolvedValue({
      transaction_id: "tx-1",
      organization_id: "org1",
      vendor: {
        id: "v1",
        legal_name: "Sahyadri LLP",
        tax_identifier: "27AADFS5678K1Z2",
        bank_account_masked: "XXXX-9104",
        status: "ACTIVE",
      },
      purchase_order: {
        id: "tx-1",
        po_number: "PO-2026-0002",
        issue_date: "2026-09-02",
        currency: "INR",
        status: "EXCEPTION",
        subtotal_amount: "12000.00",
        tax_amount: "2160.00",
        total_amount: "14160.00",
        lines: [
          {
            id: "pl-1",
            line_number: 1,
            item_code: "HEX-BOLT-M10",
            description: "High Tensile Hex Bolt",
            uom: "EA",
            quantity: "100.0000",
            unit_price: "120.0000",
            tax_amount: "2160.0000",
            line_total: "14160.0000",
          },
        ],
      },
      goods_receipts: [
        {
          id: "g-1",
          grn_number: "GRN-2026-0002",
          received_at: "2026-09-07T00:00:00Z",
          status: "ACCEPTED",
          lines: [
            {
              id: "gl-1",
              po_line_id: "pl-1",
              item_code: "HEX-BOLT-M10",
              description: "Hex Bolt",
              received_qty: "90.0000",
              accepted_qty: "90.0000",
              rejected_qty: "0.0000",
              uom: "EA",
            },
          ],
        },
      ],
      invoices: [
        {
          id: "inv-1",
          invoice_number: "INV-SIF-2001",
          invoice_date: "2026-09-12",
          due_date: "2026-10-12",
          currency: "INR",
          subtotal_amount: "12000.00",
          tax_amount: "2160.00",
          total_amount: "14160.00",
          status: "EXCEPTION",
          lines: [
            {
              id: "il-1",
              po_line_id: "pl-1",
              item_code: "HEX-BOLT-M10",
              description: "Hex Bolt",
              uom: "EA",
              quantity: "100.0000",
              unit_price: "120.0000",
              tax_amount: "2160.0000",
              line_total: "14160.0000",
            },
          ],
        },
      ],
      current_status: "EXCEPTION",
      latest_reconciliation: {
        run_id: "run-1",
        outcome: "EXCEPTION",
        rule_version: "1.0.0",
        totals: { undisputed_amount: "12744.00", disputed_amount: "1416.00" },
        completed_at: "2026-09-12T10:00:00Z",
        results: [
          {
            id: "r1",
            entity_line_id: "pl-1",
            field_name: "invoiced_quantity",
            expected_value: "90.0000",
            actual_value: "100.0000",
            variance: "10.0000",
            tolerance_applied: "abs<=0, pct<=0%",
            breakdown: {},
            rule_id: "R-QTY-01",
            result: "FAIL",
          },
        ],
      },
      exceptions: [],
      risk_signals: [],
    });
    vi.spyOn(api, "getTransactionGraph").mockRejectedValue(new Error("off"));

    localStorage.setItem("reconx_access_token", "fake-token");
    const qc = new QueryClient();
    render(
      <QueryClientProvider client={qc}>
        <AuthProvider>
          <MemoryRouter initialEntries={["/transactions/tx-1"]}>
            <Routes>
              <Route path="/transactions/:id" element={<TransactionDetailPage />} />
            </Routes>
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "PO-2026-0002" })).toBeInTheDocument();
    });
    expect(screen.getByText("R-QTY-01")).toBeInTheDocument();
    expect(screen.getByText(/Qty Δ=10/)).toBeInTheDocument();
  });

  it("supports editing an extracted field on DocumentsPage", async () => {
    vi.spyOn(api, "listDocuments").mockResolvedValue({
      items: [
        {
          document_id: "doc-1",
          organization_id: "org1",
          file_name: "scan.png",
          mime_type: "image/png",
          file_size_bytes: 1200,
          checksum: "abc123def456",
          classification: "INVOICE",
          classification_confidence: 0.9,
          status: "REVIEW_REQUIRED",
          is_duplicate_file: false,
          duplicate_of_document_id: null,
          transaction_id: null,
          created_at: "2026-09-12T00:00:00Z",
          fields: [],
        },
      ],
      total: 1,
      page: 1,
      page_size: 25,
      total_pages: 1,
    });
    vi.spyOn(api, "getDocument").mockResolvedValue({
      document_id: "doc-1",
      organization_id: "org1",
      file_name: "scan.png",
      mime_type: "image/png",
      file_size_bytes: 1200,
      checksum: "abc123def456",
      classification: "INVOICE",
      classification_confidence: 0.9,
      status: "REVIEW_REQUIRED",
      is_duplicate_file: false,
      duplicate_of_document_id: null,
      transaction_id: null,
      created_at: "2026-09-12T00:00:00Z",
      fields: [
        {
          id: "f1",
          name: "total_amount",
          value: "53100.00",
          confidence: 0.55,
          page: 1,
          bbox: null,
          evidence_ref: "page:1:rapidocr",
          extraction_method: "regex+rapidocr",
          verification_status: "extracted",
          verified: false,
          version: 1,
        },
      ],
    });
    const patchSpy = vi.spyOn(api, "patchDocumentFields").mockResolvedValue({} as any);

    const qc = new QueryClient();
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <DocumentsPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => expect(screen.getByText("scan.png")).toBeInTheDocument());
    fireEvent.click(screen.getByText("scan.png"));
    const input = await screen.findByLabelText("Edit total_amount");
    fireEvent.change(input, { target: { value: "53200.00" } });
    fireEvent.click(screen.getByText("Save Corrections"));
    await waitFor(() => expect(patchSpy).toHaveBeenCalledTimes(1));
  });
});
