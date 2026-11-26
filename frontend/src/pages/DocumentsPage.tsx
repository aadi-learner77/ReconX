import React, { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { ShieldAlert, Trash2, UploadCloud } from "lucide-react";
import { api, getAccessToken } from "../api/client";
import type { DocumentItem, ExtractedFieldItem } from "../api/types";
import {
  Button,
  Card,
  ConfidenceMeter,
  EmptyState,
  PageCaption,
  PageSkeleton,
  StatusPill,
  Toast,
} from "../components/ui";

export const DocumentsPage: React.FC = () => {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [hint, setHint] = useState<string>("");
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [previewPage, setPreviewPage] = useState<number>(1);
  const [previewBlobUrl, setPreviewBlobUrl] = useState<string | null>(null);
  const [banner, setBanner] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const { data: listData, isLoading } = useQuery({
    queryKey: ["documents"],
    queryFn: () => api.listDocuments(1),
  });

  const { data: docDetail } = useQuery({
    queryKey: ["document", selectedDocId],
    queryFn: () => api.getDocument(selectedDocId!),
    enabled: Boolean(selectedDocId),
  });

  const { data: jobStatus } = useQuery({
    queryKey: ["job", activeJobId],
    queryFn: () => api.getJob(activeJobId!),
    enabled: Boolean(activeJobId),
    refetchInterval: (query) => {
      const st = query.state.data?.status;
      return st === "QUEUED" || st === "PROCESSING" ? 1000 : false;
    },
  });

  useEffect(() => {
    if (jobStatus && (jobStatus.status === "SUCCEEDED" || jobStatus.status === "FAILED")) {
      qc.invalidateQueries({ queryKey: ["documents"] });
      if (selectedDocId) qc.invalidateQueries({ queryKey: ["document", selectedDocId] });
      setActiveJobId(null);
    }
  }, [jobStatus, qc, selectedDocId]);

  useEffect(() => {
    let revoked = false;
    let url: string | null = null;
    if (!selectedDocId || !docDetail) {
      setPreviewBlobUrl(null);
      return;
    }
    const token = getAccessToken();
    fetch(api.documentFileUrl(selectedDocId), {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((r) => (r.ok ? r.blob() : null))
      .then((blob) => {
        if (blob && !revoked) {
          url = URL.createObjectURL(blob);
          setPreviewBlobUrl(url);
        }
      })
      .catch(() => setPreviewBlobUrl(null));
    return () => {
      revoked = true;
      if (url) URL.revokeObjectURL(url);
    };
  }, [selectedDocId, docDetail?.document_id]);

  const uploadMut = useMutation({
    mutationFn: (file: File) => api.uploadDocument(file, hint || undefined),
    onSuccess: (res) => {
      setSelectedDocId(res.document_id);
      setActiveJobId(res.job_id);
      setBanner(
        res.is_duplicate_file
          ? "Exact file checksum duplicate detected — review flagged."
          : `Uploaded document queued (Job ${res.job_id.slice(0, 8)}).`
      );
      qc.invalidateQueries({ queryKey: ["documents"] });
    },
  });

  const patchMut = useMutation({
    mutationFn: (corrections: { field_name: string; value: unknown }[]) =>
      api.patchDocumentFields(selectedDocId!, corrections),
    onSuccess: () => {
      setEdits({});
      setBanner("Field correction saved with audit trail.");
      qc.invalidateQueries({ queryKey: ["document", selectedDocId] });
      qc.invalidateQueries({ queryKey: ["documents"] });
    },
  });

  const verifyMut = useMutation({
    mutationFn: () => api.verifyDocument(selectedDocId!),
    onSuccess: (res) => {
      setBanner(`Committed ${res.entity_type} (${res.entity_id.slice(0, 8)}).`);
      qc.invalidateQueries({ queryKey: ["document", selectedDocId] });
      qc.invalidateQueries({ queryKey: ["documents"] });
    },
  });

  const linkMut = useMutation({
    mutationFn: (poId: string) => api.linkDocument(selectedDocId!, poId),
    onSuccess: () => {
      setBanner("Document linked to Purchase Order.");
      qc.invalidateQueries({ queryKey: ["document", selectedDocId] });
    },
  });

  const deleteMut = useMutation({
    mutationFn: (docId: string) => api.deleteDocument(docId),
    onSuccess: (res) => {
      setConfirmDeleteId(null);
      if (selectedDocId === res.document_id) {
        setSelectedDocId(null);
        setEdits({});
      }
      setBanner(
        res.reconciled_po_ids.length
          ? `Document deleted and ${res.reconciled_po_ids.length} linked transaction(s) re-reconciled.`
          : "Document deleted and downstream records cleaned up."
      );
      qc.invalidateQueries({ queryKey: ["documents"] });
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["exceptions"] });
      qc.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
  });

  const handleFiles = (files: FileList | null) => {
    if (files && files[0]) {
      uploadMut.mutate(files[0]);
    }
  };

  const validationWarningsField = docDetail?.fields.find(
    (f) => f.name === "_validation_warnings"
  );

  return (
    <div className="space-y-8">
      <div>
        <PageCaption module="Module / Evidence Ingestion" index="OCR & Verification" />
        <h1 className="font-display text-3xl font-bold text-ink-900">Document Workspace</h1>
        <p className="text-sm text-ink-500 mt-1">
          Upload PO, GRN &amp; Invoice files (PDF, PNG, JPG, XLSX, CSV) and review extracted fields
        </p>
      </div>

      {banner && <Toast message={banner} tone="info" onDismiss={() => setBanner(null)} />}

      {(uploadMut.isError || patchMut.isError || verifyMut.isError || deleteMut.isError) && (
        <Card className="border-status-danger-fg/30 bg-status-danger-bg text-status-danger-fg text-sm">
          {((uploadMut.error || patchMut.error || verifyMut.error || deleteMut.error) as Error).message}
        </Card>
      )}

      {/* Drag & Drop Ingestion Zone */}
      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          handleFiles(e.dataTransfer.files);
        }}
        className="rounded-hero border-2 border-dashed border-sand-400 bg-paper p-6 md:p-8 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-soft"
      >
        <div className="flex items-center gap-4">
          <div className="p-3 rounded-card bg-sand-100 text-ink-900">
            <UploadCloud className="w-7 h-7" />
          </div>
          <div>
            <div className="font-display text-base font-bold text-ink-900">
              Drag &amp; drop a document here, or browse
            </div>
            <div className="text-xs text-ink-500 mt-0.5">
              Max 15 MB • Magic-byte validated • Originals remain immutable with SHA-256 checksums
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2.5">
          <select
            aria-label="Document type hint"
            value={hint}
            onChange={(e) => setHint(e.target.value)}
            className="border border-sand-200 bg-sand-50 rounded-control px-3 py-2 text-sm text-ink-900"
          >
            <option value="">Auto-classify</option>
            <option value="PO">PO</option>
            <option value="GRN">GRN</option>
            <option value="INVOICE">INVOICE</option>
          </select>
          <label className="px-4 py-2 bg-ink-900 text-on-ink text-sm font-medium rounded-control cursor-pointer hover:-translate-y-px transition-transform shadow-soft">
            Select File
            <input
              type="file"
              data-testid="file-upload-input"
              className="hidden"
              onChange={(e) => handleFiles(e.target.files)}
            />
          </label>
        </div>
      </div>

      {activeJobId && jobStatus && (
        <Card variant="subtle" className="py-3 px-4 text-sm flex items-center gap-3">
          <span className="font-mono text-xs">Job {activeJobId.slice(0, 8)}:</span>
          <StatusPill value={jobStatus.status} />
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <Card className="lg:col-span-4">
          <h2 className="font-display text-base font-bold text-ink-900 mb-3">Uploaded Documents</h2>
          {isLoading ? (
            <PageSkeleton />
          ) : !listData?.items.length ? (
            <EmptyState
              title="No documents uploaded"
              description="Drop a PO, GRN, or Invoice above to run extraction."
            />
          ) : (
            <ul className="divide-y divide-sand-200">
              {listData.items.map((d: DocumentItem) => (
                <li key={d.document_id}>
                  <button
                    onClick={() => {
                      setSelectedDocId(d.document_id);
                      setEdits({});
                    }}
                    className={`w-full text-left py-3 px-2.5 rounded-control transition ${
                      selectedDocId === d.document_id ? "bg-sand-100" : "hover:bg-sand-50"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-semibold text-ink-900 truncate">
                        {d.file_name}
                      </span>
                      <StatusPill value={d.status} />
                    </div>
                    <div className="text-xs font-mono text-ink-500 mt-1">
                      {d.classification} ({Math.round(d.classification_confidence * 100)}%)
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <div className="lg:col-span-8 space-y-4">
          {!docDetail ? (
            <EmptyState
              title="Select a document"
              description="Choose a file from the left list to preview the original document and inspect OCR confidence."
            />
          ) : (
            <Card className="space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h3 className="font-display text-lg font-bold text-ink-900">
                    {docDetail.file_name}
                  </h3>
                  <p className="text-xs font-mono text-ink-500 mt-0.5">
                    Type: {docDetail.classification} • SHA-256: {docDetail.checksum.slice(0, 12)}...
                    • Evidence Page: {previewPage}
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <StatusPill value={docDetail.status} />
                  <Button
                    size="sm"
                    onClick={() => verifyMut.mutate()}
                    disabled={verifyMut.isPending}
                  >
                    Verify &amp; Commit
                  </Button>
                  {docDetail.transaction_id && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => navigate(`/transactions/${docDetail.transaction_id}`)}
                    >
                      Open Transaction
                    </Button>
                  )}
                  {confirmDeleteId === docDetail.document_id ? (
                    <div className="flex items-center gap-1.5">
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => deleteMut.mutate(docDetail.document_id)}
                        disabled={deleteMut.isPending}
                      >
                        {deleteMut.isPending ? "Deleting..." : "Confirm Delete"}
                      </Button>
                      <Button variant="outline" size="sm" onClick={() => setConfirmDeleteId(null)}>
                        Cancel
                      </Button>
                    </div>
                  ) : (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setConfirmDeleteId(docDetail.document_id)}
                      title="Delete document and clean up consequences"
                      className="text-status-danger-fg border-status-danger-fg/30 hover:bg-status-danger-bg"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      <span>Delete</span>
                    </Button>
                  )}
                </div>
              </div>

              {/* OCR Classification Confidence Meter */}
              <div className="p-3 rounded-control bg-sand-50 border border-sand-200 flex items-center justify-between gap-3">
                <span className="font-semibold uppercase tracking-[0.08em] text-ink-500 text-[11px]">
                  OCR Classification Confidence
                </span>
                <ConfidenceMeter value={docDetail.classification_confidence} />
              </div>

              {validationWarningsField && (
                <div
                  className="p-4 rounded-card border border-status-warning-fg/40 space-y-2"
                  style={{ backgroundImage: "var(--untrusted-stripe)" }}
                >
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.08em] text-status-warning-fg">
                    <ShieldAlert className="w-4 h-4" />
                    <span>Untrusted Document Content — Validation Notice</span>
                  </div>
                  <pre className="font-mono text-xs text-ink-900 whitespace-pre-wrap">
                    {JSON.stringify(validationWarningsField.value, null, 2)}
                  </pre>
                </div>
              )}

              {docDetail.candidate_po_links && docDetail.candidate_po_links.length > 0 && (
                <div className="p-3 rounded-control bg-sand-50 border border-sand-200 text-xs flex flex-wrap items-center gap-2">
                  <span className="font-semibold text-ink-700">Candidate PO Links:</span>
                  {docDetail.candidate_po_links.map((c) => (
                    <button
                      key={c.po_id}
                      onClick={() => linkMut.mutate(c.po_id)}
                      className="px-2.5 py-1 rounded-full bg-paper border border-sand-200 hover:border-ink-900 font-mono"
                    >
                      Link {c.po_number} ({c.method}, {Math.round(c.score * 100)}%)
                    </button>
                  ))}
                </div>
              )}

              {previewBlobUrl && docDetail.mime_type === "application/pdf" && (
                <iframe
                  title="PDF Preview"
                  src={`${previewBlobUrl}#page=${previewPage}`}
                  className="w-full h-64 border border-sand-200 rounded-card"
                />
              )}
              {previewBlobUrl && docDetail.mime_type.startsWith("image/") && (
                <img
                  src={previewBlobUrl}
                  alt={docDetail.file_name}
                  className="max-h-64 border border-sand-200 rounded-card object-contain"
                />
              )}

              <h4 className="text-[11px] font-semibold text-ink-500 uppercase tracking-[0.08em]">
                Extracted Fields (click row to jump to evidence page)
              </h4>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-[11px] uppercase tracking-[0.08em] text-ink-500 border-b border-sand-200">
                      <th scope="col" className="py-2">Field</th>
                      <th scope="col" className="py-2">Value</th>
                      <th scope="col" className="py-2">Confidence</th>
                      <th scope="col" className="py-2">Provenance</th>
                      <th scope="col" className="py-2">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-sand-200">
                    {docDetail.fields
                      .filter(
                        (f: ExtractedFieldItem) =>
                          f.name !== "line_items" && f.name !== "_validation_warnings"
                      )
                      .map((f: ExtractedFieldItem) => {
                        const lowConf = f.confidence < 0.8 && f.verification_status === "extracted";
                        const strVal =
                          typeof f.value === "object" ? JSON.stringify(f.value) : String(f.value ?? "");
                        return (
                          <tr
                            key={f.id}
                            onClick={() => setPreviewPage(f.page)}
                            className={`cursor-pointer ${
                              lowConf ? "bg-status-warning-bg/55" : "hover:bg-sand-50"
                            }`}
                          >
                            <td className="py-2.5 font-medium text-ink-900">{f.name}</td>
                            <td className="py-2.5">
                              <input
                                aria-label={`Edit ${f.name}`}
                                value={edits[f.name] ?? strVal}
                                onChange={(e) =>
                                  setEdits((prev) => ({ ...prev, [f.name]: e.target.value }))
                                }
                                className="border border-sand-200 bg-paper rounded-control px-2.5 py-1 text-xs font-mono w-full focus:border-ink-900 focus:outline-none"
                              />
                            </td>
                            <td className="py-2.5 text-xs font-mono">
                              <span
                                className={`font-semibold ${
                                  lowConf ? "text-status-warning-fg" : "text-status-success-fg"
                                }`}
                              >
                                {Math.round(f.confidence * 100)}%
                              </span>
                            </td>
                            <td className="py-2.5 text-xs font-mono text-ink-500">
                              p.{f.page} ({f.extraction_method})
                            </td>
                            <td className="py-2.5 text-xs">{f.verification_status}</td>
                          </tr>
                        );
                      })}
                  </tbody>
                </table>
              </div>

              {Object.keys(edits).length > 0 && (
                <div className="pt-2 flex justify-end">
                  <Button
                    onClick={() =>
                      patchMut.mutate(
                        Object.entries(edits).map(([field_name, value]) => ({
                          field_name,
                          value,
                        }))
                      )
                    }
                  >
                    Save Corrections
                  </Button>
                </div>
              )}
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};
