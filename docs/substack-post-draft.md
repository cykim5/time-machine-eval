# Draft post: The exam where the questions were written after the textbook

Status: draft for review. Not published.

---

I helped build an AI agent called Gene-ius, on a team of 5.

Gene-ius helps laboratories interpret genetic variants of uncertain significance. Those variants account for roughly a third of the variants in ClinVar, the big public database of genetic variants and what experts think they do.

Across 23 retina and heart genes, our agent ranks which variants a lab should test first. Then it answers follow-up questions. Is this variant harmful? How does it break the protein? Which disease follows? What treatment strategy might fit?

Building it was the fun part. Grading it honestly turned out to be the hard part.

## The cheating problem I did not expect

The natural way to test a model like ours is to check it against variants whose effects are already known.

But there is a trap in that.

ClinVar keeps growing. When experts resolve a variant and publish the answer, the answer goes into the database. Our agent also reads from that same public record.

So a test variant can quietly be its own evidence. The agent looks smart. It may only be repeating something that was already in its input.

That is called leakage. The answer leaks into the exam.

Once I saw it, I started seeing it everywhere in bio AI. Any field where the database keeps absorbing published results has the same problem.

## Our fix: pretend it is January 2023

We graded the agent with a time machine design.

The model sees only data available in January 2023. Nothing newer. Then we graded it on variants that experts resolved afterwards.

No variant is ever evidence for itself. The resolutions after January 2023 simply did not exist in the model's world.

I think of it as an exam where the questions were written after the textbook was printed. A student can still do well on that exam. But only by understanding the material, not by memorizing the book.

## The result, reported the honest way

We scored the ranking by counting how many later-proven disease variants landed in the model's top 500.

We also scored a named baseline, AlphaMissense, on the exact same test. A single number proves little. A pair of numbers, on the same exam, is something a reader can actually judge.

Here is the pair.

Our agent found 38 later-proven disease variants in its top 500. AlphaMissense found 18.

That is the result I trust most from the whole project. Not because 38 is a big number. Because the exam was built so the model could not have cheated on it.

## How to steal this for your own project

Pick a cutoff date. Write it down before you run anything.

Filter every input to that date. Check the sneaky inputs too, the lookup tables and cached files and pretrained resources. That audit is where most leakage hides.

Build your test set only from labels resolved after the cutoff. Count them, and say how many you got.

Score your model in the top K. Score your baseline in the same top K, on the same test set. Report both numbers together, with the cutoff and the test set size.

Two warnings from doing it once.

First, you need enough labels after your cutoff. Too few, and the numbers jump around and prove nothing.

Second, never choose the cutoff after looking at your results. Picking the date that flatters your model is the same cheating, one level up.

I put the small starter code and a checklist in a public repo, so the next team does not have to reinvent the bookkeeping.

## Why I keep thinking about this

Models in science are getting better very fast. Our ways of grading them are not keeping up.

A fair exam is not paperwork. It is the difference between a model that memorized the past and a model that can actually help with the next variant, the next patient, the next experiment nobody has run yet.

That second kind is the only kind worth building.
