"""A tiny made-up example of a time machine evaluation.

All data here is synthetic and invented for demonstration. No real
variants, no real results. It shows the pattern end to end:

- fake records dated before and after a cutoff,
- the input frozen at the cutoff,
- a holdout built from positive labels resolved after the cutoff,
- hits@K printed for a fake model ranking vs a fake baseline ranking.

Run it with:

    python3 examples/synthetic_example.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from time_machine_eval import build_holdout, evaluate, filter_to_cutoff

CUTOFF = "2023-01-31"


def make_records():
    """Invented records: some known before the cutoff, some resolved after."""
    records = []

    # Resolved before the cutoff: the model is allowed to see these.
    for i in range(1, 21):
        records.append(
            {"id": f"OLD-{i:02d}", "date": "2022-06-15", "is_positive": i % 3 == 0}
        )

    # Resolved after the cutoff: 10 positives (the future exam answers)
    # mixed with 10 negatives. The model never sees these.
    for i in range(1, 11):
        records.append(
            {"id": f"NEW-P{i:02d}", "date": "2024-03-01", "is_positive": True}
        )
    for i in range(1, 11):
        records.append(
            {"id": f"NEW-N{i:02d}", "date": "2024-03-01", "is_positive": False}
        )

    return records


def make_rankings():
    """Two invented rankings over the post-cutoff candidates.

    The model ranking puts most future positives near the top.
    The baseline ranking is close to alphabetical, so its positives
    land wherever the alphabet puts them.
    """
    positives = [f"NEW-P{i:02d}" for i in range(1, 11)]
    negatives = [f"NEW-N{i:02d}" for i in range(1, 11)]

    model_ranking = (
        positives[:6]  # 6 positives in the model's top 10
        + negatives[:4]
        + positives[6:9]  # 3 more positives by rank 20
        + negatives[4:]
        + positives[9:]  # the last positive sits at the very end
    )

    baseline_ranking = sorted(positives + negatives)
    # Alphabetical order puts NEW-N* before NEW-P*, so the baseline
    # finds no positives in its top 10 and all 10 only by rank 20.

    return model_ranking, baseline_ranking


def main():
    records = make_records()

    frozen_input = filter_to_cutoff(records, CUTOFF)
    holdout = build_holdout(records, CUTOFF)

    model_ranking, baseline_ranking = make_rankings()

    print("Time machine evaluation on synthetic data (all values invented)")
    print(f"Cutoff date: {CUTOFF}")
    print(f"Records the model may see (on or before cutoff): {len(frozen_input)}")
    print(f"Holdout positives (resolved after cutoff): {len(holdout)}")
    print()

    results = evaluate(model_ranking, baseline_ranking, holdout, ks=(5, 10))
    for k, scores in results.items():
        print(f"hits@{k}: model = {scores['model']}, baseline = {scores['baseline']}")


if __name__ == "__main__":
    main()
