import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Copy, Play, Plus, Sliders } from "lucide-react";
import { motion } from "framer-motion";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import {
  Badge,
  Button,
  Card,
  Modal,
  PageCaption,
  PageSkeleton,
  Stat,
  StatusPill,
  Toast,
} from "../components/ui";

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
    <div className="space-y-8">
      <Card variant="hero">
        <PageCaption
          module="Intelligence / Zero-Code Policy Hot-Swap"
          index="Deterministic DSL & Re-Audit"
        />
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500 mb-1">
              <Sliders className="w-3.5 h-3.5 text-ink-900" />
              <span>Versioned Financial &amp; Compliance Rules</span>
            </div>
            <h1 className="font-display text-3xl md:text-4xl font-bold text-ink-900">
              Policy Studio
            </h1>
            <p className="text-sm text-ink-700 mt-1">
              Create, validate, version, and hot-swap deterministic rules without code changes or
              restarts.
            </p>
          </div>
          <div className="flex flex-wrap gap-2.5">
            {hasPermission("policies:create") && (
              <Button
                variant="secondary"
                onClick={() => {
                  setEditingId(null);
                  setPolicyKey(`POL-CUSTOM-${Math.floor(100 + Math.random() * 900)}`);
                  setPreviewResult(null);
                  setEditorOpen(true);
                }}
              >
                <Plus className="w-4 h-4" />
                <span>Create Policy</span>
              </Button>
            )}
            {hasPermission("policies:audit") && (
              <Button onClick={() => setAuditConfirmOpen(true)}>
                <Play className="w-4 h-4" />
                <span>Re-Run Audit</span>
              </Button>
            )}
          </div>
        </div>
      </Card>

      {msg && <Toast message={msg} tone="success" onDismiss={() => setMsg(null)} />}
      {err && <Toast message={err} tone="danger" onDismiss={() => setErr(null)} />}

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Stat label="Total Policies" value={summary.total} />
        <Stat label="Active" value={summary.active} tone="success" />
        <Stat label="Draft" value={summary.draft} tone="warning" />
        <Stat label="Audit Runs" value={audits.length} />
      </div>

      {/* Two-Pane Workspace: Rules List | Rule Editor */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        <Card className={editorOpen ? "lg:col-span-7 space-y-4" : "lg:col-span-12 space-y-4"}>
          <div className="flex flex-wrap gap-2.5">
            <input
              aria-label="Search policies"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search policy key or name..."
              className="px-3 py-2 rounded-control border border-sand-200 bg-sand-50 text-xs text-ink-900 w-60"
            />
            <select
              aria-label="Filter category"
              value={catFilter}
              onChange={(e) => setCatFilter(e.target.value)}
              className="px-3 py-2 rounded-control border border-sand-200 text-xs bg-sand-50 text-ink-900"
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
              className="px-3 py-2 rounded-control border border-sand-200 text-xs bg-sand-50 text-ink-900"
            >
              <option value="">All Statuses</option>
              <option value="ACTIVE">ACTIVE</option>
              <option value="DRAFT">DRAFT</option>
              <option value="INACTIVE">INACTIVE</option>
            </select>
          </div>

          {isLoading ? (
            <PageSkeleton />
          ) : (
            <div className="overflow-x-auto rounded-card border border-sand-200">
              <table className="w-full text-xs text-left">
                <thead className="bg-sand-100 text-ink-500 border-b border-sand-200">
                  <tr>
                    <th scope="col" className="py-2.5 px-3">Policy ID</th>
                    <th scope="col" className="py-2.5 px-3">Name</th>
                    <th scope="col" className="py-2.5 px-3">Category</th>
                    <th scope="col" className="py-2.5 px-3">Severity</th>
                    <th scope="col" className="py-2.5 px-3">Status</th>
                    <th scope="col" className="py-2.5 px-3">Ver</th>
                    <th scope="col" className="py-2.5 px-3">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-sand-200">
                  {policies.map((p: any) => (
                    <tr key={p.id} className="hover:bg-sand-50">
                      <td className="py-2.5 px-3 font-mono font-semibold text-ink-900">
                        {p.policy_key}
                      </td>
                      <td className="py-2.5 px-3">
                        <div className="font-semibold text-ink-900">{p.name}</div>
                        <div className="text-ink-500">{p.description}</div>
                      </td>
                      <td className="py-2.5 px-3 font-mono">{p.category}</td>
                      <td className="py-2.5 px-3">
                        <StatusPill value={p.severity} />
                      </td>
                      <td className="py-2.5 px-3">
                        <StatusPill value={p.status} />
                      </td>
                      <td className="py-2.5 px-3 font-mono">
                        v{p.active_version || p.latest_version}
                      </td>
                      <td className="py-2.5 px-3 flex flex-wrap gap-1.5">
                        {hasPermission("policies:update") && (
                          <Button variant="outline" size="sm" onClick={() => openEdit(p)}>
                            Edit
                          </Button>
                        )}
                        {hasPermission("policies:activate") && p.status !== "ACTIVE" && (
                          <Button size="sm" onClick={() => activateMut.mutate(p.id)}>
                            Activate
                          </Button>
                        )}
                        {hasPermission("policies:activate") &&
                          p.status === "ACTIVE" &&
                          !p.is_system_policy && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => deactivateMut.mutate(p.id)}
                            >
                              Deactivate
                            </Button>
                          )}
                        {hasPermission("policies:create") && (
                          <Button variant="ghost" size="sm" onClick={() => cloneMut.mutate(p.id)}>
                            <Copy className="w-3 h-3" />
                            <span>Clone</span>
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={async () => {
                            const list = await api.listPolicyVersions(p.id);
                            setVersionsFor({ key: p.policy_key, list });
                          }}
                        >
                          Versions
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        {editorOpen && (
          <Card className="lg:col-span-12 space-y-5">
            <div className="flex flex-wrap justify-between items-center gap-3 border-b border-sand-200 pb-3">
              <div className="flex items-center gap-3">
                <h2 className="font-display text-lg font-bold text-ink-900">
                  {editingId ? `Edit Policy (${policyKey})` : "Create New Dynamic Policy"}
                </h2>
                <Badge
                  value={
                    editingId &&
                    policies.find((p: any) => p.id === editingId)?.status === "ACTIVE"
                      ? `Published · v${policies.find((p: any) => p.id === editingId)?.active_version}`
                      : "Draft"
                  }
                  tone={
                    editingId &&
                    policies.find((p: any) => p.id === editingId)?.status === "ACTIVE"
                      ? "success"
                      : "warning"
                  }
                />
              </div>
              <button
                type="button"
                onClick={() => setEditorOpen(false)}
                className="text-xs text-ink-500 hover:text-ink-900"
              >
                Close
              </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Left: Rule Builder */}
              <div className="space-y-4">
                <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">
                  Rule Builder — Condition Rows &amp; Scope Chips
                </div>
                <div className="flex flex-wrap items-center gap-1.5">
                  <Badge value={`IF ${field}`} tone="info" />
                  <Badge value={operator} tone="neutral" />
                  <Badge value={thresholdVal || "0"} tone="warning" />
                  <Badge value={`THEN ${exceptionType}`} tone="danger" />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  <label className="space-y-1">
                    <span className="block text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">
                      Policy Key
                    </span>
                    <input
                      aria-label="Policy Key"
                      value={policyKey}
                      disabled={Boolean(editingId)}
                      onChange={(e) => setPolicyKey(e.target.value)}
                      className="w-full px-3 py-2 rounded-control border border-sand-200 bg-sand-50 font-mono"
                    />
                  </label>
                  <label className="space-y-1">
                    <span className="block text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">
                      Severity
                    </span>
                    <select
                      aria-label="Severity"
                      value={severity}
                      onChange={(e) => setSeverity(e.target.value)}
                      className="w-full px-3 py-2 rounded-control border border-sand-200 bg-sand-50"
                    >
                      <option value="LOW">LOW</option>
                      <option value="MEDIUM">MEDIUM</option>
                      <option value="HIGH">HIGH</option>
                      <option value="CRITICAL">CRITICAL</option>
                    </select>
                  </label>
                  <label className="space-y-1 sm:col-span-2">
                    <span className="block text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">
                      Policy Name
                    </span>
                    <input
                      aria-label="Policy Name"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="w-full px-3 py-2 rounded-control border border-sand-200 bg-sand-50"
                    />
                  </label>
                  <label className="space-y-1">
                    <span className="block text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">
                      Category
                    </span>
                    <select
                      aria-label="Category"
                      value={category}
                      onChange={(e) => setCategory(e.target.value)}
                      className="w-full px-3 py-2 rounded-control border border-sand-200 bg-sand-50"
                    >
                      <option value="FINANCIAL">FINANCIAL</option>
                      <option value="PROCUREMENT">PROCUREMENT</option>
                      <option value="COMPLIANCE">COMPLIANCE</option>
                      <option value="VENDOR">VENDOR</option>
                      <option value="DUPLICATE">DUPLICATE</option>
                    </select>
                  </label>
                  <label className="space-y-1">
                    <span className="block text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">
                      Condition Metric
                    </span>
                    <select
                      aria-label="Rule Field"
                      value={field}
                      onChange={(e) => setField(e.target.value)}
                      className="w-full px-3 py-2 rounded-control border border-sand-200 bg-sand-50 font-mono"
                    >
                      {allowedFields.map((f) => (
                        <option key={f} value={f}>
                          IF {f}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="space-y-1">
                    <span className="block text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">
                      Operator
                    </span>
                    <select
                      aria-label="Operator"
                      value={operator}
                      onChange={(e) => setOperator(e.target.value)}
                      className="w-full px-3 py-2 rounded-control border border-sand-200 bg-sand-50 font-mono"
                    >
                      {allowedOps.map((op: string) => (
                        <option key={op} value={op}>
                          {op}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="space-y-1">
                    <span className="block text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">
                      Threshold Value
                    </span>
                    <input
                      aria-label="Threshold Value"
                      value={thresholdVal}
                      onChange={(e) => setThresholdVal(e.target.value)}
                      className="w-full px-3 py-2 rounded-control border border-sand-200 bg-sand-50 font-mono"
                    />
                  </label>
                </div>

                <label className="block space-y-1 text-xs">
                  <span className="block text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">
                    Rule Description &amp; Investigation Guidance
                  </span>
                  <input
                    aria-label="Policy Description"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    className="w-full px-3 py-2 rounded-control border border-sand-200 bg-sand-50 text-xs"
                  />
                </label>

                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => previewMut.mutate()}
                    disabled={previewMut.isPending}
                  >
                    Preview Policy Impact (Dry-Run)
                  </Button>
                  <Button size="sm" onClick={() => saveMut.mutate()} disabled={saveMut.isPending}>
                    Save Policy Version
                  </Button>
                </div>
              </div>

              {/* Right: Live JSON/DSL Preview + Re-Audit Impact */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">
                    Live JSON / Constrained DSL Preview
                  </span>
                  <span className="font-mono text-[11px] text-ink-500">Deterministic Schema</span>
                </div>
                <pre className="p-4 rounded-card bg-sand-100 border border-sand-200 font-mono text-[11px] text-ink-900 overflow-x-auto leading-relaxed">
                  {JSON.stringify(buildDef(), null, 2)}
                </pre>

                <div className="p-4 rounded-card bg-sand-50 border border-sand-200 text-xs space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="font-display font-bold text-ink-900">Re-Audit Impact</span>
                    <Badge
                      value={previewResult ? "Dry-Run Ready" : "Click Preview Impact"}
                      tone={previewResult ? "info" : "neutral"}
                    />
                  </div>
                  {previewResult ? (
                    <div className="space-y-2.5">
                      <div className="font-bold text-ink-900">
                        Dry-Run Projection — Scanned {previewResult.records_scanned} | Matching{" "}
                        {previewResult.records_matching} | Potential New:{" "}
                        {previewResult.potential_new_exceptions}
                      </div>
                      <div className="space-y-2">
                        <div>
                          <div className="flex justify-between font-mono text-[11px] text-ink-500 mb-1">
                            <span>Before (Existing Exceptions)</span>
                            <span>
                              {Math.max(
                                0,
                                (previewResult.records_matching || 0) -
                                  (previewResult.potential_new_exceptions || 0)
                              )}
                            </span>
                          </div>
                          <div className="h-2 rounded-full bg-sand-200 overflow-hidden">
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{
                                width: `${
                                  previewResult.records_scanned > 0
                                    ? Math.min(
                                        100,
                                        Math.round(
                                          (Math.max(
                                            0,
                                            (previewResult.records_matching || 0) -
                                              (previewResult.potential_new_exceptions || 0)
                                          ) /
                                            previewResult.records_scanned) *
                                            100
                                        )
                                      )
                                    : 0
                                }%`,
                              }}
                              transition={{ duration: 0.45 }}
                              className="h-full bg-ink-700 rounded-full"
                            />
                          </div>
                        </div>
                        <div>
                          <div className="flex justify-between font-mono text-[11px] text-status-danger-fg mb-1">
                            <span>After (Projected Total Matching)</span>
                            <span>{previewResult.records_matching}</span>
                          </div>
                          <div className="h-2 rounded-full bg-sand-200 overflow-hidden">
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{
                                width: `${
                                  previewResult.records_scanned > 0
                                    ? Math.min(
                                        100,
                                        Math.round(
                                          ((previewResult.records_matching || 0) /
                                            previewResult.records_scanned) *
                                            100
                                        )
                                      )
                                    : 0
                                }%`,
                              }}
                              transition={{ duration: 0.55 }}
                              className="h-full bg-status-danger-fg rounded-full"
                            />
                          </div>
                        </div>
                      </div>
                      <div className="font-mono text-[11px] text-ink-500">
                        Content Hash: {previewResult.content_hash}
                      </div>
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        {(previewResult.affected_transactions || []).slice(0, 8).map((tx: any) => (
                          <Link
                            key={tx.transaction_id}
                            to={`/transactions/${tx.transaction_id}`}
                            className="px-2 py-0.5 rounded-full bg-paper border border-sand-200 font-mono text-ink-900 underline"
                          >
                            {tx.po_number}
                          </Link>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="text-ink-500">
                      Run &ldquo;Preview Policy Impact (Dry-Run)&rdquo; to compare before/after exception counts.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </Card>
        )}
      </div>

      {versionsFor && (
        <Card className="space-y-3">
          <div className="flex justify-between items-center">
            <h3 className="font-display text-base font-bold text-ink-900">
              Immutable Version History — {versionsFor.key}
            </h3>
            <button
              type="button"
              onClick={() => setVersionsFor(null)}
              className="text-xs text-ink-500 hover:text-ink-900"
            >
              Close
            </button>
          </div>
          {versionsFor.list.map((v) => (
            <div
              key={v.id}
              className="p-3 rounded-control bg-sand-50 border border-sand-200 text-xs flex flex-wrap justify-between gap-2"
            >
              <div className="flex items-center gap-2">
                <span className="font-mono font-bold">v{v.version_number}</span>
                {v.is_active && <StatusPill value="ACTIVE" />}
                <span className="text-ink-700">{v.change_summary}</span>
              </div>
              <div className="font-mono text-ink-500">hash: {v.content_hash.slice(0, 16)}</div>
            </div>
          ))}
        </Card>
      )}

      <Modal
        open={auditConfirmOpen}
        onClose={() => setAuditConfirmOpen(false)}
        title="Confirm Historical Re-Audit"
        footer={
          <>
            <Button variant="outline" size="sm" onClick={() => setAuditConfirmOpen(false)}>
              Cancel
            </Button>
            <Button size="sm" onClick={() => auditMut.mutate()} disabled={auditMut.isPending}>
              {auditMut.isPending ? "Running..." : "Confirm Re-Run Audit"}
            </Button>
          </>
        }
      >
        This will evaluate all eligible historical organization transactions against the currently
        active policy versions and may create new exception cases.
      </Modal>

      {(auditResults || audits.length > 0) && (
        <Card className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="font-display text-lg font-bold text-ink-900">Policy Re-Audit Runs</h2>
            <div className="flex flex-wrap gap-2">
              {audits.slice(0, 5).map((r: any) => (
                <button
                  key={r.id}
                  type="button"
                  onClick={() => setActiveAuditId(r.id)}
                  className={`px-3 py-1.5 rounded-full border text-xs font-mono ${
                    activeAuditId === r.id
                      ? "bg-ink-900 text-on-ink border-ink-900 font-semibold"
                      : "border-sand-200 bg-sand-50 text-ink-700"
                  }`}
                >
                  {r.status} • Scanned {r.transactions_scanned} • New {r.new_exceptions}
                </button>
              ))}
            </div>
          </div>
          {auditResults && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
              <div className="p-3.5 rounded-card bg-status-danger-bg/60 border border-status-danger-fg/30">
                <div className="font-bold text-status-danger-fg mb-2">
                  Newly Flagged ({(auditResults.newly_flagged || []).length})
                </div>
                {(auditResults.newly_flagged || []).map((item: any, i: number) => (
                  <div key={i} className="mb-1.5 font-mono">
                    <Link to={`/transactions/${item.transaction_id}`} className="font-semibold underline">
                      {item.po_number}
                    </Link>{" "}
                    ({item.policy_key} v{item.policy_version})
                  </div>
                ))}
              </div>
              <div className="p-3.5 rounded-card bg-status-warning-bg/60 border border-status-warning-fg/30">
                <div className="font-bold text-status-warning-fg mb-2">
                  Existing Violations ({(auditResults.existing_violations || []).length})
                </div>
                {(auditResults.existing_violations || []).slice(0, 8).map((item: any, i: number) => (
                  <div key={i} className="mb-1.5 font-mono">
                    <Link to={`/transactions/${item.transaction_id}`} className="font-semibold underline">
                      {item.po_number}
                    </Link>{" "}
                    ({item.policy_key} v{item.policy_version})
                  </div>
                ))}
              </div>
              <div className="p-3.5 rounded-card bg-status-success-bg/60 border border-status-success-fg/30">
                <div className="font-bold text-status-success-fg mb-2">
                  No Longer Triggered ({(auditResults.resolved_or_not_triggered || []).length})
                </div>
                <div className="text-ink-700">
                  Prior policy exceptions no longer triggered under active policy rules.
                </div>
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
  );
};
