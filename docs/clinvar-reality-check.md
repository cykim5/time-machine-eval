# ClinVar reality check: how much does the database itself move?

This page reports one real measurement: how ClinVar changed between
two dated releases, January 2025 and November 2026. It exists to show
why a time freeze matters at all. If the database barely moved, a
naive test on current data would be nearly harmless. It moves a lot,
mostly by growing.

**What these numbers are:** counts of the database's own churn, that
is, how many variant labels moved between two releases. They are not
a model evaluation and they do not score any model.

## The releases used

Both files are ClinVar `variant_summary` releases from the NCBI
ClinVar archive
(`https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/archive/`):

- Older: `variant_summary_2025-01.txt.gz`, 288,267,418 bytes,
  last modified 2025-01-02.
- Newer: `variant_summary_2026-11.txt.gz`, 457,862,838 bytes,
  last modified 2026-11-05.

The window is about 22 months. One note on the choice: the archive
only keeps roughly the last two years of monthly releases, and the
January 2023 release that the Gene-ius evaluation froze at is no
longer there (it returns a 404), so this check uses the oldest
release still available, January 2025, against the newest one.

Run on 2026-11-12 with `examples/clinvar_reality_check.py` in this
repo. The downloads were deleted after the counts were computed; no
raw ClinVar data is committed here.

## How the counts were made

- Counts are per unique VariationID, not per row. A variant_summary
  file has roughly twice as many rows as variants, because one
  VariationID can appear on several rows (one per allele). Only the
  first row for each ID is kept.
- Each variant is put in one of four categories from its
  ClinicalSignificance field: "uncertain" if the field contains
  "Uncertain", "pathogenic" if it contains "Pathogenic", "benign" if
  it contains "Benign", and "other" otherwise (conflicting, not
  provided, drug response, and similar). The uncertain check runs
  first, so a mixed label that mentions uncertainty counts as
  uncertain. "Resolved" means pathogenic or benign.
- Both files were streamed through gzip one line at a time; only one
  category code per variant was held in memory.

## The counts

| | January 2025 release | November 2026 release |
| --- | --- | --- |
| Rows in the file | 6,181,555 | 9,345,867 |
| Unique variants | 3,122,952 | 4,707,240 |
| Duplicate rows skipped | 3,058,603 | 4,638,627 |
| Duplicate rows disagreeing with the kept row | 0 | 0 |
| Uncertain (VUS) variants | 1,508,670 (48.3%) | 2,434,008 (51.7%) |

Overlap between the two releases:

- Variants in both releases: 3,113,336
- Variants only in the newer release: 1,593,904 (33.9% of the newer file)
- Variants only in the older release: 9,616

What happened to the 1,508,670 variants that were uncertain in
January 2025:

- Resolved by November 2026: 1,939 (0.13% of them), of which 1,062
  pathogenic and 877 benign
- Still uncertain: 1,452,937
- Moved to another label (the "other" bucket): 46,723
- No longer in the file: 7,071

Movement in the other direction:

- Resolved variants that went back to uncertain: 783 (691 pathogenic,
  92 benign)
- Variants that flipped pathogenic to benign or the reverse: 3
  (2 pathogenic to benign, 1 benign to pathogenic)
- Variants whose category changed at all: 81,624 (2.6% of the
  variants present in both releases)

Full transition counts (unique variants, January 2025 to November 2026):

| From / to | Uncertain | Pathogenic | Benign | Other |
| --- | --- | --- | --- |
| Uncertain | 1,452,937 | 1,062 | 877 | 46,723 |
| Pathogenic | 691 | 214,860 | 2 | 3,729 |
| Benign | 92 | 1 | 256,674 | 3,692 |
| Other | 3,028 | 7,705 | 14,022 | 1,107,241 |

## What this means for time-frozen evaluation

Three things stand out, and all three support freezing time rather
than testing on the current database:

1. **The database grows faster than it resolves.** A third of the
   variants in the November 2026 file did not exist in January 2025.
   A model trained and tested on today's ClinVar is partly graded on
   variants that did not exist at any earlier freeze date, so its
   test set is not a fair picture of what it could have known then.
2. **Clean resolutions are rare and slow.** Only 0.13% of uncertain
   variants got a clean pathogenic or benign answer in 22 months.
   That is why a time-frozen test set has to pool across many genes
   and a long window to reach a useful size, as the Gene-ius
   evaluation does, and why the test set size should always be
   reported next to the score.
3. **Labels almost never flip sides.** Only 3 variants in over 3
   million moved between pathogenic and benign. The churn is growth
   plus uncertain variants sliding into the mixed "other" bucket
   (46,723 of them), not experts reversing settled calls. A
   time-frozen test is therefore a test of genuinely new knowledge
   arriving, not of old knowledge being rewritten.

## Limits of this check

- The four categories are a simplification. "Other" is a mixed
  bucket, and a variant moving from uncertain to "other" may have
  gained a conflicting interpretation rather than a clearer one.
- Keeping the first row per VariationID is a judgment call, but it
  costs nothing here: in both releases, zero duplicate rows
  disagreed with the kept row.
- The window is 22 months, not the Gene-ius window. The point is
  the shape of the churn (fast growth, slow resolution), not the
  exact rates, which depend on the window chosen.
