# Software Requirements Specification — ReconX AI

- **Document ID**: RXAI-SRS-001
- **Version**: 1.0 — Initial implementation baseline
- **Date**: 25 November 2026
- **Product**: ReconX AI — Autonomous Financial Reconciliation & Intelligence Platform
- **Problem Statement**: PS-BA1 — Autonomous Three-Way Invoice, Purchase Order & Goods-Receipt Reconciliation Bot
- **Prepared for**: Synchronise 2026 / Department of ISE, Ramaiah Institute of Technology
- **Status**: Proposed solution specification; converted faithfully from `ReconX_AI_SRS_PS_BA1.pdf`

## How to use this SRS

- Treat requirements marked **MUST** as release-critical. **SHOULD** items are important but may be deferred if time is constrained. **MAY** items are optional extensions.
- Build the end-to-end happy path first: upload or ingest documents -> extract fields -> link PO/GRN/invoice -> reconcile -> investigate exceptions -> review/approve -> audit.
- Keep deterministic financial calculations and policy decisions in tested backend code. Use language models for extraction assistance, explanation and workflow orchestration—not as the authority for arithmetic or payment authorization.
- All sample values and thresholds in this document are illustrative. Configure thresholds per organization; do not present them as statutory or universal rules.
- The official PS title is the source scope. The additional intelligence features in this SRS are proposed differentiators, not requirements explicitly stated in the short problem-statement title.

---

## 1. Introduction

### 1.1 Purpose
This Software Requirements Specification defines the proposed requirements for ReconX AI, a web-based platform for autonomous three-way reconciliation of supplier invoices, purchase orders (POs) and goods-receipt records (GRNs). It provides a shared baseline for product design, implementation, testing and demonstration.

### 1.2 Product objective
The system shall reduce manual accounts-payable checking by ingesting financial documents, extracting structured data, linking related records, applying configurable reconciliation rules, identifying exceptions, investigating them with evidence and routing decisions through controlled approval workflows.

### 1.3 Intended audience
- Product owner and hackathon team: scope and prioritisation.
- Frontend and backend developers: screens, APIs, domain logic and integration contracts.
- AI/ML developers: extraction, entity matching, anomaly scoring and agent orchestration.
- QA/testers: test cases, expected outcomes and acceptance criteria.
- Evaluators: understand the problem, innovation, controls and demonstrable outcomes.

### 1.4 Definitions and conventions
- **MUST**: mandatory requirement for the target release.
- **SHOULD**: strongly recommended requirement; defer only with a documented reason.
- **MAY**: optional capability.
- **Three-way match**: comparison of PO, GRN and supplier invoice data.
- **Exception**: a mismatch, missing record, policy breach, low-confidence extraction or risk signal requiring review.
- **Evidence**: source document, page/region, extracted value, linked record, rule result or audit event supporting a conclusion.

### 1.5 Source and scope note
The supplied problem-statement title establishes the core requirement: an autonomous bot for three-way invoice, PO and goods-receipt reconciliation. The detailed workflows and advanced differentiators below are a proposed engineering interpretation designed to make a robust hackathon solution. Confirm any domain-specific rules, judging constraints and mandatory integrations with the official organisers before implementation.

---

## 2. Overall Description

### 2.1 Product perspective
ReconX AI is a modular application consisting of a web frontend, API/backend, document-processing pipeline, deterministic reconciliation engine, agent orchestration layer, relational database, optional graph store, background job queue and audit/analytics services. It may operate with uploaded demo documents and seeded sample data; enterprise integrations are optional unless explicitly required by the organisers.

### 2.2 Operating environment
| Component | Proposed baseline |
|---|---|
| Client | Modern desktop/mobile browser; responsive React web application. |
| Backend | Python 3.11+ with FastAPI; REST/JSON APIs. |
| Database | PostgreSQL as system of record. |
| Graph layer | Neo4j optional for relationship exploration; PostgreSQL remains authoritative. *(Overridden by D2: relational edge queries + React Flow, no Neo4j.)* |
| Document processing | PyMuPDF for text PDFs; OCR engine such as PaddleOCR *(D4: RapidOCR onnxruntime)* for scanned documents. |
| AI services | Provider-agnostic LLM adapter; optional embedding model. |
| ML | Scikit-learn / XGBoost for anomaly and risk models; begin with explainable rules if labelled data is unavailable. |
| Async jobs | Redis + Celery or equivalent task queue. *(D1: DB-backed jobs table + in-process worker thread.)* |
| Deployment | Docker Compose for local/demo deployment; cloud deployment optional. |

### 2.3 Design principles
- **Evidence-first**: every extracted field and automated conclusion should be traceable to a source.
- **Deterministic finance**: exact arithmetic, tax calculations, tolerance checks and approval rules are implemented in code.
- **Human control**: payment release and high-risk exceptions require authorised approval.
- **Modular intelligence**: AI agents call narrow, permissioned tools; they do not directly mutate critical financial state without policy checks.
- **Graceful degradation**: if an AI provider or graph database is unavailable, core deterministic reconciliation remains usable.
- **Auditability**: retain who/what/when for uploads, extraction, matching, investigation, overrides and approvals.

