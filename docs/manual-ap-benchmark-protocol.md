# ReconX AI — Manual AP vs. ReconX Controlled Benchmark Protocol

## 1. Objective
Conduct a controlled, repeatable 20-transaction comparison between **Manual Accounts Payable (AP) Reconciliation** and **ReconX AI Automated Reconciliation** using identical synthetic source bundles.

## 2. 20-Transaction Test Set Composition

| Scenario Type | Count | Case IDs |
|---|---|---|
| Perfect 3-way match | 4 | `BENCH-01` .. `BENCH-04` |
| Quantity mismatch (over-billing / short-receipt) | 4 | `BENCH-05` .. `BENCH-08` |
| Unit price mismatch (outside tolerance) | 3 | `BENCH-09` .. `BENCH-11` |
| Partial delivery (multiple GRNs against 1 PO) | 3 | `BENCH-12` .. `BENCH-14` |
| Duplicate / near-duplicate invoice | 3 | `BENCH-15` .. `BENCH-17` |
| Missing GRN | 3 | `BENCH-18` .. `BENCH-20` |

## 3. Stopwatch Measurement Rules

### A. Manual AP Reconciliation
Start stopwatch when opening the first document for the case; stop when the final match/exception decision and discrepancy note are recorded:
1. Open source PO, GRN(s), and Invoice files.
2. Check line-item quantities (ordered vs. accepted vs. invoiced).
3. Check unit prices, tax, and line/document totals.
4. Validate against prior invoices for duplicates.
5. Identify discrepancies and record the final decision (`MATCHED` / `EXCEPTION` / `INCOMPLETE`).

### B. ReconX AI Automated Reconciliation
Start stopwatch at initial document submission (`POST /api/v1/documents`) or reconciliation trigger; stop when extraction + 3-way match result (`outcome` + rule breakdown) is generated.

## 4. Recording & Computing Results
1. Record stopwatch measurements in `docs/benchmark-data-template.csv` (leave unmeasured cells blank; never fabricate timings).
2. Run the aggregator script:
   ```powershell
   .\backend\.venv\Scripts\python.exe scripts\compute_benchmark_metrics.py
   ```
3. Update `docs/benchmark-report.md` only with measured outputs from completed rows.
