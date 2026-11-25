"""Compute paired Manual AP vs. ReconX benchmark metrics from docs/benchmark-data-template.csv.

Skips incomplete/unmeasured rows rather than fabricating values.
"""

import csv
import statistics
import sys
from pathlib import Path

CSV_PATH = Path(__file__).resolve().parents[1] / "docs" / "benchmark-data-template.csv"


def _parse_bool(val: str) -> bool:
    return val.strip().lower() in {"1", "true", "yes", "y"}


def main() -> int:
    if not CSV_PATH.exists():
        print(f"CSV template not found: {CSV_PATH}", file=sys.stderr)
        return 1

    manual_times: list[float] = []
    reconx_times: list[float] = []
    manual_acc: list[bool] = []
    reconx_acc: list[bool] = []
    manual_int: list[int] = []
    reconx_int: list[int] = []
    total_rows = 0

    with CSV_PATH.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            m_t = (row.get("manual_time_sec") or "").strip()
            r_t = (row.get("reconx_time_sec") or "").strip()
            if not m_t or not r_t:
                continue
            manual_times.append(float(m_t))
            reconx_times.append(float(r_t))
            if (row.get("manual_accurate") or "").strip():
                manual_acc.append(_parse_bool(row["manual_accurate"]))
            if (row.get("reconx_accurate") or "").strip():
                reconx_acc.append(_parse_bool(row["reconx_accurate"]))
            if (row.get("manual_interventions") or "").strip():
                manual_int.append(int(row["manual_interventions"]))
            if (row.get("reconx_interventions") or "").strip():
                reconx_int.append(int(row["reconx_interventions"]))

    n = len(manual_times)
    print(f"Benchmark CSV: {CSV_PATH}")
    print(f"Total template cases: {total_rows} | Measured paired cases: {n}")
    if n == 0:
        print("Status: NO MEASURED HUMAN TIMINGS RECORDED YET (unmeasured rows left blank).")
        return 0

    total_manual = sum(manual_times)
    total_reconx = sum(reconx_times)
    saved = total_manual - total_reconx
    pct_saved = (saved / total_manual * 100.0) if total_manual > 0 else 0.0

    print(f"Mean Manual Time (s):   {statistics.mean(manual_times):.2f}")
    print(f"Median Manual Time (s): {statistics.median(manual_times):.2f}")
    print(f"Mean ReconX Time (s):   {statistics.mean(reconx_times):.2f}")
    print(f"Median ReconX Time (s): {statistics.median(reconx_times):.2f}")
    print(f"Total Time Saved (s):   {saved:.2f} ({pct_saved:.2f}%)")
    if manual_acc:
        print(f"Manual Accuracy:        {sum(manual_acc) / len(manual_acc) * 100:.2f}%")
    if reconx_acc:
        print(f"ReconX Accuracy:        {sum(reconx_acc) / len(reconx_acc) * 100:.2f}%")
    if manual_int:
        print(f"Manual Interventions:   {sum(manual_int)}")
    if reconx_int:
        print(f"ReconX Interventions:   {sum(reconx_int)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