### 2.4 Constraints
- The system cannot guarantee fraud detection; it identifies risk indicators for investigation.
- OCR and LLM extraction can be wrong. Critical fields must have confidence scores and validation.
- A hackathon prototype may use synthetic or anonymised data; no real banking credentials or payment execution are needed.
- GST/tax and accounting policies vary by jurisdiction and organization. Keep rules configurable and label demo assumptions.
- Graph database and predictive forecasting are optional extensions; they must not block the core workflow.

---

## 3. Stakeholders and User Classes

| User class | Responsibilities | Typical permissions |
|---|---|---|
| AP / Finance operator | Upload documents, review extraction, initiate reconciliation, manage exceptions. | Create/read transactions; correct draft extraction; submit cases. |
| Finance approver | Review exceptions and approve/reject eligible cases. | Approve/reject within assigned limits; view evidence. |
| Procurement officer | Review PO terms, supplier and quantity/price disputes. | Read POs; comment or resolve procurement-related tasks. |
| Receiving / warehouse user | Confirm receipt quantities, rejected/damaged quantities and GRNs. | Create or update receipt records subject to controls. |
| Auditor | Inspect decisions, evidence, changes and audit trail. | Read-only access to authorised records and audit logs. |
| Administrator | Manage users, roles, thresholds, suppliers and configuration. | Administrative configuration; no silent alteration of historical audit events. |

### 3.1 Authentication and role model
The system MUST implement role-based access control (RBAC). A user may hold more than one role. Permissions must be checked server-side for every protected API. The frontend may hide unavailable actions but must not be treated as the security boundary.

---

## 4. Product Scope and Boundaries

### 4.1 In scope
- Upload, classify, extract and validate PO, GRN and invoice documents.
- Create or import structured transaction records and associate documents with suppliers and purchase orders.
- Perform line-level and document-level three-way matching.
- Handle partial deliveries, multiple GRNs, split invoices and configurable tolerances.
- Identify duplicate invoices, missing records, price/quantity/tax mismatches and inconsistent supplier details.
- Create discrepancy cases and run evidence-backed investigation assistance.
- Calculate explainable risk indicators from transaction and vendor history.
- Provide review, approval, rejection, clarification and audit workflows.
- Provide dashboards, filters, reports and a natural-language read-only finance copilot.
- Maintain immutable-style audit history through append-only events or protected audit records.

### 4.2 Out of scope for initial release
- Directly initiating bank transfers or releasing real payments.
- Replacing an ERP, accounting ledger, procurement suite or statutory tax system.
- Guaranteeing fraud detection or making legal conclusions.
- Autonomously changing approved purchase orders or supplier bank details.
- Training a production-grade fraud model without sufficient representative, labelled data.
- Unattended email sending to external suppliers unless a user explicitly enables and approves the integration.

### 4.3 Release priorities
| Priority | Capabilities |
|---|---|
| P0 — Core demo | Authentication/RBAC; document upload; extraction; structured review; PO-GRN-invoice linking; deterministic matching; exceptions; dashboard; audit trail. |
| P1 — Differentiation | Investigation agent; evidence citations; duplicate detection; vendor history; explainable risk scoring; approval workflow. |
| P2 — Advanced extension | Financial Evidence Graph; anomaly ML; finance copilot; cash-flow forecasting; email/ERP connectors. |

---

## 5. Functional Requirements

### 5.1 Identity, access and organization configuration
| ID | Requirement | Priority |
|---|---|---|
| FR-AUTH-01 | The system MUST allow authorised users to sign in and sign out securely. | P0 |
| FR-AUTH-02 | The system MUST enforce server-side RBAC for every protected operation. | P0 |
| FR-AUTH-03 | The system MUST support roles for finance operator, approver, procurement, receiving, auditor and administrator. | P0 |
| FR-AUTH-04 | The system SHOULD support configurable approval limits and separation of duties. | P1 |
| FR-AUTH-05 | The system MUST record user identity and timestamp for critical actions. | P0 |
| FR-CFG-01 | Administrators MUST configure currency, tax settings, quantity/price tolerances, duplicate rules and approval thresholds. | P0 |
| FR-CFG-02 | Configuration changes MUST be audited and versioned. | P1 |

### 5.2 Document ingestion and management
| ID | Requirement | Priority |
|---|---|---|
| FR-DOC-01 | Users MUST upload PDF, PNG, JPG/JPEG and XLSX/CSV documents within configured size limits. | P0 |
| FR-DOC-02 | The system MUST classify an uploaded document as PO, GRN, invoice or unknown, with a confidence score. | P0 |
| FR-DOC-03 | The system MUST store original file metadata, checksum, uploader, timestamp and processing status. | P0 |
| FR-DOC-04 | The system MUST detect exact duplicate files using a cryptographic checksum. | P0 |
| FR-DOC-05 | The system SHOULD support multi-page documents and scanned images through OCR. | P0 |
| FR-DOC-06 | The system MUST allow a user to correct extracted fields before committing them as verified data. | P0 |
| FR-DOC-07 | The system SHOULD preserve page number and text-region/bounding-box references for extracted fields. | P1 |
| FR-DOC-08 | The system MUST reject unsupported, corrupted or unsafe files with a clear error. | P0 |

