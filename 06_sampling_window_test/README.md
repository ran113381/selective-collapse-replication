# 06_sampling_window_test: a direct test of the within-month sampling window (Supplementary Section S19)

## What this directory tests

The main panel takes, in each month, the first 100 questions created in that month
(see `01_panels_and_classification`). As platform volume collapsed, the time needed
to fill those 100 widened: a mean of 6.8 hours in the pre-period, 55.4 hours in the
post period, and 9.75 days in the final month. The pre-period sample therefore holds
no observation from later in the month, a region the post-period sample routinely
reaches.

That is a structural gap rather than a power problem: the panel has no observation
in that region, so no reweighting of the panel itself can fill it. The only remedy
is to draw new questions. This directory holds that draw and its analysis.

## Three comparisons

| | What changes | Result (Welch 95%) | What it can say |
|---|---|---|---|
| R1 | sampling rule and rater together | +0.199 [−0.007, +0.406] | something moved, but not which of the two |
| R1c | rater only (the same panel questions) | +0.098 [−0.040, +0.235] | the raters themselves drift across periods |
| R1d | sampling rule only (rater held fixed) | −0.002 [−0.190, +0.186] | the test of the sampling rule |

Read alone, R1 looks as if the sampling rule moved the result. R1c shows that part
of that signal is a pure rater effect, and R1d, holding the rater fixed, finds no
movement. A comparison across raters cannot separate the two.

The limits are in S19.4. Converted to the blind classification's scale, the R1d
interval admits a sampling-rule contribution of up to about 0.36, which is 150% of
that classification's 0.240 shift on the matched subsample (on the earlier
classification's scale, 88% of its 0.355 shift), so it cannot exclude a smaller
contribution; and the twelve post-period months drawn have
a median fill of 13.9 hours, against 24.1 for all 42 post-period months, so the test
sits mostly where the artefact it looks for would be small.

## Contents

```
draw/           the month-uniform draw as fetched (1,198 questions) and the two token maps
blind_batches/  the blind batches given to the raters: id/title/tags/body only, 20 files
labels/         the raters' labels: id/score/label/why, 20 files
scripts/        fetch, coverage, the three comparisons, sensitivities, gamma refits, bin composition
results/        all result JSONs and three month-by-month comparison CSVs
PROMPT.md       the rating instruction, verbatim
RUN_LOG.md      run dates, raters, parameters (including those recorded as not set), blinding checks
```

## The draw

Thirty months: all 18 pre-period months and 12 post-period months. Each month is cut
into eight equal time strata; within each stratum a start time is drawn at random and
the next five questions are taken. The random start is needed: taking each stratum's
first question would put the eight start hours on only four values in a 30-day
month, leaving the time-of-day mix incomplete.

Coverage in the pre-period:

| | Main panel | Month-uniform draw |
|---|---|---|
| Beyond the first day of the month | 0.0% | 95.1% |
| Beyond the second day | 0.0% | 91.0% |
| Median time into the month | 3.6 hours | 372.5 hours |
| Days of the month covered (all thirty months) | 11 | 31 |

## Blinding

The raters received the rubric and the question text only. Stack Overflow question
identifiers increase with time, so each was replaced by an opaque token from a
shuffled pool (rank correlation with the identifier 0.065 and 0.004). Batches were
shuffled across months, so each spans 29 or 30 of the thirty months. Neither design
is named to the raters: the two sets of batch files differ by one character in
their names, which carries no meaning.

Two kinds of period cue remain in the question text: a four-digit year and an
AI-related term. They were left in place, because removing them would make the
instrument differ from the text the earlier classifier scored, and each is removed
in a sensitivity reported in S19.3.

## Notes

- No script in this directory calls a model. The labels were produced in model
  sessions, as the earlier classification was (see `01_panels_and_classification`).
  The label files carry no endpoint, timestamp or model version string, so the labels
  cannot be regenerated, only reused; every analysis reproduces from them. See
  `RUN_LOG.md`.
- The data paths in the scripts are absolute paths from the machine they were written
  on; adjust them as the last section of `RUN_LOG.md` describes.
- Which files each of the twenty rating sessions touched is listed in
  `07_blind_reclassification/session_access_audit/` (Supplementary Section S19.2).
- `R1_coverage.py` asserts every window and coverage figure against the manuscript and
  stops without writing if any disagrees. On its first run it caught two places where
  the fill and reach measures had been used interchangeably.
