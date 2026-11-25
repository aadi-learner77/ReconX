export interface ApiErrorEnvelope {
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
    correlation_id: string;
  };
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in_seconds: number;
}

export interface UserProfile {
  id: string;
  organization_id: string;
  organization_name: string;
  email: string;
  full_name: string;
  status: string;
  roles: string[];
  permissions: string[];
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface DashboardSummary {
  kpis: {
    documents: number;
    transactions: number;
    matched_cases: number;
    open_exceptions: number;
    pending_approvals: number;
    processing_jobs: number;
  };
  outcome_breakdown: { outcome: string; count: number }[];
  job_status: Record<string, number>;
  exception_queue: {
    id: string;
    transaction_id: string;
    type: string;
    severity: string;
    status: string;
    summary: string;
  }[];
  recent_activity: {
    id: string;
    action: string;
    entity_type: string;
    actor_type: string;
    timestamp: string;
  }[];
}

export interface ExtractedFieldItem {
  id: string;
  name: string;
  value: unknown;
  confidence: number;
  page: number;
  bbox: { x0: number; y0: number; x1: number; y1: number } | null;
  evidence_ref: string;
  extraction_method: string;
  verification_status: string;
  verified: boolean;
  version: number;
}

export interface DocumentItem {
  document_id: string;
  organization_id: string;
  file_name: string;
  mime_type: string;
  file_size_bytes: number;
  checksum: string;
  classification: string;
  classification_confidence: number;
  status: string;
  is_duplicate_file: boolean;
  duplicate_of_document_id: string | null;
  transaction_id: string | null;
  created_at: string;
  fields: ExtractedFieldItem[];
  candidate_po_links?: { po_id: string; po_number: string; method: string; score: number }[];
  suggested_po_id?: string | null;
  link_ambiguous?: boolean;
}

export interface TransactionListItem {
  transaction_id: string;
  transaction_type: string;
  po_number: string | null;
  vendor_id: string;
  vendor_name: string;
  currency: string;
  total_amount: string;
  document_date: string;
  status: string;
  latest_outcome: string | null;
  exception_count: number;
  risk_level: string;
  scenario_label: string | null;
}

export interface TransactionBundle {
  transaction_id: string;
  organization_id: string;
  vendor: {
    id: string;
    legal_name: string;
    tax_identifier: string;
    bank_account_masked: string;
    status: string;
  };
  purchase_order: {
    id: string;
    po_number: string;
    issue_date: string;
    currency: string;
    status: string;
    subtotal_amount: string;
    tax_amount: string;
    total_amount: string;
    lines: {
      id: string;
      line_number: number;
      item_code: string;
      description: string;
      uom: string;
      quantity: string;
      unit_price: string;
      tax_amount: string;
      line_total: string;
    }[];
  } | null;
  goods_receipts: {
    id: string;
    grn_number: string;
    received_at: string;
    status: string;
    lines: {
      id: string;
      po_line_id: string | null;
      item_code: string;
      description: string;
      received_qty: string;
      accepted_qty: string;
      rejected_qty: string;
      uom: string;
    }[];
  }[];
  invoices: {
    id: string;
    invoice_number: string;
    invoice_date: string;
    due_date: string;
    currency: string;
    subtotal_amount: string;
    tax_amount: string;
    total_amount: string;
    status: string;
    lines: {
      id: string;
      po_line_id: string | null;
      item_code: string;
      description: string;
      uom: string;
      quantity: string;
      unit_price: string;
      tax_amount: string;
      line_total: string;
    }[];
  }[];
  current_status: string;
  latest_reconciliation: {
    run_id: string;
    outcome: string;
    rule_version: string;
    totals: Record<string, unknown>;
    completed_at: string;
    results: {
      id: string;
      entity_line_id: string;
      field_name: string;
      expected_value: string;
      actual_value: string;
      variance: string;
      tolerance_applied: string;
      breakdown: Record<string, unknown>;
      rule_id: string;
      result: string;
    }[];
  } | null;
  exceptions: {
    id: string;
    type: string;
    severity: string;
    status: string;
    rule_id: string;
    summary: string;
    version: number;
  }[];
  risk_signals: {
    id: string;
    signal_type: string;
    severity: string;
    score: string;
    reason: { reason_codes?: string[]; contributing_signals?: string[]; disclaimer?: string };
    label: string;
  }[];
}

export interface ExceptionCaseDetail {
  id: string;
  transaction_id: string;
  type: string;
  severity: string;
  status: string;
  owner_id: string | null;
  summary: string;
  affected_fields: string[];
  values: Record<string, string>;
  rule_id: string;
  evidence_refs: Record<string, string>[];
  version: number;
  created_at: string;
  comments: { id: string; author_id: string; body: string; is_clarification_request: boolean; created_at: string }[];
  approvals: { id: string; approver_id: string; decision: string; rationale: string; amount_evaluated: string; decided_at: string }[];
  investigations: { id: string; model_provider: string; model_name: string; confidence: number; structured_output: Record<string, any>; created_at: string }[];
}