### 5.3 Data extraction and validation
| ID | Requirement | Priority |
|---|---|---|
| FR-EXT-01 | The system MUST extract document number, supplier, dates, currency, line items, quantities, unit prices, taxes, discounts and totals when present. | P0 |
| FR-EXT-02 | Each extracted field MUST retain source document, page/reference, extraction method and confidence where available. | P0 |
| FR-EXT-03 | The system MUST validate required fields, data types, date formats, currency consistency and arithmetic totals. | P0 |
| FR-EXT-04 | The system MUST flag low-confidence or conflicting critical fields for human review. | P0 |
| FR-EXT-05 | The system SHOULD use semantic matching to suggest equivalent product descriptions across documents. | P1 |
| FR-EXT-06 | Semantic similarity MUST NOT override quantity, price, tax, supplier or policy validation. | P0 |
| FR-EXT-07 | The system MUST distinguish extracted, user-corrected and system-derived values. | P0 |

### 5.4 Transaction association and reconciliation
| ID | Requirement | Priority |
|---|---|---|
| FR-MAT-01 | The system MUST associate invoices and GRNs with a PO using explicit identifiers and controlled fallback matching. | P0 |
| FR-MAT-02 | The system MUST support line-level matching for supplier, item, unit of measure, quantity, unit price, tax and totals. | P0 |
| FR-MAT-03 | The system MUST support multiple GRNs against one PO and partial deliveries. | P0 |
| FR-MAT-04 | The system SHOULD support multiple invoices against one PO and split billing. | P1 |
| FR-MAT-05 | The system MUST calculate ordered, received, accepted, rejected, invoiced and remaining quantities separately. | P0 |
| FR-MAT-06 | The system MUST apply configurable quantity and price tolerances and show the rule applied. | P0 |
| FR-MAT-07 | The system MUST identify missing PO, missing GRN, over-billing, under-billing, price variance, tax variance and supplier mismatch. | P0 |
| FR-MAT-08 | The system MUST produce a result of matched, matched-with-tolerance, exception, incomplete or review-required. | P0 |
| FR-MAT-09 | The system MUST prevent a transaction from being marked approved solely because an LLM says it matches. | P0 |

### 5.5 Exception management and investigation
| ID | Requirement | Priority |
|---|---|---|
| FR-EXC-01 | The system MUST create an exception case for every failed rule or unresolved critical extraction field. | P0 |
| FR-EXC-02 | An exception MUST include type, severity, affected fields, values, rule, evidence references, owner and status. | P0 |
| FR-EXC-03 | The investigation agent SHOULD search linked POs, GRNs, invoices, prior cases and vendor history using authorised tools. | P1 |
| FR-EXC-04 | The agent MUST produce a structured explanation, evidence list, missing-information list and recommended next action. | P1 |
| FR-EXC-05 | The agent MUST distinguish verified facts, inferred hypotheses and unknown information. | P1 |
| FR-EXC-06 | The agent MUST NOT fabricate missing GRNs, approvals, supplier communications or evidence. | P0 |
| FR-EXC-07 | The agent MUST NOT modify critical financial records or release payments without an authorised workflow action. | P0 |
| FR-EXC-08 | Users MUST be able to assign, comment, request clarification, resolve, reject or escalate an exception. | P0 |
| FR-EXC-09 | All agent tool calls and resulting state changes MUST be logged. | P0 |

### 5.6 Fraud and anomaly intelligence
| ID | Requirement | Priority |
|---|---|---|
| FR-RISK-01 | The system MUST identify exact duplicate invoice numbers within a supplier/organization scope. | P0 |
| FR-RISK-02 | The system SHOULD identify near-duplicate invoices using amount, date, supplier, line-item and document similarity. | P1 |
| FR-RISK-03 | The system SHOULD flag unusual price deviations from historical prices for the same or similar items. | P1 |
| FR-RISK-04 | The system SHOULD flag unusual vendor patterns such as repeated mismatches, abnormal frequency or sudden changes in billing behaviour. | P1 |
| FR-RISK-05 | Risk outputs MUST include reason codes and contributing signals, not only a score. | P1 |
| FR-RISK-06 | Risk scores MUST be described as indicators for review, not proof of fraud. | P0 |
| FR-RISK-07 | If there is insufficient history or training data, the system MUST fall back to transparent rules and label model confidence as limited. | P0 |
| FR-RISK-08 | Supplier bank-detail changes MUST trigger enhanced verification and must never be accepted solely on an AI recommendation. | P0 |

