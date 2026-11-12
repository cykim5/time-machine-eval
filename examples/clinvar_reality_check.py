"""Real data check: how much does ClinVar itself change over time?

This script answers one question with real public data: if you freeze
ClinVar at an earlier release and look again later, how many variants
that were uncertain back then have a resolved answer now?

It downloads nothing by default. Give it two dated ClinVar
variant_summary releases (from the NCBI ClinVar archive at
https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/archive/):

    python3 examples/clinvar_reality_check.py \
        --old variant_summary_2025-01.txt.gz \
        --new variant_summary_2026-11.txt.gz

Or let it fetch the two default releases into a temporary folder,
process them, and delete them afterwards:

    python3 examples/clinvar_reality_check.py --download

The files are large (hundreds of megabytes compressed), so both are
streamed through gzip one line at a time. Two small dictionaries are
kept in memory, one category code per unique variant per release.
No raw ClinVar data is ever written into this repository.

One quirk of the data, found by running this script: a
variant_summary file has roughly twice as many rows as variants,
because one VariationID can appear on several rows (one per allele).
Every count here is per unique VariationID, keeping the first row
for each ID, and the number of duplicate rows (and how many of them
disagree with the kept row) is reported alongside the counts.

What the numbers mean, and what they do not mean: the counts below
measure the database's own churn, that is, how many labels moved
between releases. They are not a model evaluation and they do not
score any model. They exist to show why a time freeze matters at
all: a test set drawn from the current database silently includes
answers that did not exist at the freeze date.

Classification rule used here (documented so the run can be redone):
a variant is "uncertain" if its ClinicalSignificance contains
"Uncertain", "pathogenic" if it contains "Pathogenic", "benign" if
it contains "Benign", and "other" otherwise (conflicting, not
provided, drug response, and similar). "Resolved" means pathogenic
or benign. The uncertain check runs first, so a mixed label that
mentions uncertainty counts as uncertain.
"""

import argparse
import gzip
import json
import os
import sys
import tempfile
import urllib.request

OLD_URL = (
    "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/archive/"
    "variant_summary_2025-01.txt.gz"
)
NEW_URL = (
    "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/archive/"
    "variant_summary_2026-11.txt.gz"
)

# Category codes, kept as small ints to save memory.
VUS = 0
PATHOGENIC = 1
BENIGN = 2
OTHER = 3
CATEGORY_NAMES = {VUS: "vus", PATHOGENIC: "pathogenic", BENIGN: "benign", OTHER: "other"}


def categorize(clinical_significance):
    """Map a ClinVar ClinicalSignificance string to one category code."""
    value = clinical_significance or ""
    if "Uncertain" in value:
        return VUS
    if "Pathogenic" in value:
        return PATHOGENIC
    if "Benign" in value:
        return BENIGN
    return OTHER


def iter_variant_rows(path, stats):
    """Yield (variation_id, category) pairs, streaming through gzip.

    Only the two columns this check needs are read. Rows with a
    missing or non-numeric VariationID are skipped and counted in
    ``stats["skipped"]``.
    """
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
        header = handle.readline().rstrip("\n").split("\t")
        try:
            vid_index = header.index("VariationID")
            sig_index = header.index("ClinicalSignificance")
        except ValueError as exc:
            raise ValueError(
                f"{path}: expected VariationID and ClinicalSignificance "
                f"columns, got header: {header[:12]}"
            ) from exc
        for line in handle:
            fields = line.rstrip("\n").split("\t")
            if len(fields) <= max(vid_index, sig_index):
                stats["skipped"] += 1
                continue
            raw_id = fields[vid_index].strip()
            try:
                variation_id = int(raw_id)
            except ValueError:
                stats["skipped"] += 1
                continue
            yield variation_id, categorize(fields[sig_index])


def load_release(path):
    """Read one release into {variation_id: category code}.

    A variant_summary file has more rows than variants: one
    VariationID can appear on several rows (one per allele). Only
    the first row for each VariationID is kept, so every count below
    is per unique variant, not per row. Duplicate rows are counted,
    and duplicate rows that disagree with the kept category are
    counted separately, so the size of that judgment call is visible.
    """
    categories = {}
    rows = 0
    duplicates = 0
    disagreements = 0
    stats = {"skipped": 0}
    for variation_id, category in iter_variant_rows(path, stats):
        rows += 1
        existing = categories.get(variation_id)
        if existing is None:
            categories[variation_id] = category
        else:
            duplicates += 1
            if existing != category:
                disagreements += 1
    return categories, rows, duplicates, disagreements, stats["skipped"]


