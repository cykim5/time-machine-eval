# Worked example: the Gene-ius evaluation

This page writes up one real use of the time machine method, using only the Gene-ius project's own reported facts and results. Nothing here is estimated or reconstructed; where the project did not report a detail, this page does not invent one.

## The project

Gene-ius is an AI agent (LLM agents, knowledge graphs, Python, team of 5) that helps laboratories interpret genetic variants of uncertain significance, which account for roughly a third of variants in ClinVar. Across 23 retina and heart genes it ranks which variants to test first, then answers whether a variant is harmful, how it breaks the protein, which disease follows, and what treatment strategy might fit.

## The evaluation problem it faced

The agent ranks variants. The obvious way to test a ranking like this is to check it against variants whose effects are already known. But known effects live in the same public record the agent draws on, so a test built that way can reward the agent for repeating evidence it already had access to. A variant would, in effect, be evidence for itself.

## The time machine design it used

The model sees only data available in January 2023 and is graded on variants experts resolved afterwards, so no variant is ever evidence for itself.

In the vocabulary of the README checklist:

- Cutoff: January 2023.
- Input: only data available in January 2023.
- Test set: variants experts resolved after that date.
- Score: how many later-proven disease variants appear in the top 500 of the ranking (hits@500).
- Baseline: AlphaMissense, scored on the same test.

## Reported result

**From the Gene-ius project:** it found 38 later-proven disease variants in its top 500, against 18 for AlphaMissense.

## What to copy from this example

- The cutoff is a month a reader can point to, not a vague "held-out set."
- The score names its K (500), so a reader knows the size of the net.
- The baseline is a named, published method (AlphaMissense), not a straw man, and it is scored on the identical test set.
- The result is reported as a pair of numbers. Either number alone would be much weaker evidence.