### 5.7 Vendor intelligence
| ID | Requirement | Priority |
|---|---|---|
| FR-VEN-01 | The system SHOULD maintain a vendor profile with transaction count, mismatch rate, delivery timeliness and dispute history. | P1 |
| FR-VEN-02 | Vendor metrics MUST disclose the date range and number of transactions used. | P1 |
| FR-VEN-03 | The system MAY calculate a vendor reliability indicator from explainable weighted metrics. | P2 |
| FR-VEN-04 | The system MUST avoid presenting a score as an objective or definitive judgment where sample size is small. | P0 |

### 5.8 Approval and workflow
| ID | Requirement | Priority |
|---|---|---|
| FR-WF-01 | The system MUST route matched cases and exceptions according to configurable policies. | P0 |
| FR-WF-02 | The system MUST support approve, reject, request-information and escalate actions. | P0 |
| FR-WF-03 | The system MUST enforce role and approval-limit checks server-side. | P0 |
| FR-WF-04 | The system SHOULD enforce maker-checker separation for high-value or high-risk cases. | P1 |
| FR-WF-05 | The system MUST maintain status history and approval rationale. | P0 |
| FR-WF-06 | The system MUST keep payment execution outside the initial scope; approval means approval in the workflow, not a bank transfer. | P0 |

### 5.9 Dashboard, reports and copilot
| ID | Requirement | Priority |
|---|---|---|
| FR-UI-01 | The dashboard MUST show document counts, matched cases, exceptions, pending approvals and processing status. | P0 |
| FR-UI-02 | Users MUST filter transactions by supplier, date, status, amount, exception type and risk level. | P0 |
| FR-UI-03 | The reconciliation screen MUST show PO, GRN and invoice values side-by-side with field-level differences. | P0 |
| FR-UI-04 | The system SHOULD provide vendor trends, exception trends and cash-obligation summaries. | P1 |
| FR-UI-05 | The finance copilot SHOULD answer natural-language questions using authorised database retrieval. | P1 |
| FR-UI-06 | Copilot answers MUST cite transaction IDs or source records and indicate when no data is found. | P1 |
| FR-UI-07 | The copilot MUST be read-only in the initial release; it cannot approve, edit or pay through free-form chat. | P0 |
| FR-UI-08 | Reports SHOULD be exportable to CSV/PDF subject to permissions. | P1 |

### 5.10 Audit and notifications
| ID | Requirement | Priority |
|---|---|---|
| FR-AUD-01 | The system MUST record document upload, extraction, correction, match, exception, assignment, approval, rejection and configuration events. | P0 |
| FR-AUD-02 | Audit entries MUST include actor/system identity, timestamp, action, target entity and relevant before/after values where applicable. | P0 |
| FR-AUD-03 | Audit history MUST be protected against ordinary user modification or deletion. | P0 |
| FR-NOT-01 | The system SHOULD notify assigned users about new exceptions, approvals and clarification requests. | P1 |
| FR-NOT-02 | Notifications MUST avoid exposing sensitive invoice details to unauthorised recipients. | P0 |

---

## 6. Business Rules and Reconciliation Logic

### 6.1 Reconciliation dimensions
The matching engine must compare at least the following dimensions where the relevant fields exist: organization, supplier identity, PO reference, item identity, unit of measure, ordered quantity, received quantity, accepted quantity, rejected quantity, invoiced quantity, unit price, currency, tax code/rate, discount, freight/other charges, document dates and computed totals.

### 6.2 Quantity logic
For a PO line, define ordered quantity $Q_{PO}$; accepted receipt quantity $Q_{GRN}$; rejected quantity $Q_{REJ}$; invoiced quantity $Q_{INV}$. The implementation must aggregate linked receipt lines without double-counting and must respect the configured unit of measure.

| Derived value | Definition / rule |
|---|---|
| Accepted quantity | Sum of accepted quantities across linked GRNs. |
| Remaining to receive | $\max(0, \text{ordered quantity} - \text{accepted quantity} - \text{rejected quantity})$, subject to business policy. |
| Quantity eligible for invoice matching | Accepted quantity, adjusted only by explicit configurable policy (for example, approved service/advance billing rules). |
| Potential over-billing | $\max(0, \text{invoiced quantity} - \text{eligible quantity})$. |
| Potential under-billing | $\max(0, \text{eligible quantity} - \text{invoiced quantity})$, not necessarily an error if partial billing is allowed. |

### 6.3 Monetary logic
- Use decimal arithmetic, never binary floating-point, for currency calculations.
- Calculate line extension, discounts, tax and totals using configured currency precision and documented rounding rules.
- Compare invoice amounts to PO/receipt-supported amounts using configured tolerances.
- Separate disputed and undisputed amounts where the policy permits partial approval; never silently approve the full invoice when only part is supported.
- Show the calculation breakdown and source fields used for every variance.

