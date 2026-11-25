import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Copy, Play, Plus, ShieldCheck, Sliders } from "lucide-react";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { StatusBadge } from "../components/StatusBadge";

export const PolicyStudioPage: React.FC = () => {
  const qc = useQueryClient();
  const { hasPermission } = useAuth();
  const [search, setSearch] = useState("");
  const [catFilter, setCatFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const [editorOpen, setEditorOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [policyKey, setPolicyKey] = useState("POL-CUSTOM-002");
  const [name, setName] = useState("Invoice Over-Billing Threshold");
  const [description, setDescription] = useState("Detect invoices exceeding accepted GRN qty.");
  const [category, setCategory] = useState("FINANCIAL");
  const [severity, setSeverity] = useState("HIGH");
  const [field, setField] = useState("variance.qty_diff");
  const [operator, setOperator] = useState("gt");
  const [thresholdVal, setThresholdVal] = useState("5");
  const [exceptionType, setExceptionType] = useState("POLICY_VIOLATION");

  const [previewResult, setPreviewResult] = useState<any | null>(null);
  const [versionsFor, setVersionsFor] = useState<{ key: string; list: any[] } | null>(null);
  const [auditConfirmOpen, setAuditConfirmOpen] = useState(false);
  const [activeAuditId, setActiveAuditId] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const { data: meta } = useQuery({
    queryKey: ["policy-metadata"],
    queryFn: api.getPolicyMetadata,
  });
  const { data: polData, isLoading } = useQuery({
    queryKey: ["policies", search, catFilter, statusFilter],
    queryFn: () =>
      api.listPolicies({ q: search, category: catFilter, status_filter: statusFilter }),
  });
  const { data: audits = [] } = useQuery({
    queryKey: ["policy-audits"],
    queryFn: api.listPolicyAudits,
  });
  const { data: auditResults } = useQuery({
    queryKey: ["policy-audit-results", activeAuditId],
    queryFn: () => api.getPolicyAuditResults(activeAuditId!),
    enabled: Boolean(activeAuditId),
  });

  const buildDef = () => ({
    scope: { document_types: ["PURCHASE_ORDER", "GOODS_RECEIPT", "INVOICE"] },
    condition: {
      field,
      operator,
      value: field.includes("is_duplicate") || field.includes("has_pending")
        ? thresholdVal === "true"
        : thresholdVal,
    },
    action: {
      type: "CREATE_EXCEPTION",
      exception_type: exceptionType,
      instructions: description,
    },
  });

  const saveMut = useMutation({
    mutationFn: () =>
      editingId
        ? api.updatePolicy(editingId, {
            name,
            description,
            category,
            severity,
            definition: buildDef(),
            change_summary: "Updated via Policy Studio",
          })
        : api.createPolicy({
            policy_key: policyKey,
            name,
            description,
            category,
            severity,
            definition: buildDef(),
          }),
    onSuccess: (res) => {
      setErr(null);
      setMsg(`Saved policy ${res.policy_key} (v${res.latest_version}).`);
      setEditorOpen(false);
      qc.invalidateQueries({ queryKey: ["policies"] });
    },
    onError: (e: any) => setErr(e.message),
  });

  const previewMut = useMutation({
    mutationFn: () =>
      api.previewPolicyImpact({
        policy_key: policyKey,
        severity,
        definition: buildDef(),
      }),
    onSuccess: (res) => {
      setErr(null);
      setPreviewResult(res);
    },
    onError: (e: any) => setErr(e.message),
  });

  const activateMut = useMutation({
    mutationFn: (id: string) => api.activatePolicy(id),
    onSuccess: (res) => {
      setErr(null);
      setMsg(`Activated ${res.policy_key} v${res.active_version} (hash ${res.content_hash.slice(0, 10)}).`);
      qc.invalidateQueries({ queryKey: ["policies"] });
    },
    onError: (e: any) => setErr(e.message),
  });

  const deactivateMut = useMutation({
    mutationFn: (id: string) => api.deactivatePolicy(id),
    onSuccess: (res) => {
      setErr(null);
      setMsg(`Deactivated ${res.policy_key}.`);
      qc.invalidateQueries({ queryKey: ["policies"] });
    },
    onError: (e: any) => setErr(e.message),
  });

  const cloneMut = useMutation({
    mutationFn: (id: string) => api.clonePolicy(id),
    onSuccess: (res) => {
      setMsg(`Cloned policy as ${res.policy_key}.`);
      qc.invalidateQueries({ queryKey: ["policies"] });
    },
  });

  const auditMut = useMutation({
    mutationFn: () => api.startPolicyAudit({}),
    onSuccess: (res) => {
      setAuditConfirmOpen(false);
      setActiveAuditId(res.id);
      setMsg(
        `Re-Audit ${res.status}: scanned ${res.transactions_scanned} transactions, ${res.new_exceptions} new exception(s).`
      );
      qc.invalidateQueries({ queryKey: ["policy-audits"] });
      qc.invalidateQueries({ queryKey: ["exceptions"] });
      qc.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
    onError: (e: any) => setErr(e.message),
  });

  const summary = polData?.summary || { total: 0, active: 0, inactive: 0, draft: 0 };
  const policies = polData?.items || [];
  const allowedFields = Object.keys(meta?.allowed_fields || { "variance.qty_diff": "decimal" });
  const allowedOps = meta?.allowed_operators || ["gt", "gte", "lt", "lte", "eq", "ne"];

  const openEdit = (p: any) => {
    setEditingId(p.id);
    setPolicyKey(p.policy_key);
    setName(p.name);
    setDescription(p.description);
    setCategory(p.category);
    setSeverity(p.severity);
    const cond = p.definition?.condition || {};
    if (cond.field) setField(cond.field);
    if (cond.operator) setOperator(cond.operator);
    if (cond.value !== undefined) setThresholdVal(String(cond.value));
    if (p.definition?.action?.exception_type) setExceptionType(p.definition.action.exception_type);
    setPreviewResult(null);
    setEditorOpen(true);
  };

  return (
    <div className="space-y-6">
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-indigo-600 mb-1">
            <Sliders className="w-3.5 h-3.5" />
            <span>Intelligence • Zero-Code Policy Hot-Swap</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900">Policy Studio</h1>
          <p className="text-sm text-slate-600 mt-1">
            Create, validate, version, and hot-swap deterministic financial &amp; compliance rules
            without code changes or restarts.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {hasPermission("policies:create") && (
            <button
              type="button"
              onClick={() => {
                setEditingId(null);
                setPolicyKey(`POL-CUSTOM-${Math.floor(100 + Math.random() * 900)}`);
                setPreviewResult(null);
                setEditorOpen(true);
              }}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-slate-300 bg-white text-sm font-semibold text-slate-800 hover:bg-slate-50"
            >
              <Plus className="w-4 h-4" />
              <span>Create Policy</span>
            </button>
          )}
          {hasPermission("policies:audit") && (
            <button
              type="button"
              onClick={() => setAuditConfirmOpen(true)}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-semibold hover:bg-indigo-700"
            >
              <Play className="w-4 h-4" />
              <span>Re-Run Audit</span>
            </button>
          )}
        </div>
      </div>

      {msg && (
        <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-xs text-emerald-800">
          {msg}
        </div>
      )}
      {err && (
        <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-800">
          {err}
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-4 bg-white border border-slate-200 rounded-xl">
          <div className="text-xs text-slate-500">Total Policies</div>
          <div className="text-2xl font-bold text-slate-900">{summary.total}</div>
        </div>
        <div className="p-4 bg-white border border-slate-200 rounded-xl">
          <div className="text-xs text-slate-500">Active</div>
          <div className="text-2xl font-bold text-emerald-700">{summary.active}</div>
        </div>
        <div className="p-4 bg-white border border-slate-200 rounded-xl">
          <div className="text-xs text-slate-500">Draft</div>
          <div className="text-2xl font-bold text-amber-700">{summary.draft}</div>
        </div>
        <div className="p-4 bg-white border border-slate-200 rounded-xl">
          <div className="text-xs text-slate-500">Audit Runs</div>
          <div className="text-2xl font-bold text-indigo-700">{audits.length}</div>
        </div>
      </div>

      {/* Policy Editor & Dry-Run Impact Preview */}
      {editorOpen && (
        <div className="bg-white border border-indigo-200 rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-sm font-bold text-slate-900">
              {editingId ? `Edit Policy (${policyKey})` : "Create New Dynamic Policy"}
            </h2>
            <button
              type="button"
              onClick={() => setEditorOpen(false)}
              className="text-xs text-slate-500 hover:text-slate-800"
            >
              Close
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs">
            <input
              aria-label="Policy Key"
              value={policyKey}
              disabled={Boolean(editingId)}
              onChange={(e) => setPolicyKey(e.target.value)}
              placeholder="POL-CUSTOM-002"
              className="px-3 py-2 rounded-lg border border-slate-300"
            />
            <input
              aria-label="Policy Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Policy Name"
              className="px-3 py-2 rounded-lg border border-slate-300 md:col-span-2"
            />
            <select
              aria-label="Severity"
              value={severity}
              onChange={(e) => setSeverity(e.target.value)}
              className="px-3 py-2 rounded-lg border border-slate-300 bg-white"
            >
              <option value="LOW">LOW</option>
              <option value="MEDIUM">MEDIUM</option>
              <option value="HIGH">HIGH</option>
              <option value="CRITICAL">CRITICAL</option>
            </select>
            <select
              aria-label="Category"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="px-3 py-2 rounded-lg border border-slate-300 bg-white"
            >
              <option value="FINANCIAL">FINANCIAL</option>
              <option value="PROCUREMENT">PROCUREMENT</option>
              <option value="COMPLIANCE">COMPLIANCE</option>
              <option value="VENDOR">VENDOR</option>
              <option value="DUPLICATE">DUPLICATE</option>
            </select>
            <select
              aria-label="Rule Field"
              value={field}
              onChange={(e) => setField(e.target.value)}
              className="px-3 py-2 rounded-lg border border-slate-300 bg-white"
            >
              {allowedFields.map((f) => (
                <option key={f} value={f}>
                  IF {f}
                </option>
              ))}
            </select>
            <select
              aria-label="Operator"
              value={operator}
              onChange={(e) => setOperator(e.target.value)}
              className="px-3 py-2 rounded-lg border border-slate-300 bg-white"
            >
              {allowedOps.map((op: string) => (
                <option key={op} value={op}>
                  {op}
                </option>
              ))}
            </select>
            <input
              aria-label="Threshold Value"
              value={thresholdVal}
              onChange={(e) => setThresholdVal(e.target.value)}
              placeholder="Threshold (e.g. 5)"
              className="px-3 py-2 rounded-lg border border-slate-300"
            />
          </div>
          <input
            aria-label="Policy Description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Description & investigation guidance"
            className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs"
          />
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => previewMut.mutate()}
              disabled={previewMut.isPending}
              className="px-3 py-1.5 rounded-lg border border-indigo-300 text-indigo-700 text-xs font-semibold hover:bg-indigo-50"
            >
              Preview Policy Impact (Dry-Run)
            </button>
            <button
              type="button"
              onClick={() => saveMut.mutate()}
              disabled={saveMut.isPending}
              className="px-4 py-1.5 rounded-lg bg-indigo-600 text-white text-xs font-semibold hover:bg-indigo-700"
            >
              Save Policy Version
            </button>
          </div>
          {previewResult && (
            <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs space-y-1">
              <div className="font-bold text-slate-900">
                Dry-Run Projection (No Exceptions Created) — Scanned {previewResult.records_scanned} |
                Matching {previewResult.records_matching} | Potential New:{" "}
                {previewResult.potential_new_exceptions}
              </div>
              <div className="font-mono text-[11px] text-slate-500">
                Content Hash: {previewResult.content_hash}
              </div>
              <div className="flex flex-wrap gap-2 pt-1">
                {(previewResult.affected_transactions || []).slice(0, 8).map((tx: any) => (
                  <Link
                    key={tx.transaction_id}
                    to={`/transactions/${tx.transaction_id}`}
                    className="px-2 py-0.5 rounded bg-white border border-slate-300 text-indigo-700 hover:underline"
                  >
                    {tx.po_number}
                  </Link>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Policy Table */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3">
        <div className="flex flex-wrap gap-2">
          <input
            aria-label="Search policies"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search policy key or name..."
            className="px-3 py-1.5 rounded-lg border border-slate-300 text-xs w-60"
          />
          <select
            aria-label="Filter category"
            value={catFilter}
            onChange={(e) => setCatFilter(e.target.value)}
            className="px-3 py-1.5 rounded-lg border border-slate-300 text-xs bg-white"
          >
            <option value="">All Categories</option>
            <option value="FINANCIAL">FINANCIAL</option>
            <option value="DUPLICATE">DUPLICATE</option>
            <option value="COMPLIANCE">COMPLIANCE</option>
          </select>
          <select
            aria-label="Filter status"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 rounded-lg border border-slate-300 text-xs bg-white"
          >
            <option value="">All Statuses</option>
            <option value="ACTIVE">ACTIVE</option>
            <option value="DRAFT">DRAFT</option>
            <option value="INACTIVE">INACTIVE</option>
          </select>
        </div>

        {isLoading ? (
          <div className="text-xs text-slate-500">Loading policies...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
                <tr>
                  <th className="py-2 px-3">Policy ID</th>
                  <th className="py-2 px-3">Name</th>
                  <th className="py-2 px-3">Category</th>
                  <th className="py-2 px-3">Severity</th>
                  <th className="py-2 px-3">Status</th>
                  <th className="py-2 px-3">Version</th>
                  <th className="py-2 px-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {policies.map((p: any) => (
                  <tr key={p.id}>
                    <td className="py-2 px-3 font-mono font-semibold text-slate-900">
                      {p.policy_key}
                    </td>
                    <td className="py-2 px-3">
                      <div className="font-semibold text-slate-900">{p.name}</div>
                      <div className="text-slate-500">{p.description}</div>
                    </td>
                    <td className="py-2 px-3">{p.category}</td>
                    <td className="py-2 px-3">
                      <StatusBadge value={p.severity} />
                    </td>
                    <td className="py-2 px-3">
                      <StatusBadge value={p.status} />
                    </td>
                    <td className="py-2 px-3 font-mono">
                      v{p.active_version || p.latest_version}
                    </td>
                    <td className="py-2 px-3 flex flex-wrap gap-1.5">
                      {hasPermission("policies:update") && (
                        <button
                          type="button"
                          onClick={() => openEdit(p)}
                          className="px-2 py-1 rounded border border-slate-300 hover:bg-slate-50"
                        >
                          Edit
                        </button>
                      )}
                      {hasPermission("policies:activate") && p.status !== "ACTIVE" && (
                        <button
                          type="button"
                          onClick={() => activateMut.mutate(p.id)}
                          className="px-2 py-1 rounded bg-emerald-600 text-white hover:bg-emerald-700"
                        >
                          Activate
                        </button>
                      )}
                      {hasPermission("policies:activate") &&
                        p.status === "ACTIVE" &&
                        !p.is_system_policy && (
                          <button
                            type="button"
                            onClick={() => deactivateMut.mutate(p.id)}
                            className="px-2 py-1 rounded bg-amber-600 text-white hover:bg-amber-700"
                          >
                            Deactivate
                          </button>
                        )}
                      {hasPermission("policies:create") && (
                        <button
                          type="button"
                          onClick={() => cloneMut.mutate(p.id)}
                          className="inline-flex items-center gap-1 px-2 py-1 rounded border border-slate-300 hover:bg-slate-50"
                        >
                          <Copy className="w-3 h-3" />
                          <span>Clone</span>
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={async () => {
                          const list = await api.listPolicyVersions(p.id);
                          setVersionsFor({ key: p.policy_key, list });
                        }}
                        className="px-2 py-1 rounded border border-slate-300 hover:bg-slate-50"
                      >
                        Versions
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {versionsFor && (
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-2">
          <div className="flex justify-between items-center">
            <h3 className="text-sm font-semibold text-slate-900">
              Immutable Version History — {versionsFor.key}
            </h3>
            <button
              type="button"
              onClick={() => setVersionsFor(null)}
              className="text-xs text-slate-500"
            >
              Close
            </button>
          </div>
          {versionsFor.list.map((v) => (
            <div
              key={v.id}
              className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-xs flex flex-wrap justify-between gap-2"
            >
              <div>
                <span className="font-bold">v{v.version_number}</span>{" "}
                {v.is_active && (
                  <span className="px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 font-semibold">
                    ACTIVE
                  </span>
                )}{" "}
                — {v.change_summary}
              </div>
              <div className="font-mono text-slate-500">hash: {v.content_hash.slice(0, 16)}</div>
            </div>
          ))}
        </div>
      )}

      {/* Re-Run Audit Confirmation Modal */}
      {auditConfirmOpen && (
        <div className="fixed inset-0 bg-slate-900/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl p-5 max-w-md w-full space-y-3 shadow-xl">
            <div className="flex items-center gap-2 text-indigo-700 font-bold text-sm">
              <ShieldCheck className="w-4 h-4" />
              <span>Confirm Historical Re-Audit</span>
            </div>
            <p className="text-xs text-slate-600">
              This will evaluate all eligible historical organization transactions against the
              currently active policy versions and may create new exception cases.
            </p>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setAuditConfirmOpen(false)}
                className="px-3 py-1.5 rounded-lg border border-slate-300 text-xs"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => auditMut.mutate()}
                disabled={auditMut.isPending}
                className="px-4 py-1.5 rounded-lg bg-indigo-600 text-white text-xs font-semibold hover:bg-indigo-700"
              >
                {auditMut.isPending ? "Running..." : "Confirm Re-Run Audit"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Re-Audit Results */}
      {(auditResults || audits.length > 0) && (
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-sm font-semibold text-slate-900">Policy Re-Audit Runs</h2>
            <div className="flex flex-wrap gap-2">
              {audits.slice(0, 5).map((r: any) => (
                <button
                  key={r.id}
                  type="button"
                  onClick={() => setActiveAuditId(r.id)}
                  className={`px-2.5 py-1 rounded border text-xs ${
                    activeAuditId === r.id
                      ? "border-indigo-500 bg-indigo-50 text-indigo-800 font-semibold"
                      : "border-slate-200 text-slate-700"
                  }`}
                >
                  {r.status} • Scanned {r.transactions_scanned} • New {r.new_exceptions}
                </button>
              ))}
            </div>
          </div>
          {auditResults && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
              <div className="p-3 rounded-lg bg-rose-50/50 border border-rose-200">
                <div className="font-bold text-rose-900 mb-2">
                  Newly Flagged ({(auditResults.newly_flagged || []).length})
                </div>
                {(auditResults.newly_flagged || []).map((item: any, i: number) => (
                  <div key={i} className="mb-1.5">
                    <Link
                      to={`/transactions/${item.transaction_id}`}
                      className="font-semibold text-indigo-700 hover:underline"
                    >
                      {item.po_number}
                    </Link>{" "}
                    ({item.policy_key} v{item.policy_version})
                  </div>
                ))}
              </div>
              <div className="p-3 rounded-lg bg-amber-50/50 border border-amber-200">
                <div className="font-bold text-amber-900 mb-2">
                  Existing Violations ({(auditResults.existing_violations || []).length})
                </div>
                {(auditResults.existing_violations || []).slice(0, 8).map((item: any, i: number) => (
                  <div key={i} className="mb-1.5">
                    <Link
                      to={`/transactions/${item.transaction_id}`}
                      className="font-semibold text-indigo-700 hover:underline"
                    >
                      {item.po_number}
                    </Link>{" "}
                    ({item.policy_key} v{item.policy_version})
                  </div>
                ))}
              </div>
              <div className="p-3 rounded-lg bg-emerald-50/50 border border-emerald-200">
                <div className="font-bold text-emerald-900 mb-2">
                  No Longer Triggered ({(auditResults.no_longer_triggered || []).length})
                </div>
                {(auditResults.no_longer_triggered || []).map((item: any, i: number) => (
                  <div key={i} className="mb-1.5">
                    {item.po_number} ({item.policy_key})
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
