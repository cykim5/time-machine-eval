"""Time machine evaluation: freeze the past, grade on the future.

A small, dependency-free module implementing the generic pattern:

1. Filter records to a cutoff date (what the model was allowed to see).
2. Build a holdout label set from records resolved after the cutoff
   (the exam questions written after the textbook was printed).
3. Score a ranked prediction list with hits@K.
4. Score a baseline ranking the same way, on the same holdout, so the
   two numbers can be compared honestly.

Records are plain dicts. Each record needs at least an ID and a date.
Dates can be ``datetime.date`` / ``datetime.datetime`` objects or ISO
format strings such as "2023-01-31" or "2022-06-15".

Only the Python standard library is used.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Hashable, Iterable, List, Mapping, Sequence, Set

Record = Mapping[str, Any]


def parse_date(value: Any) -> date:
    """Return a ``datetime.date`` for a date, datetime, or ISO string.

    Raises:
        TypeError: if the value is not a date, datetime, or string.
        ValueError: if a string is not a valid ISO date.
    """
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value.strip())
    raise TypeError(f"Cannot parse a date from {type(value).__name__}: {value!r}")


def filter_to_cutoff(
    records: Iterable[Record],
    cutoff: Any,
    date_key: str = "date",
) -> List[Record]:
    """Keep only records dated on or before ``cutoff``.

    This is the model's frozen view of the world: everything it was
    allowed to see. Records after the cutoff are excluded, so a record
    can never be evidence for itself.

    Args:
        records: The full record collection.
        cutoff: The freeze date (date, datetime, or ISO string).
        date_key: The record field holding the date the fact became
            public (for example a resolution or publication date).

    Returns:
        A new list with the records dated on or before the cutoff,
        in their original order.
    """
    cutoff_date = parse_date(cutoff)
    return [r for r in records if parse_date(r[date_key]) <= cutoff_date]


def build_holdout(
    records: Iterable[Record],
    cutoff: Any,
    date_key: str = "date",
    id_key: str = "id",
    label_key: str = "is_positive",
) -> Set[Hashable]:
    """Build the post-cutoff holdout: IDs of positive labels resolved later.

    A record joins the holdout when its date is strictly after the
    cutoff and its label field is truthy. These are the true answers
    the model had no way to see at freeze time.

    Args:
        records: The full record collection.
        cutoff: The freeze date (date, datetime, or ISO string).
        date_key: The record field holding the date.
        id_key: The record field holding the unique ID.
        label_key: The record field holding the resolved label;
            truthy means the record counts as a positive answer.

    Returns:
        A set of IDs forming the test set for hits@K scoring.
    """
    cutoff_date = parse_date(cutoff)
    return {
        r[id_key]
        for r in records
        if parse_date(r[date_key]) > cutoff_date and bool(r.get(label_key))
    }


def hits_at_k(
    ranked_ids: Sequence[Hashable],
    holdout_ids: Set[Hashable],
    k: int,
) -> int:
    """Count how many holdout IDs appear in the top ``k`` of a ranking.

    Each holdout ID counts at most once, even if the ranking repeats
    it, so a duplicated ID can never inflate the score.

    Args:
        ranked_ids: Candidate IDs, best first.
        holdout_ids: The set of true answer IDs (from ``build_holdout``).
        k: How deep into the ranking to look. Values larger than the
            ranking are allowed and simply score the whole list.

    Returns:
        The number of distinct holdout IDs found in the first
        ``k`` positions.
    """
    if k < 0:
        raise ValueError("k must be zero or positive")
    top = set(ranked_ids[:k])
    return len(top & set(holdout_ids))


def evaluate(
    model_ranking: Sequence[Hashable],
    baseline_ranking: Sequence[Hashable],
    holdout_ids: Set[Hashable],
    ks: Iterable[int] = (10, 50, 100),
) -> Dict[int, Dict[str, int]]:
    """Score a model ranking and a baseline ranking on the same holdout.

    Args:
        model_ranking: Your model's candidate IDs, best first.
        baseline_ranking: The baseline's candidate IDs, best first.
        holdout_ids: The set of true answer IDs.
        ks: The depths to score at.

    Returns:
        A dict mapping each k to ``{"model": hits, "baseline": hits}``.
        Both rankings are always scored with the same k and the same
        holdout; that sameness is what makes the comparison fair.
    """
    return {
        int(k): {
            "model": hits_at_k(model_ranking, holdout_ids, int(k)),
            "baseline": hits_at_k(baseline_ranking, holdout_ids, int(k)),
        }
        for k in ks
    }


def summarize(
    model_ranking: Sequence[Hashable],
    baseline_ranking: Sequence[Hashable],
    holdout_ids: Set[Hashable],
    ks: Iterable[int] = (10, 50, 100),
    baseline_name: str = "baseline",
) -> str:
    """Format an evaluation as a short human-readable report string."""
    lines = [f"Holdout size (post-cutoff positives): {len(holdout_ids)}"]
    for k, scores in evaluate(model_ranking, baseline_ranking, holdout_ids, ks).items():
        lines.append(
            f"hits@{k}: model = {scores['model']}, {baseline_name} = {scores['baseline']}"
        )
    return "\n".join(lines)