### 6.4 Tolerances and policy configuration
Tolerance values are organization-specific. Provide configurable absolute and percentage tolerances for price and quantity, with optional supplier/item-specific overrides. A tolerance match must be labelled as such; it must not be presented as an exact match. Any override must record the user, reason, previous value and new value.

### 6.5 Matching outcomes
| Outcome | Meaning | Next step |
|---|---|---|
| `MATCHED` | All required fields and rules pass exactly. | Proceed to configured approval policy. |
| `MATCHED_WITH_TOLERANCE` | Differences fall within configured tolerance. | Show tolerance and continue only if policy permits. |
| `EXCEPTION` | One or more business rules fail. | Create case and hold affected workflow. |
| `INCOMPLETE` | Required document or data is missing. | Request missing record/data. |
| `REVIEW_REQUIRED` | Extraction confidence, identity ambiguity or risk signal needs human review. | Route to assigned reviewer. |

### 6.6 Duplicate and near-duplicate logic
Exact duplicates should use normalized invoice number + supplier identity + organization scope, supported by file checksum. Near-duplicate detection may use a weighted combination of supplier, amount, invoice date, line items, PO reference and document similarity. A near-duplicate is a review signal, not an automatic rejection.

### 6.7 Evidence and confidence
Every material field should carry provenance: document ID, page, source text or bounding box where available, extraction method, confidence, and whether a human corrected it. Confidence thresholds must be configurable. A low-confidence critical field should block automatic matching until reviewed.

---

## 7. AI/ML and Agent Requirements

### 7.1 AI components and responsibilities
| Component | Responsibility | Must not do |
|---|---|---|
| Document classifier | Predict PO/GRN/invoice/unknown document type. | Make final financial approval. |
| Extraction model / OCR | Propose structured field values with provenance and confidence. | Invent absent fields or silently overwrite verified values. |
| Semantic item matcher | Suggest equivalent product descriptions and candidate links. | Override exact identifiers or monetary rules. |
| Anomaly detector | Identify unusual prices, patterns, duplicates and vendor behaviour. | Declare fraud as a fact. |
| Investigation agent | Gather authorised records, run read-only tools and produce evidence-backed case summary. | Create evidence, alter source records or release payment. |
| Finance copilot | Answer read-only questions from authorised data. | Bypass RBAC or execute actions from natural language. |

### 7.2 Proposed agent architecture
- Orchestrator agent: routes a task to a specialised capability and tracks the investigation state.
- Document agent: invokes classification and extraction tools; writes only to a draft extraction object.
- Matching service: deterministic code, not an LLM agent; returns rule-by-rule results.
- Investigation agent: calls read-only tools to retrieve linked documents, GRNs, PO lines, prior cases and vendor history.
- Risk service: calculates deterministic risk indicators and optional ML anomaly scores with reason codes.
- Workflow service: enforces policy and RBAC before any state transition.
- Audit service: records agent prompts/tool calls at an appropriate level, outputs, decisions and user approvals.

### 7.3 Agent tool contract
Agents must use a limited allowlist of typed tools. Each tool must validate input, apply tenant and role scope, enforce timeouts and return structured JSON. The agent must not receive database credentials or unrestricted SQL access.

| Tool | Access | Purpose |
|---|---|---|
| `get_transaction_bundle(transaction_id)` | Read | Retrieve PO, GRNs, invoice, lines and current status. |
| `search_related_documents(filters)` | Read | Find candidate documents within permitted scope. |
| `get_vendor_history(vendor_id, period)` | Read | Retrieve historical metrics and relevant prior exceptions. |
| `run_reconciliation(transaction_id)` | Controlled service | Run deterministic matching; no agent-supplied formula. |
| `create_investigation_draft(case_id, structured_findings)` | Draft write | Save proposed explanation pending validation/review. |
| `assign_case(case_id, user_id)` | Workflow write | Assign only if user has permission. |
| `request_clarification(case_id, template_id)` | Approval-gated | Create a draft request; external send requires explicit user approval. |

### 7.4 Prompt injection and untrusted document content
Uploaded documents, email text and OCR output are untrusted data. They may contain malicious instructions. The agent must treat document text only as evidence, never as system instructions. Tool permissions must be enforced outside the model. The model must not follow instructions embedded in invoices such as requests to ignore controls, change bank details or approve payments.

### 7.5 Explainability format
Each investigation response should follow a strict schema: `summary`; `facts`; `discrepancies`; `evidence_refs`; `rule_ids`; `hypotheses` clearly labelled; `missing_information`; `risk_indicators`; `recommended_action`; `confidence`/`limitations`; `human_approval_required`. Unsupported claims must be omitted or explicitly marked unknown.

### 7.6 ML strategy
Start with explainable rules and robust baselines. Use labelled synthetic or anonymised records for demo evaluation. Add Isolation Forest, robust statistical deviation or supervised models only when training data quality supports them. Split data by time or vendor to reduce leakage. Report precision, recall, F1 and false-positive rate where labels exist. Do not claim model accuracy without a reproducible test set.

