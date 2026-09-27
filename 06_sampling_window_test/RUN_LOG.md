# Run log: the sampling-window test (Supplementary Section S19)

Everything below is either read off a stored artifact or off the file system.
Where a parameter was not recorded, this log says so rather than supplying a
plausible value.

## Dates

All runs are from **2026-09-22**. Unlike the classification runs of Section 4.3,
which carry only a month, these files carry file-system timestamps, given here
in local time.

| Step | Artifact | Written |
|---|---|---|
| Month-uniform draw fetched | `draw/R1_uniform_raw.json` | 17:32 |
| Uniform blind batches built | `blind_batches/R1_blind_batch_*.json` | 17:32 |
| Uniform design scored | `labels/R1_labels_batch_*.json` | 17:34–17:35 |
| Panel-subsample blind batches built | `blind_batches/R1c_blind_batch_*.json` | 17:36 |
| Panel subsample scored | `labels/R1c_labels_batch_*.json` | 17:39–17:48 |

The ten instances of each design ran concurrently, which is why ten label files
share a two-minute window in the first design. The second design's spread is
wider because one instance took longer than the others: the one scoring
panel-subsample batch 05, which switched model partway through (see below).

## The raters

| | |
|---|---|
| Model | `claude-opus-5`, except that the instance scoring panel-subsample batch 05 switched to `claude-opus-4-8` partway through, after the newer model's safety filter stopped on a question in its batch, and wrote that batch's labels (Supplementary Section S19.2) |
| Instances | 20 total, 10 per design, one per batch |
| Instance reuse | none; each batch went to a separate instance, and no instance saw another's output |
| Batch size | 118–120 questions (uniform design), 120 (panel subsample) |
| Prompt | `PROMPT.md`, verbatim and identical across instances but for three substitutions listed there |
| Sampling parameters | **not set and not recorded.** No temperature, top-p or seed was specified; the instances ran at the platform default, and the stored outputs carry no record of what that was. |
| Per-call metadata | **none.** The label files carry `id`, `score`, `label`, `why` and nothing else — no endpoint, no timestamp, no model version string. The model name above is read from the instances' own task transcripts, which are outside this package. |

This is the same situation as the earlier classification described in
`01_panels_and_classification` and in Section 4.3 of the manuscript: the rating
was done by model sessions, not by a script calling an endpoint, so none of the
scripts for this test calls a model and re-running them will not regenerate the
labels. (The GLM runs elsewhere in the package are the exception: they were
scripted endpoint calls.) The labels themselves are shipped for that reason.

**What this costs a replicator.** The analysis is fully reproducible from the
stored labels. The labels are not reproducible: a fresh run would draw fresh
outputs, and at an unrecorded temperature it would not draw the same ones. A
replicator who wants an independent check should re-score the shipped blind
batches with a rater of their choosing and re-run `scripts/R1d_analyze.py`; the
design comparison it computes is valid for any rater applied to both batch sets,
which is the property Section S19.3 relies on.

## Blinding, as verified from the shipped files

| Check | Uniform design | Panel subsample |
|---|---|---|
| Batches | 10 | 10 |
| Distinct months per batch (min–max, of 30) | 29–30 | 29–30 |
| Spearman rank correlation, token number vs. real question id | 0.065 | 0.004 |
| Date, month or stratum field present in any batch | none | none |
| Real question id present in any batch text | none | none |
| Existing label or score present in any batch | none | none |
| Every input item labelled exactly once | yes | yes |

These are recomputed by `scripts/R1_sensitivity.py`, which writes them to
`results/R1_sensitivity_result.json` under the key `blinding`.

Two cues to period survive inside the question text itself and were left there
because removing them would make this instrument differ from the one that scored
the panel: a four-digit year (30 of 1,198 draw questions, 24 of 1,200 panel
questions) and an AI-related term matched by the pattern given in S19.2 (15 and
14). The pattern is not limited to post-2022 names: it also matches Copilot,
OpenAI and GPT-3, and 3 of the 14 panel matches are pre-period questions. Both
cues are removed in sensitivities reported in S19.3.

## Reproducing the analysis

The scripts read the panel from `_legB_data` in the authors' working tree. In
this package that data is at `01_panels_and_classification/data/`. `R1_coverage.py`
and `R1_composition.py` read it through a `LEGB` constant at the top; the other four
scripts carry the path as inline literals, so edit each occurrence.

Order:

```
python scripts/R1_coverage.py      # window widths and coverage      -> results/R1_coverage_result.json
python scripts/R1_analyze.py       # comparison 1 (cross-rater)      -> results/R1_result.json
python scripts/R1c_analyze.py      # comparison 2 (rater isolated)   -> results/R1c_result.json
python scripts/R1d_analyze.py      # comparison 3 (design isolated)  -> results/R1d_result.json
python scripts/R1_sensitivity.py   # sensitivities, refits, blinding -> results/R1_sensitivity_result.json
                                   #                                    results/R1_gamma_refits_result.json
python scripts/R1_composition.py   # bin composition (log s4/s1)     -> results/R1_composition_result.json
```

`R1_coverage.py` asserts every window and coverage figure against the value
printed in the manuscript and refuses to write if any disagrees; it caught two
mislabelled definitions on its first run.

`R1_uniform_draw_fetch.py` re-fetches the draw from the Stack Exchange API. It
will not return the same questions: the API is live, and the script's stratum
offsets are seeded but the question set at those offsets is whatever the
platform holds at fetch time. The draw as used is shipped in `draw/`.

## Not in this package

The two scripts that applied these results to the manuscript text
(`R1_writeback_b.py`, `R1_fix_c.py`) are excluded. They edit prose, reproduce no
number, and carry local file-system paths.
