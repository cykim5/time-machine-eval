"""Time Machine Eval: time-frozen evaluation for bio AI models.

The pattern in one line: freeze your inputs at a cutoff date, then
grade the model only on labels resolved after that cutoff, so no
record is ever evidence for itself.

From the repository root:

    from src import filter_to_cutoff, build_holdout, hits_at_k, evaluate

After ``pip install -e .`` the module is also available top level:

    from time_machine_eval import filter_to_cutoff, build_holdout
"""

from .time_machine_eval import (
    build_holdout,
    evaluate,
    filter_to_cutoff,
    hits_at_k,
    parse_date,
    summarize,
)

__all__ = [
    "build_holdout",
    "evaluate",
    "filter_to_cutoff",
    "hits_at_k",
    "parse_date",
    "summarize",
]