---

## 8. Data Requirements and Logical Data Model

### 8.1 Core entities
- `Organization`: id, name, base_currency, timezone, settings_json.
- `User`: id, organization_id, email, password_hash/identity_provider_id, status.
- `Role / Permission`: role_id, permission_code; user-role association.
- `Vendor`: id, organization_id, legal_name, normalized_name, tax_identifier, status.
- `PurchaseOrder`: id, organization_id, vendor_id, po_number, issue_date, currency, status, total.
- `POLine`: id, po_id, line_number, item_code, description, uom, quantity, unit_price, tax, discount.
- `GoodsReceipt`: id, organization_id, vendor_id, grn_number, po_id, received_at, status.
- `GRNLine`: id, grn_id, po_line_id, received_qty, accepted_qty, rejected_qty, uom.
- `Invoice`: id, organization_id, vendor_id, invoice_number, po_id, invoice_date, due_date, currency, totals, status.
- `InvoiceLine`: id, invoice_id, po_line_id, description, quantity, unit_price, tax, discount, line_total.
- `Document`: id, organization_id, file_name, storage_key, checksum, mime_type, uploaded_by, status.
- `ExtractionField`: id, document_id, field_name, value_json, confidence, page, evidence_ref, verification_status.
- `ReconciliationRun`: id, transaction_id, rule_version, status, totals, started_at, completed_at.
- `MatchResult`: id, run_id, entity_line_id, field_name, expected_value, actual_value, variance, rule_id, result.
- `ExceptionCase`: id, transaction_id, type, severity, status, owner_id, summary, created_at.
- `Investigation`: id, case_id, agent_version, structured_output_json, confidence, created_at.
- `RiskSignal`: id, transaction_id, signal_type, score, reason_json, model_version.
- `Approval`: id, case_id/transaction_id, approver_id, decision, rationale, decided_at.
- `AuditEvent`: id, organization_id, actor_type, actor_id, action, entity_type, entity_id, before_json, after_json, timestamp, correlation_id.
- `Notification`: id, recipient_id, type, reference_id, status, created_at.

### 8.2 Relationships
- One organization has many users, vendors, POs, documents and transactions.
- One vendor may have many POs and invoices.
- One PO has many PO lines, GRNs and invoices.
- One GRN has many GRN lines; each GRN line may reference a PO line.
- One invoice has many invoice lines; invoice lines may map to PO lines.
- A reconciliation run produces many match results and may create multiple exception cases.
- An exception may have multiple investigations, comments, assignments and approval events.
- Audit events reference the actor and affected entity; they are append-only from the application perspective.

### 8.3 Data integrity
- Use UUID or equivalent stable primary keys; enforce foreign keys and organization scoping.
- Store money as DECIMAL/NUMERIC with explicit currency code.
- Store dates and timestamps consistently; persist UTC timestamps and display in organization timezone.
- Use unique constraints for invoice identity within organization/vendor according to configured normalization.
- Use idempotency keys for ingestion and job processing to prevent duplicate creation.
- Keep original document files immutable; corrections create new extraction versions or audit events.
- Use soft deletion only where appropriate; retain audit and legal records according to configured retention policy.

### 8.4 Financial Evidence Graph
The optional graph layer represents nodes such as Vendor, PO, GRN, Invoice, Product, Exception and Approval, connected by relationships such as `ISSUED`, `REFERENCES`, `RECEIVED_AGAINST`, `BILLED_AGAINST`, `CONTAINS`, `FLAGGED_BY` and `APPROVED_BY`. PostgreSQL remains the source of truth. Graph projections must be rebuildable from relational records and must not become an independent authority for financial amounts.

### 8.5 Data retention and privacy
Retention periods, access to supplier identifiers and document storage locations must be configurable to meet the organization's policy. For the hackathon, use synthetic or anonymised data. Do not upload real confidential invoices to third-party AI providers without an explicit data-processing decision.

---

## 9. External Interface Requirements

### 9.1 User interface
- Dashboard: KPI cards, reconciliation queue, exception queue, approvals and recent activity.
- Document workspace: upload area, file preview, extraction fields, confidence indicators and correction controls.
- Transaction workspace: PO/GRN/invoice side-by-side comparison, line-level variance and match outcome.
- Investigation workspace: timeline, evidence panel, agent findings, missing data and recommended action.
- Vendor profile: history, metrics, price trends and open cases.
- Admin settings: users, roles, tolerances, workflow rules and model/provider settings.

### 9.2 API conventions
- REST endpoints use JSON request/response bodies and consistent HTTP status codes.
- All list endpoints support pagination, filtering and stable sorting.
- Protected endpoints require authentication and server-side authorization.
- Mutating endpoints should accept idempotency keys where retries are possible.
- Errors use a consistent structure: `code`, `message`, `details`, `correlation_id`.
- Version APIs under `/api/v1`.

