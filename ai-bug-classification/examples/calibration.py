"""
NON-PRODUCTION DEMONSTRATION. Synthetic data only.

The check I would now run *before* choosing confidence thresholds: compare
the model's self-reported confidence with human-reviewed correctness.

If accuracy does not rise with confidence, the threshold is not filtering
anything; it only decides which wrong answers get written silently.

Run:  python3 calibration.py
"""

from typing import Iterable, List, Sequence, Tuple

BUCKETS: Sequence[Tuple[float, float]] = ((0.0, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.01))


def calibration_table(samples: Iterable[Tuple[float, bool]]) -> List[dict]:
    rows = []
    samples = list(samples)
    for lo, hi in BUCKETS:
        hits = [ok for conf, ok in samples if lo <= conf < hi]
        rows.append({
            "bucket": f"{lo:.1f}-{min(hi, 1.0):.1f}",
            "n": len(hits),
            "accuracy": (sum(hits) / len(hits)) if hits else None,
        })
    return rows


def is_informative(rows: List[dict], min_gap: float = 0.10) -> bool:
    """Crude signal test: top bucket must beat the bottom populated bucket."""
    populated = [r for r in rows if r["n"]]
    if len(populated) < 2:
        return False
    return populated[-1]["accuracy"] - populated[0]["accuracy"] >= min_gap


# Two synthetic review samples: one well calibrated, one flat.
WELL_CALIBRATED = [(0.65, False), (0.68, False), (0.66, True), (0.75, True), (0.78, False),
                   (0.72, True), (0.85, True), (0.88, True), (0.83, False), (0.93, True),
                   (0.95, True), (0.97, True), (0.91, True)]
FLAT = [(0.86, True), (0.88, False), (0.90, True), (0.91, True), (0.92, False), (0.93, True),
        (0.94, True), (0.95, False), (0.96, True), (0.89, True), (0.87, True), (0.97, False)]


def _print(name: str, samples) -> None:
    rows = calibration_table(samples)
    print(name)
    for r in rows:
        acc = "  -  " if r["accuracy"] is None else f"{r['accuracy']:.0%}"
        print(f"  {r['bucket']:<9} n={r['n']:<3} accuracy={acc}")
    verdict = "usable as a gate" if is_informative(rows) else "NOT informative - do not gate on it"
    print(f"  -> confidence is {verdict}\n")


if __name__ == "__main__":
    _print("Sample A (synthetic, well calibrated)", WELL_CALIBRATED)
    _print("Sample B (synthetic, flat: everything reported at 0.86-0.97)", FLAT)
