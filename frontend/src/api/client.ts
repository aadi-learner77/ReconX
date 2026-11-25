import type {
  ApiErrorEnvelope,
  DashboardSummary,
  DocumentItem,
  ExceptionCaseDetail,
  Paginated,
  TokenResponse,
  TransactionBundle,
  TransactionListItem,
  UserProfile,
} from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
const PREFIX = `${API_BASE}/api/v1`;

export class ApiClientError extends Error {
  code: string;
  status: number;
  correlationId: string;

  constructor(code: string, message: string, status: number, correlationId = "") {
    super(message);
    this.code = code;
    this.status = status;
    this.correlationId = correlationId;
  }
}

export function getAccessToken(): string | null {
  return localStorage.getItem("reconx_access_token");
}

export function setTokens(tokens: TokenResponse | null): void {
  if (!tokens) {
    localStorage.removeItem("reconx_access_token");
    localStorage.removeItem("reconx_refresh_token");
    return;
  }
  localStorage.setItem("reconx_access_token", tokens.access_token);
  localStorage.setItem("reconx_refresh_token", tokens.refresh_token);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getAccessToken();
  const headers = new Headers(init.headers || {});
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (!(init.body instanceof FormData) && !headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }
  const resp = await fetch(`${PREFIX}${path}`, { ...init, headers });
  if (!resp.ok) {
    let errBody: ApiErrorEnvelope | null = null;
    try {
      errBody = await resp.json();
    } catch {
      errBody = null;
    }
    throw new ApiClientError(
      errBody?.error?.code || "REQUEST_FAILED",
      errBody?.error?.message || `HTTP ${resp.status}`,
      resp.status,
      errBody?.error?.correlation_id || ""
    );
  }
  return resp.json() as Promise<T>;
}

