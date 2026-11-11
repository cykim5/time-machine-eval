# Time Machine Eval

**How to grade a bio AI model without letting it cheat**

A small methods template for evaluating predictive models on scientific databases that keep changing. It comes from a problem we hit in a real project (see the worked example below), and it is written so another builder can copy the pattern in an afternoon.

Status: a personal methods note and starter code, not a released product. The example numbers in this repo are either from the worked example project, labeled as its reported results, or from a tiny made-up dataset used to demo the code.

## The problem: the database already knows the answers

Many bio AI models learn from, and are tested on, public scientific databases. ClinVar is a good example. ClinVar collects genetic variants and what experts have concluded about them: harmful, harmless, or still uncertain.

Databases like this keep growing. When experts resolve a variant and publish the result, that result becomes part of the database.

Now think about testing a model:

1. You train or build the model using the database.
2. You test the model on variants taken from the same database.
3. Some of those test answers were added to the database before your model ever saw them, and the model may have used them as input.

A high score in that setup can mean two very different things:

- The model learned real patterns and can judge new variants.
- The model memorized answers that were already in its input.

A naive test cannot tell these apart. It rewards memorization and calls it skill. This problem is often called leakage, because the answer leaks into the input.

## The fix: freeze time

Pretend it is an earlier date, and grade the model on the future it could not have seen.

1. Pick a cutoff date, for example January 2023.
2. Give the model only the data that existed on or before that date. Nothing later, not even indirectly through a feature, a lookup table, or a pretrained resource that quietly contains newer records.
3. Build your test set only from labels that were resolved after the cutoff date.
4. Run the model, rank its predictions, and score the ranking against that future test set.

A plain language version: it is an exam where the questions were written after the textbook was printed. A student can still do well, but only by understanding the material. Memorizing the textbook is not enough, because the answers are not in it.

One rule makes the whole thing honest: a record can never be evidence for itself. If a variant was resolved after the cutoff, that resolution, and anything derived from it, stays out of the model's input.

## The scoring: hits in the top K, against a baseline

Most of these models output a ranking, a list of candidates ordered from most promising to least promising. So the natural score is:

- **Hits@K**: how many of the true answers appear in the top K places of the ranking. For example, hits@500 counts how many later-proven disease variants sit in the model's top 500.

One more step is essential: **run the same scoring for one named baseline** and report both numbers side by side. A baseline is a simpler method to compare against, for example an existing published score, a popularity ranking, or last year's approach. "38 hits" means little alone. "38 hits, against 18 for the baseline, on the same test set" is a result a reader can judge.

Report these together, every time:

- The cutoff date
- How many test labels were resolved after the cutoff
- The value of K
- Your model's hits@K
- The named baseline and its hits@K on the identical test set

## When this method applies, and when it does not

It applies when:

- Your data source keeps dated records of when each fact became known (publication dates, submission dates, resolution dates).
- Enough new labels arrive after your cutoff to make a real test set.
- Your model produces a ranking or a score you can turn into a ranking.

It does not work well when:

- Records have no reliable dates, or dates were overwritten as records were updated. A freeze you cannot reconstruct is not a freeze.
- Almost nothing was resolved after your cutoff, so the test set is tiny and the numbers jump around.
- The thing you are evaluating is not a prediction about the world, for example a summarizer or a search tool. Time freezing tests predictive judgment; it says little about other kinds of quality.
- You pick the cutoff after looking at your results. Choosing the date that makes your model look best is the same cheating, one level up. **Pick the cutoff first, write it down, and keep it.**

## The checklist

Copy this list into your own project and work through it in order.

- [ ] Name the database (or databases) your model uses as input.
- [ ] For each one, find the date field that says when a fact became public, not when the underlying event happened.
- [ ] Choose a cutoff date and write it in your README before running any evaluation. Pick a date with enough resolved labels after it to grade on.
- [ ] Filter every input to records dated on or before the cutoff. Check indirect inputs too: lookup tables, embeddings, pretrained models, cached files.
- [ ] Build the test set from labels resolved after the cutoff only. Record how many positive labels that gives you.
- [ ] Freeze both sets. Save the lists of record IDs so the exact same split can be rerun later.
- [ ] Run your model and save its full ranked list, not just the top few.
- [ ] Get the baseline ranking for the same candidates from the named baseline.
- [ ] Score hits@K for your model and for the baseline, with the same K and the same test set. The code in `src/time_machine_eval.py` does this part.
- [ ] Report the cutoff, the test set size, K, and both hit counts together. If the baseline wins, report that too.

## Worked example: Gene-ius

Gene-ius is an AI agent (LLM agents, knowledge graphs, Python, team of 5) that helps laboratories interpret genetic variants of uncertain significance, which account for roughly a third of variants in ClinVar. Across 23 retina and heart genes it ranks which variants to test first, then answers whether a variant is harmful, how it breaks the protein, which disease follows, and what treatment strategy might fit.

It was evaluated with a time machine design: the model sees only data available in January 2023 and is graded on variants experts resolved afterwards, so no variant is ever evidence for itself.

**Reported result from the Gene-ius project:** it found 38 later-proven disease variants in its top 500, against 18 for AlphaMissense.

That sentence is the whole method in one line: a January 2023 freeze, a post-freeze test set, hits@500, and a named baseline (AlphaMissense) scored on the same test.

A fuller write-up is in [docs/geneius-worked-example.md](docs/geneius-worked-example.md).

## Run the demo

The repo includes a tiny made-up example so you can see the pattern work in a few seconds. It uses only the Python standard library.

```
python3 examples/synthetic_example.py
```

It builds fake records dated before and after a cutoff, freezes the input, builds a test set from the later records, then prints hits@K for a fake model ranking and a fake baseline ranking.

## Repository structure

```
time-machine-eval/
  README.md                      this file
  docs/
    geneius-worked-example.md    the Gene-ius evaluation, written up in full
    substack-post-draft.md       a draft blog version of this explainer
  src/
    time_machine_eval.py         the reusable pattern: freeze, holdout, hits@K
  examples/
    synthetic_example.py         a small made-up dataset that runs end to end
```

## Limits of this template

- The code handles the bookkeeping (dates, holdout, hits@K). It cannot check your indirect inputs for you; that audit is manual and it is where most leakage hides.
- A time-frozen test is one honest test, not the only test. It complements, and does not replace, checks on data quality, calibration, and performance on the cases your users actually have.
- Small post-cutoff test sets give noisy numbers. Treat small differences between a model and a baseline as undecided, not as a win.