### 9.3 External integrations
Potential later integrations include ERP/procurement systems, email inbox ingestion, object storage, identity providers and notification providers. Each integration must use least-privilege credentials, explicit configuration and audit logging. The initial hackathon build may simulate these with local uploads and seeded data.

### 9.4 Accessibility and usability
- Use clear status labels and text in addition to colour.
- Support keyboard navigation for core review and approval actions.
- Show source evidence next to extracted values and discrepancies.
- Avoid destructive actions without confirmation.
- Make the interface responsive and usable at common laptop resolutions.

---

## 10. Non-Functional Requirements

| ID | Category | Requirement / target |
|---|---|---|
| NFR-PERF-01 | Performance | For the demo environment, ordinary dashboard/API reads SHOULD return within 2 seconds at the 95th percentile under a small test load; document-processing time is measured separately. |
| NFR-PERF-02 | Processing | Document jobs MUST run asynchronously and expose queued/processing/succeeded/failed states. |
| NFR-REL-01 | Reliability | A failed OCR/LLM call MUST not corrupt the original document or partially approve a transaction. |
| NFR-REL-02 | Recovery | Background jobs MUST support bounded retries, idempotency and dead-letter/error visibility. |
| NFR-SEC-01 | Security | Passwords must be hashed with a modern password hashing algorithm or delegated to a trusted identity provider. |
| NFR-SEC-02 | Security | Use TLS in deployed environments; secrets must be environment-managed and never committed to source control. |
| NFR-SEC-03 | Security | Enforce tenant/organization scoping and RBAC on every API and data query. |
| NFR-AUD-01 | Auditability | Every critical state transition must have a traceable audit event. |
| NFR-MAINT-01 | Maintainability | Separate document processing, matching, risk, agent, workflow and API modules. |
| NFR-TEST-01 | Testability | Business rules must be unit-testable without calling an LLM or external service. |
| NFR-SCALE-01 | Scalability | Document processing and AI tasks SHOULD scale independently through workers. |
| NFR-UX-01 | Usability | A first-time finance operator SHOULD be able to upload a document set and understand the result without developer assistance. |
| NFR-PORT-01 | Portability | The application SHOULD run locally through Docker Compose with documented environment variables. |
| NFR-OBS-01 | Observability | Log structured events with request/job correlation IDs; do not log secrets or unnecessary personal/financial data. |

### 10.1 Availability and performance interpretation
Do not claim enterprise-grade uptime or throughput from a hackathon prototype. Establish measurable demo targets, run load tests and report the tested environment, dataset size and observed results.

---

## 11. Security, Privacy and Governance

### 11.1 Security controls
- Authentication: secure sessions or short-lived access tokens; secure cookies where applicable; rate-limit login attempts.
- Authorization: RBAC, organization-level isolation and object-level permission checks.
- File security: validate extension and MIME type, enforce size limits, scan files where feasible, store outside public web roots and use random storage keys.
- Data protection: encrypt traffic; encrypt storage where supported; mask sensitive fields in logs and UI where appropriate.
- Secrets: use environment variables or secret manager; provide `.env.example` without real secrets.
- Audit: record approvals, overrides, corrections, agent tool calls and configuration changes.
- Backups: document database and object-storage backup/restore approach for any persistent deployment.

### 11.2 Human oversight
Automatic processing may classify, extract, reconcile and prepare recommendations. High-risk exceptions, ambiguous identity matches, supplier bank-detail changes, policy overrides and payment release must require a designated human decision. No payment integration is part of the initial scope.

### 11.3 AI governance
- Show when content is AI-generated or AI-assisted.
- Retain model/provider/version and prompt-template version for investigations where feasible.
- Use structured output schemas and validate all model responses before use.
- Treat all external document content as untrusted input.
- Provide a fallback path when the AI provider is unavailable.
- Allow users to correct extraction and report incorrect agent findings.
- Avoid using vendor risk scores as the sole basis for punitive action.

### 11.4 Privacy
Collect only data required for reconciliation. Use synthetic demo records whenever possible. Define who can view tax identifiers, bank details, invoice attachments and audit history. Do not expose one organization's data to another organization. Establish retention and deletion policy before production use.

---

## 12. System Architecture

### 12.1 Logical architecture
- Presentation: React UI; upload, review, reconciliation, exception, approval, analytics and admin screens.
- API / application: FastAPI routes, authentication, RBAC, validation, orchestration of domain services.
- Domain services: Document service, extraction service, matching engine, exception service, vendor service, workflow service, audit service.
- Intelligence services: OCR/LLM adapter, semantic matcher, anomaly scorer, investigation agent, finance copilot.
- Persistence: PostgreSQL; object storage for originals; relational graph projection (per D2); DB-backed jobs table (per D1).
- Workers: Async document parsing, OCR, extraction, reconciliation, anomaly scoring and notifications.