export const api = {
  login: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  logout: (refreshToken: string | null) =>
    request<{ status: string }>("/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    }),
  me: () => request<UserProfile>("/auth/me"),
  dashboardSummary: () => request<DashboardSummary>("/dashboard/summary"),
  listDocuments: (page = 1) => request<Paginated<DocumentItem>>(`/documents?page=${page}&page_size=25`),
  getDocument: (id: string) => request<DocumentItem>(`/documents/${id}`),
  documentFileUrl: (id: string) => `${PREFIX}/documents/${id}/file`,
  uploadDocument: (file: File, hint?: string) => {
    const fd = new FormData();
    fd.append("file", file);
    if (hint) fd.append("document_type_hint", hint);
    return request<{ document_id: string; status: string; job_id: string; is_duplicate_file: boolean }>(
      "/documents",
      { method: "POST", body: fd }
    );
  },
  getJob: (jobId: string) =>
    request<{ job_id: string; status: string; last_error: string | null }>(`/jobs/${jobId}`),
  patchDocumentFields: (docId: string, corrections: { field_name: string; value: unknown }[]) =>
    request<DocumentItem>(`/documents/${docId}/fields`, {
      method: "PATCH",
      body: JSON.stringify({ corrections }),
    }),
  verifyDocument: (docId: string) =>
    request<{ document_id: string; entity_type: string; entity_id: string; transaction_id: string }>(
      `/documents/${docId}/verify`,
      { method: "POST" }
    ),
  linkDocument: (docId: string, poId: string) =>
    request<{ document_id: string; transaction_id: string }>(`/documents/${docId}/link`, {
      method: "POST",
      body: JSON.stringify({ po_id: poId }),
    }),
  listTransactions: (params: Record<string, string>) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== "" && v !== undefined)
    ).toString();
    return request<Paginated<TransactionListItem>>(`/transactions${qs ? `?${qs}` : ""}`);
  },
  getTransaction: (id: string) => request<TransactionBundle>(`/transactions/${id}`),
  reconcileTransaction: (id: string) =>
    request<{ run_id: string; outcome: string; exceptions: unknown[] }>(`/transactions/${id}/reconcile`, {
      method: "POST",
    }),
  getTransactionGraph: (id: string) =>
    request<{ nodes: any[]; edges: any[]; source: string }>(`/graph/transactions/${id}`),
  rebuildTransactionGraph: (id: string) =>
    request<{ nodes: any[]; edges: any[]; source: string }>(`/graph/transactions/${id}/rebuild`, {
      method: "POST",
    }),
  getObligationGraph: (id: string) =>
    request<{
      nodes: any[];
      edges: any[];
      summary: Record<string, string>;
      has_payment_records: boolean;
      source: string;
    }>(`/graph/obligations/${id}`),
  getAgentHarnessOverview: () => request<any>("/intelligence/agent-harness"),
  testGeminiConnection: () =>
    request<{
      connected: boolean;
      configured_provider: string;
      model: string;
      latency_ms: number;
      error_category: string;
      message: string;
    }>("/intelligence/gemini/test", { method: "POST" }),
  getTransactionRisk: (id: string) =>
    request<{ transaction_id: string; disclaimer: string; signals: any[] }>(`/transactions/${id}/risk`),
  listExceptions: (statusFilter = "") =>
    request<Paginated<ExceptionCaseDetail>>(
      `/exceptions${statusFilter ? `?status=${encodeURIComponent(statusFilter)}` : ""}`
    ),
  getException: (id: string) => request<ExceptionCaseDetail>(`/exceptions/${id}`),
  assignException: (id: string, ownerId: string) =>
    request<ExceptionCaseDetail>(`/exceptions/${id}/assign`, {
      method: "POST",
      body: JSON.stringify({ owner_id: ownerId }),
    }),
  addComment: (id: string, body: string, isClarification: boolean) =>
    request<any>(`/exceptions/${id}/comments`, {
      method: "POST",
      body: JSON.stringify({ body, is_clarification_request: isClarification }),
    }),
  decideException: (id: string, decision: string, rationale: string, version: number) =>
    request<{ case_id: string; status: string; version: number; audit_event_id: string }>(
      `/exceptions/${id}/decision`,
      {
        method: "POST",
        body: JSON.stringify({ decision, rationale, version }),
      }
    ),
  startInvestigation: (caseId: string) =>
    request<any>(`/exceptions/${caseId}/investigations`, { method: "POST" }),
  listVendors: () => request<Paginated<any>>("/vendors?page_size=50"),
  getVendorProfile: (id: string) => request<any>(`/vendors/${id}/profile`),
  listUsers: () => request<Paginated<any>>("/admin/users?page_size=50"),
  createUser: (payload: any) =>
    request<any>("/admin/users", { method: "POST", body: JSON.stringify(payload) }),
  getConfig: () => request<any>("/admin/config"),
  updateConfig: (configJson: Record<string, unknown>) =>
    request<any>("/admin/config", { method: "PUT", body: JSON.stringify({ config_json: configJson }) }),
  listTolerances: () => request<any[]>("/admin/tolerances"),
  upsertTolerance: (payload: any) =>
    request<any>("/admin/tolerances", { method: "POST", body: JSON.stringify(payload) }),
  listJobs: () => request<Paginated<any>>("/admin/jobs?page_size=50"),
  retryJob: (jobId: string) => request<any>(`/admin/jobs/${jobId}/retry`, { method: "POST" }),
  listAudit: (params: Record<string, string>) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== "" && v !== undefined)
    ).toString();
    return request<Paginated<any>>(`/audit${qs ? `?${qs}` : ""}`);
  },
  listNotifications: () => request<any[]>("/notifications"),
  markNotificationRead: (id: string) =>
    request<any>(`/notifications/${id}/read`, { method: "POST" }),
  copilotQuery: (question: string) =>
    request<{ answer: string; citations: any[]; read_only: boolean; limitations: string }>(
      "/copilot/query",
      { method: "POST", body: JSON.stringify({ question }) }
    ),
  cashObligations: () => request<any>("/analytics/cash-obligations"),
  exportReportUrl: (fmt: "csv" | "pdf") => `${PREFIX}/reports/export?format=${fmt}`,
  getPolicyMetadata: () => request<any>("/policies/metadata"),
  listPolicies: (params: Record<string, string> = {}) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== "" && v !== undefined)
    ).toString();
    return request<{ items: any[]; summary: Record<string, number> }>(
      `/policies${qs ? `?${qs}` : ""}`
    );
  },
  createPolicy: (payload: any) =>
    request<any>("/policies", { method: "POST", body: JSON.stringify(payload) }),
  updatePolicy: (id: string, payload: any) =>
    request<any>(`/policies/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  validatePolicy: (id: string) =>
    request<any>(`/policies/${id}/validate`, { method: "POST" }),
  activatePolicy: (id: string) =>
    request<any>(`/policies/${id}/activate`, { method: "POST" }),
  deactivatePolicy: (id: string) =>
    request<any>(`/policies/${id}/deactivate`, { method: "POST" }),
  clonePolicy: (id: string) =>
    request<any>(`/policies/${id}/clone`, { method: "POST" }),
  previewPolicyImpact: (payload: any) =>
    request<any>("/policies/preview", { method: "POST", body: JSON.stringify(payload) }),
  listPolicyVersions: (id: string) => request<any[]>(`/policies/${id}/versions`),
  listPolicyAudits: () => request<any[]>("/policy-audits"),
  startPolicyAudit: (payload: any = {}) =>
    request<any>("/policy-audits", { method: "POST", body: JSON.stringify(payload) }),
  getPolicyAuditResults: (id: string) => request<any>(`/policy-audits/${id}/results`),
  listExecutiveBriefs: () => request<any[]>("/executive-briefs"),
  generateExecutiveBrief: (payload: any) =>
    request<any>("/executive-briefs", { method: "POST", body: JSON.stringify(payload) }),
  getExecutiveBrief: (id: string) => request<any>(`/executive-briefs/${id}`),
  downloadExecutiveBrief: async (id: string, format: "pdf" | "markdown" | "csv") => {
    const token = getAccessToken();
    const resp = await fetch(`${PREFIX}/executive-briefs/${id}/download?format=${format}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!resp.ok) throw new ApiClientError("DOWNLOAD_FAILED", `HTTP ${resp.status}`, resp.status);
    return resp.blob();
  },
};