def compare_releases(old_path, new_path):
    """Compare two releases and return an honest count summary.

    All counts are per unique VariationID. Both releases are loaded
    into small dictionaries (one category code per variant) so that
    duplicate rows can never inflate a count.
    """
    old_categories, old_rows, old_dups, old_dis, old_skip = load_release(old_path)
    new_categories, new_rows, new_dups, new_dis, new_skip = load_release(new_path)

    old_vus = sum(1 for c in old_categories.values() if c == VUS)
    new_vus = sum(1 for c in new_categories.values() if c == VUS)

    transitions = {}
    for variation_id, old_category in old_categories.items():
        new_category = new_categories.get(variation_id)
        if new_category is None:
            continue
        key = (old_category, new_category)
        transitions[key] = transitions.get(key, 0) + 1

    shared = sum(transitions.values())

    def moved(old_cat, new_cat):
        return transitions.get((old_cat, new_cat), 0)

    old_vus_seen = sum(moved(VUS, new_cat) for new_cat in CATEGORY_NAMES)
    resolved_from_vus = moved(VUS, PATHOGENIC) + moved(VUS, BENIGN)
    reverted_to_vus = moved(PATHOGENIC, VUS) + moved(BENIGN, VUS)
    flipped = moved(PATHOGENIC, BENIGN) + moved(BENIGN, PATHOGENIC)
    changed = sum(
        count
        for (old_cat, new_cat), count in transitions.items()
        if old_cat != new_cat
    )

    return {
        "old_file": os.path.basename(old_path),
        "new_file": os.path.basename(new_path),
        "old_total_rows": old_rows,
        "old_unique_variants": len(old_categories),
        "old_duplicate_rows_skipped": old_dups,
        "old_duplicate_rows_disagreeing": old_dis,
        "old_rows_skipped_unreadable": old_skip,
        "old_vus": old_vus,
        "old_vus_share": old_vus / len(old_categories) if old_categories else 0.0,
        "new_total_rows": new_rows,
        "new_unique_variants": len(new_categories),
        "new_duplicate_rows_skipped": new_dups,
        "new_duplicate_rows_disagreeing": new_dis,
        "new_rows_skipped_unreadable": new_skip,
        "new_vus": new_vus,
        "new_vus_share": new_vus / len(new_categories) if new_categories else 0.0,
        "shared_variants": shared,
        "new_only_variants": len(new_categories) - shared,
        "old_only_variants": len(old_categories) - shared,
        "vus_in_old_resolved_in_new": resolved_from_vus,
        "vus_in_old_resolved_pathogenic": moved(VUS, PATHOGENIC),
        "vus_in_old_resolved_benign": moved(VUS, BENIGN),
        "vus_in_old_still_vus_in_new": moved(VUS, VUS),
        "vus_in_old_now_other_in_new": moved(VUS, OTHER),
        "vus_in_old_absent_from_new": old_vus - old_vus_seen,
        "resolved_in_old_reverted_to_vus_in_new": reverted_to_vus,
        "pathogenic_to_benign_or_reverse": flipped,
        "total_changed_category": changed,
        "transitions": {
            f"{CATEGORY_NAMES[o]} -> {CATEGORY_NAMES[n]}": count
            for (o, n), count in sorted(transitions.items())
        },
    }


def download(url, dest_dir):
    filename = os.path.join(dest_dir, url.rsplit("/", 1)[-1])
    urllib.request.urlretrieve(url, filename)
    return filename


def print_summary(results):
    """Print the counts in plain language."""
    print("ClinVar reality check: what changed between two releases")
    print(f"Older release: {results['old_file']}")
    print(f"Newer release: {results['new_file']}")
    print()
    print(
        f"Older release: {results['old_total_rows']:,} rows, "
        f"{results['old_unique_variants']:,} unique variants "
        f"({results['old_duplicate_rows_skipped']:,} duplicate rows skipped, "
        f"{results['old_duplicate_rows_disagreeing']:,} of them disagreeing "
        f"with the kept row)"
    )
    print(
        f"Newer release: {results['new_total_rows']:,} rows, "
        f"{results['new_unique_variants']:,} unique variants "
        f"({results['new_duplicate_rows_skipped']:,} duplicate rows skipped, "
        f"{results['new_duplicate_rows_disagreeing']:,} of them disagreeing "
        f"with the kept row)"
    )
    print(f"Variants in both releases: {results['shared_variants']:,}")
    print(f"Variants only in the newer release: {results['new_only_variants']:,}")
    print(f"Variants only in the older release: {results['old_only_variants']:,}")
    print()
    print(
        f"Uncertain (VUS) in older release: {results['old_vus']:,} "
        f"({results['old_vus_share']:.1%} of variants)"
    )
    print(
        f"Uncertain (VUS) in newer release: {results['new_vus']:,} "
        f"({results['new_vus_share']:.1%} of variants)"
    )
    print()
    print("Of the variants that were uncertain in the older release:")
    print(
        f"  resolved by the newer release: "
        f"{results['vus_in_old_resolved_in_new']:,} "
        f"({results['vus_in_old_resolved_pathogenic']:,} pathogenic, "
        f"{results['vus_in_old_resolved_benign']:,} benign)"
    )
    print(
        f"  still uncertain: {results['vus_in_old_still_vus_in_new']:,}"
    )
    print(
        f"  moved to another label: {results['vus_in_old_now_other_in_new']:,}"
    )
    print(
        f"  no longer in the file: {results['vus_in_old_absent_from_new']:,}"
    )
    print()
    print(
        "Resolved variants that went back to uncertain: "
        f"{results['resolved_in_old_reverted_to_vus_in_new']:,}"
    )
    print(
        "Variants that flipped pathogenic to benign or the reverse: "
        f"{results['pathogenic_to_benign_or_reverse']:,}"
    )
    print(
        "Variants whose category changed at all: "
        f"{results['total_changed_category']:,}"
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Compare two ClinVar variant_summary releases and "
        "count how many uncertain variants were resolved between them."
    )
    parser.add_argument("--old", help="Path to the older release .gz file")
    parser.add_argument("--new", help="Path to the newer release .gz file")
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download the two default releases to a temp folder, "
        "process them, then delete them.",
    )
    parser.add_argument(
        "--output",
        help="Optional path to write the full count summary as JSON.",
    )
    args = parser.parse_args(argv)

    temp_dir = None
    try:
        if args.download:
            temp_dir = tempfile.mkdtemp(prefix="clinvar-reality-check-")
            old_path = download(OLD_URL, temp_dir)
            new_path = download(NEW_URL, temp_dir)
        else:
            if not args.old or not args.new:
                parser.error("--old and --new are required unless --download is used")
            old_path = args.old
            new_path = args.new
        results = compare_releases(old_path, new_path)
    finally:
        if temp_dir is not None:
            for name in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, name))
            os.rmdir(temp_dir)

    print_summary(results)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            json.dump(results, handle, indent=2)
        print(f"\nFull counts written to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
