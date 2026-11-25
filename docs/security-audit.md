# ReconX AI — Security Audit

Verified via `backend/tests/test_hardening_security.py`, `test_auth_rbac.py`, `test_audit.py`, and Playwright audit:

- **Broken Access Control / RBAC:** `operator` blocked with `403` on approval & admin endpoints; `auditor` read-only.
- **IDOR / Cross-Tenant Isolation (`NFR-SEC-03`):** Org B admin cannot read or mutate Org A vendors, transactions, exceptions, investigations, or copilot data (`test_idor_cross_tenant_isolation_sweep`, `AT-11`).
- **SQL Injection & Arbitrary SQL:** Parameterized SQLAlchemy ORM everywhere; AST scan in `test_hardening_security.py` verifies `services/agents/` never imports `text` or calls `.execute(`; Copilot uses typed DB tools only.
- **Prompt Injection (`AT-08`):** Document text fenced in `<<<UNTRUSTED_DOCUMENT_CONTENT>>>`; `ALLOWLISTED_AGENT_TOOLS` contains zero payment/approval tools; `validate_evidence_refs` rejects fabricated UUIDs/rule IDs (`422`).
- **Malicious / Unsafe Uploads:** Magic-byte validation, size limits, UUID `storage_key`, SHA-256 checksums outside web root.
- **Secrets Hygiene:** Real keys stored only in gitignored `.env`; AST/regex secret scan passes (`0` leaks).
