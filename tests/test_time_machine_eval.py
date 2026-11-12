"""Unit tests for the time machine evaluation module.

Standard library unittest only, so the suite runs anywhere Python does:

    python3 -m unittest discover tests

Run from the repository root.
"""

import sys
import unittest
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from time_machine_eval import (
    build_holdout,
    evaluate,
    filter_to_cutoff,
    hits_at_k,
    parse_date,
    summarize,
)


def record(record_id, date_value, is_positive=True):
    return {"id": record_id, "date": date_value, "is_positive": is_positive}


class TestParseDate(unittest.TestCase):
    def test_date_object_passes_through(self):
        self.assertEqual(parse_date(date(2023, 1, 31)), date(2023, 1, 31))

    def test_datetime_keeps_only_the_date_part(self):
        self.assertEqual(
            parse_date(datetime(2023, 1, 31, 23, 59, 59)), date(2023, 1, 31)
        )

    def test_iso_string(self):
        self.assertEqual(parse_date("2023-01-31"), date(2023, 1, 31))

    def test_string_with_surrounding_whitespace(self):
        self.assertEqual(parse_date("  2023-01-31\n"), date(2023, 1, 31))

    def test_invalid_month_raises_value_error(self):
        with self.assertRaises(ValueError):
            parse_date("2023-13-01")

    def test_nonsense_string_raises_value_error(self):
        with self.assertRaises(ValueError):
            parse_date("not-a-date")

    def test_empty_string_raises_value_error(self):
        with self.assertRaises(ValueError):
            parse_date("")

    def test_none_raises_type_error(self):
        with self.assertRaises(TypeError):
            parse_date(None)

    def test_number_raises_type_error(self):
        with self.assertRaises(TypeError):
            parse_date(20230131)

    def test_list_raises_type_error(self):
        with self.assertRaises(TypeError):
            parse_date([2023, 1, 31])


class TestFilterToCutoff(unittest.TestCase):
    def test_keeps_records_on_or_before_cutoff(self):
        records = [
            record("before", "2022-06-15"),
            record("on-day", "2023-01-31"),
            record("after", "2023-02-01"),
        ]
        frozen = filter_to_cutoff(records, "2023-01-31")
        self.assertEqual([r["id"] for r in frozen], ["before", "on-day"])

    def test_cutoff_day_itself_is_included(self):
        records = [record("only", "2023-01-31")]
        self.assertEqual(len(filter_to_cutoff(records, "2023-01-31")), 1)

    def test_preserves_original_order(self):
        records = [
            record("c", "2022-01-01"),
            record("a", "2022-02-01"),
            record("b", "2022-03-01"),
        ]
        frozen = filter_to_cutoff(records, "2023-01-31")
        self.assertEqual([r["id"] for r in frozen], ["c", "a", "b"])

    def test_empty_input_returns_empty_list(self):
        self.assertEqual(filter_to_cutoff([], "2023-01-31"), [])

    def test_cutoff_as_date_object(self):
        records = [record("old", "2022-01-01"), record("new", "2024-01-01")]
        frozen = filter_to_cutoff(records, date(2023, 1, 31))
        self.assertEqual([r["id"] for r in frozen], ["old"])

    def test_custom_date_key(self):
        records = [{"id": "x", "resolved": "2022-05-05"}]
        frozen = filter_to_cutoff(records, "2023-01-31", date_key="resolved")
        self.assertEqual(len(frozen), 1)

    def test_missing_date_key_raises_key_error(self):
        with self.assertRaises(KeyError):
            filter_to_cutoff([{"id": "x"}], "2023-01-31")


