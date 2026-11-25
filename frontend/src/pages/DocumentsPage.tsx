import React, { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { UploadCloud } from "lucide-react";
import { api, getAccessToken } from "../api/client";
import type { DocumentItem, ExtractedFieldItem } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";

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

  const handleFiles = (files: FileList | null) => {
    if (files && files[0]) {
      uploadMut.mutate(files[0]);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Document Workspace</h1>
          <p className="text-sm text-slate-500">
            Upload PO, GRN & Invoice files (PDF, PNG, JPG, XLSX, CSV) and review extracted fields
          </p>
        </div>
      </div>

      {banner && (
        <div className="p-3 rounded-lg bg-indigo-50 border border-indigo-200 text-sm text-indigo-900 flex justify-between">
          <span>{banner}</span>
          <button onClick={() => setBanner(null)} className="text-xs underline">
            Dismiss
          </button>
        </div>
      )}

      {(uploadMut.isError || patchMut.isError || verifyMut.isError) && (
        <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-sm text-rose-800">
          {((uploadMut.error || patchMut.error || verifyMut.error) as Error).message}
        </div>
      )}

      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          handleFiles(e.dataTransfer.files);
        }}
        className="bg-white border-2 border-dashed border-slate-300 rounded-xl p-6 flex flex-col sm:flex-row items-center justify-between gap-4"
      >
        <div className="flex items-center gap-3">
          <UploadCloud className="w-8 h-8 text-indigo-600" />
          <div>
            <div className="text-sm font-semibold text-slate-900">
              Drag & drop a document here, or browse
            </div>
            <div className="text-xs text-slate-500">
              Max 15 MB • Magic-byte validated • Originals remain immutable
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <select
            aria-label="Document type hint"
            value={hint}
            onChange={(e) => setHint(e.target.value)}
            className="border border-slate-300 rounded-lg px-2.5 py-1.5 text-sm"
          >
            <option value="">Auto-classify</option>
            <option value="PO">PO</option>
            <option value="GRN">GRN</option>
            <option value="INVOICE">INVOICE</option>
          </select>
          <label className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg cursor-pointer hover:bg-indigo-700">
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
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-900 flex items-center gap-2">
          <span>Job {activeJobId.slice(0, 8)}:</span>
          <StatusBadge value={jobStatus.status} />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-4 bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-900 mb-3">Uploaded Documents</h2>
          {isLoading ? (
            <div className="text-sm text-slate-500">Loading...</div>
          ) : !listData?.items.length ? (
            <div className="text-sm text-slate-500 py-6 text-center">No documents uploaded yet.</div>
          ) : (
            <ul className="divide-y divide-slate-100">
              {listData.items.map((d: DocumentItem) => (
                <li key={d.document_id}>
                  <button
                    onClick={() => {
                      setSelectedDocId(d.document_id);
                      setEdits({});
                    }}
                    className={`w-full text-left py-2.5 px-2 rounded-lg transition ${
                      selectedDocId === d.document_id ? "bg-indigo-50" : "hover:bg-slate-50"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-medium text-slate-900 truncate">
                        {d.file_name}
                      </span>
                      <StatusBadge value={d.status} />
                    </div>
                    <div className="text-xs text-slate-500 mt-0.5">
                      {d.classification} ({Math.round(d.classification_confidence * 100)}%)
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="lg:col-span-8 space-y-4">
          {!docDetail ? (
            <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-sm text-slate-500">
              Select a document to preview file & inspect extracted fields.
            </div>
          ) : (
            <>
              <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                  <div>
                    <h3 className="font-semibold text-slate-900">{docDetail.file_name}</h3>
                    <p className="text-xs text-slate-500">
                      Type: {docDetail.classification} • SHA-256: {docDetail.checksum.slice(0, 12)}...
                      • Evidence Page: {previewPage}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge value={docDetail.status} />
                    <button
                      onClick={() => verifyMut.mutate()}
                      disabled={verifyMut.isPending}
                      className="px-3 py-1.5 bg-emerald-600 text-white text-xs font-medium rounded-lg hover:bg-emerald-700"
                    >
                      Verify & Commit
                    </button>
                    {docDetail.transaction_id && (
                      <button
                        onClick={() => navigate(`/transactions/${docDetail.transaction_id}`)}
                        className="px-3 py-1.5 border border-slate-300 text-xs font-medium rounded-lg hover:bg-slate-50"
                      >
                        Open Transaction
                      </button>
                    )}
                  </div>
                </div>

                {docDetail.candidate_po_links && docDetail.candidate_po_links.length > 0 && (
                  <div className="mb-3 p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-xs flex flex-wrap items-center gap-2">
                    <span className="font-medium text-slate-700">Candidate PO Links:</span>
                    {docDetail.candidate_po_links.map((c) => (
                      <button
                        key={c.po_id}
                        onClick={() => linkMut.mutate(c.po_id)}
                        className="px-2 py-1 rounded bg-white border border-slate-300 hover:border-indigo-500"
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
                    className="w-full h-64 border border-slate-200 rounded-lg mb-4"
                  />
                )}
                {previewBlobUrl && docDetail.mime_type.startsWith("image/") && (
                  <img
                    src={previewBlobUrl}
                    alt={docDetail.file_name}
                    className="max-h-64 border border-slate-200 rounded-lg mb-4 object-contain"
                  />
                )}

                <h4 className="text-xs font-semibold text-slate-700 uppercase tracking-wide mb-2">
                  Extracted Fields (click row to jump to evidence page)
                </h4>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-xs text-slate-500 border-b">
                        <th className="py-2">Field</th>
                        <th className="py-2">Value</th>
                        <th className="py-2">Confidence</th>
                        <th className="py-2">Provenance</th>
                        <th className="py-2">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {docDetail.fields
                        .filter((f: ExtractedFieldItem) => f.name !== "line_items")
                        .map((f: ExtractedFieldItem) => {
                          const lowConf = f.confidence < 0.8 && f.verification_status === "extracted";
                          const strVal =
                            typeof f.value === "object" ? JSON.stringify(f.value) : String(f.value ?? "");
                          return (
                            <tr
                              key={f.id}
                              onClick={() => setPreviewPage(f.page)}
                              className={`cursor-pointer ${lowConf ? "bg-amber-50/70" : "hover:bg-slate-50"}`}
                            >
                              <td className="py-2 font-medium text-slate-800">{f.name}</td>
                              <td className="py-2">
                                <input
                                  aria-label={`Edit ${f.name}`}
                                  value={edits[f.name] ?? strVal}
                                  onChange={(e) =>
                                    setEdits((prev) => ({ ...prev, [f.name]: e.target.value }))
                                  }
                                  className="border border-slate-300 rounded px-2 py-1 text-xs w-full"
                                />
                              </td>
                              <td className="py-2 text-xs">
                                <span
                                  className={`font-semibold ${
                                    lowConf ? "text-amber-700" : "text-emerald-700"
                                  }`}
                                >
                                  {Math.round(f.confidence * 100)}%
                                </span>
                              </td>
                              <td className="py-2 text-xs text-slate-500">
                                p.{f.page} ({f.extraction_method})
                              </td>
                              <td className="py-2 text-xs">{f.verification_status}</td>
                            </tr>
                          );
                        })}
                    </tbody>
                  </table>
                </div>

                {Object.keys(edits).length > 0 && (
                  <div className="mt-3 flex justify-end">
                    <button
                      onClick={() =>
                        patchMut.mutate(
                          Object.entries(edits).map(([field_name, value]) => ({
                            field_name,
                            value,
                          }))
                        )
                      }
                      className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700"
                    >
                      Save Corrections
                    </button>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