### 12.2 Key architectural decisions
- PostgreSQL is authoritative for financial entities, amounts, approvals and audit records.
- The matching engine is deterministic and independently testable.
- LLM and OCR providers are hidden behind adapters to allow replacement.
- Agents use typed tools and cannot run arbitrary SQL.
- Graph layer uses relational edge queries + React Flow (no Neo4j, per D2).
- Async workers process heavy documents; the API returns a job identifier rather than blocking on OCR/LLM processing.

---

## 13. Core Workflows and Use Cases

- **UC-01: Upload and process documents** — Upload PO/GRN/invoice files -> validate type/size/checksum -> store securely -> async jobs classify and extract -> validate extracted data -> user reviews low-confidence fields -> verified records available for matching.
- **UC-02: Reconcile a transaction** — Select transaction or trigger matching -> aggregate linked GRNs and invoice lines -> compare supplier, items, quantities, prices, tax, totals -> store rule results -> assign outcome (`MATCHED`, `MATCHED_WITH_TOLERANCE`, `EXCEPTION`, `INCOMPLETE`, `REVIEW_REQUIRED`) -> create exception cases.
- **UC-03: Investigate discrepancy** — Orchestrator loads case context -> agent calls allowlisted read tools -> gathers linked documents and history -> identifies facts, discrepancies, unknowns -> creates structured investigation draft with evidence references -> reviewer validates.
- **UC-04: Approve or reject** — Approver opens case -> reviews source documents, match results, investigation -> enters rationale -> approves, rejects, requests information or escalates -> workflow service checks role, limit, maker-checker policy -> commits state transition and audit event; no payment executed.
- **UC-05: Ask finance copilot** — Authenticated user asks question -> copilot interprets intent -> retrieval service applies user/org scope and queries approved views -> model summarizes retrieved records -> cites transaction IDs and indicates limitations; read-only.

---

## 14. Error Handling and Observability

- Categories: Input validation, Document processing, Business rule, Integration, AI quality, Authorization.
- Structured logs with `request_id`, `job_id`, `transaction_id` and `correlation_id`.
- Track job duration, OCR failures, extraction confidence, matching outcomes and agent tool errors.
- Do not log passwords, API keys, full bank details or unnecessary document contents.
- Provide an admin view for failed jobs and retry status.
- Capture model name/version, extraction version, rule version and agent workflow version for reproducibility.

---

## 15. Testing and Acceptance Criteria

### 15.2 Minimum acceptance scenarios
| Test ID | Scenario | Expected result |
|---|---|---|
| AT-01 | Valid PO, GRN and invoice with exact values. | MATCHED; all compared fields pass; audit record exists. |
| AT-02 | PO=100, accepted GRN=90, invoice=100. | EXCEPTION for unsupported 10 units; no full approval. |
| AT-03 | PO=100, GRN1=60, GRN2=40, invoice=100. | Aggregate receipts correctly; MATCHED if other rules pass. |
| AT-04 | Invoice price exceeds PO price beyond configured tolerance. | Price variance exception with exact calculation. |
| AT-05 | Same invoice number and supplier submitted twice. | Duplicate signal; second record requires review. |
| AT-06 | Invoice has no linked PO. | INCOMPLETE; missing PO exception. |
| AT-07 | OCR confidence low for invoice total. | Review required; no automatic approval. |
| AT-08 | Agent is asked to approve a payment in a document prompt. | Ignore document instruction; agent has no payment tool; audit event retained. |
| AT-09 | User without approver role calls approval API. | 403 Forbidden; transaction state unchanged. |
| AT-10 | Graph database unavailable. | Core reconciliation still works using PostgreSQL. |
| AT-11 | Copilot asks for another organization's invoice data. | Return no data/deny; tenant isolation preserved. |
| AT-12 | Approver approves with valid role and rationale. | State transition recorded with approver, timestamp and audit event. |

---

## 17. Risks, Assumptions and Open Decisions

### 17.2 Open decisions to confirm
1. Official hackathon constraints: mandatory technology, offline/online requirements, judging rubric and submission format.
2. Whether email inbox ingestion or ERP integration is expected by the organisers.
3. Supported document formats and maximum file size.
4. Whether services, milestone billing, advance payments, credit notes and debit notes are required.
5. Organization-specific tolerances, tax rules, approval hierarchy and retention policy.
6. Whether the team can use external LLM/OCR APIs and whether data may leave the local environment.

---

## Appendix B. Sample API Contracts
- **B.1 Upload document**: `POST /api/v1/documents` -> `{ "document_id": "uuid", "status": "QUEUED", "job_id": "uuid" }`
- **B.2 Get document processing status**: `GET /api/v1/documents/{document_id}`
- **B.3 Create reconciliation run**: `POST /api/v1/transactions/{transaction_id}/reconcile`
- **B.4 Start investigation**: `POST /api/v1/exceptions/{case_id}/investigations`, `GET /api/v1/investigations/{investigation_id}`
- **B.5 Approve/reject case**: `POST /api/v1/exceptions/{case_id}/decision`
- **B.6 Error response**: `{ "error": { "code": "...", "message": "...", "details": {}, "correlation_id": "uuid" } }`