class TestBuildHoldout(unittest.TestCase):
    def test_only_post_cutoff_positives_join(self):
        records = [
            record("pre-positive", "2022-01-01", True),
            record("on-day-positive", "2023-01-31", True),
            record("post-positive", "2023-02-01", True),
            record("post-negative", "2023-02-01", False),
        ]
        self.assertEqual(build_holdout(records, "2023-01-31"), {"post-positive"})

    def test_empty_when_nothing_resolved_after_cutoff(self):
        records = [record("old", "2022-01-01", True)]
        self.assertEqual(build_holdout(records, "2023-01-31"), set())

    def test_empty_input_returns_empty_set(self):
        self.assertEqual(build_holdout([], "2023-01-31"), set())

    def test_duplicate_ids_collapse_to_one(self):
        records = [
            record("dup", "2023-06-01", True),
            record("dup", "2023-07-01", True),
        ]
        self.assertEqual(build_holdout(records, "2023-01-31"), {"dup"})

    def test_truthy_labels_count_as_positive(self):
        records = [
            record("one", "2023-06-01", 1),
            record("yes", "2023-06-01", "yes"),
            record("zero", "2023-06-01", 0),
            record("none", "2023-06-01", None),
        ]
        self.assertEqual(build_holdout(records, "2023-01-31"), {"one", "yes"})

    def test_missing_label_field_is_not_positive(self):
        records = [{"id": "x", "date": "2023-06-01"}]
        self.assertEqual(build_holdout(records, "2023-01-31"), set())

    def test_custom_keys(self):
        records = [{"vid": "v1", "when": "2023-06-01", "label": True}]
        self.assertEqual(
            build_holdout(
                records,
                "2023-01-31",
                date_key="when",
                id_key="vid",
                label_key="label",
            ),
            {"v1"},
        )


class TestHitsAtK(unittest.TestCase):
    def test_basic_count(self):
        ranking = ["a", "b", "c", "d", "e"]
        self.assertEqual(hits_at_k(ranking, {"b", "d"}, 3), 1)
        self.assertEqual(hits_at_k(ranking, {"b", "d"}, 4), 2)

    def test_k_larger_than_ranking_scores_whole_list(self):
        ranking = ["a", "b"]
        self.assertEqual(hits_at_k(ranking, {"a", "b"}, 500), 2)

    def test_k_zero_returns_zero(self):
        self.assertEqual(hits_at_k(["a", "b"], {"a", "b"}, 0), 0)

    def test_negative_k_raises_value_error(self):
        with self.assertRaises(ValueError):
            hits_at_k(["a"], {"a"}, -1)

    def test_boundary_tie_only_the_one_inside_top_k_counts(self):
        # Two holdout IDs sit right at the boundary: one at position k,
        # one at position k + 1. Only the first is a hit at k.
        ranking = ["x", "y", "hit-in", "hit-out"]
        self.assertEqual(hits_at_k(ranking, {"hit-in", "hit-out"}, 3), 1)
        self.assertEqual(hits_at_k(ranking, {"hit-in", "hit-out"}, 4), 2)

    def test_duplicate_ids_in_ranking_count_once(self):
        # A ranking that repeats an ID must not inflate the score.
        ranking = ["a", "a", "a", "b"]
        self.assertEqual(hits_at_k(ranking, {"a"}, 4), 1)
        self.assertEqual(hits_at_k(ranking, {"a", "b"}, 4), 2)

    def test_empty_ranking_returns_zero(self):
        self.assertEqual(hits_at_k([], {"a"}, 10), 0)

    def test_empty_holdout_returns_zero(self):
        self.assertEqual(hits_at_k(["a", "b"], set(), 10), 0)

    def test_no_overlap_returns_zero(self):
        self.assertEqual(hits_at_k(["a", "b"], {"c", "d"}, 10), 0)


class TestEvaluate(unittest.TestCase):
    def test_scores_both_rankings_at_each_k(self):
        model = ["a", "b", "c"]
        baseline = ["c", "b", "a"]
        holdout = {"a", "c"}
        result = evaluate(model, baseline, holdout, ks=(1, 3))
        self.assertEqual(result[1], {"model": 1, "baseline": 1})
        self.assertEqual(result[3], {"model": 2, "baseline": 2})

    def test_default_ks(self):
        result = evaluate(["a"], ["b"], {"a"})
        self.assertEqual(set(result.keys()), {10, 50, 100})
        self.assertEqual(result[10], {"model": 1, "baseline": 0})

    def test_empty_holdout_gives_zeros(self):
        result = evaluate(["a"], ["b"], set(), ks=(5,))
        self.assertEqual(result[5], {"model": 0, "baseline": 0})

    def test_negative_k_raises_value_error(self):
        with self.assertRaises(ValueError):
            evaluate(["a"], ["b"], {"a"}, ks=(-1,))


class TestSummarize(unittest.TestCase):
    def test_report_string(self):
        report = summarize(["a", "b"], ["c"], {"a"}, ks=(1,), baseline_name="Alpha")
        self.assertIn("Holdout size (post-cutoff positives): 1", report)
        self.assertIn("hits@1: model = 1, Alpha = 0", report)


if __name__ == "__main__":
    unittest.main()
