# Replication package

This package accompanies the manuscript's data availability statement. All data
analysed are public and were retrieved from the Stack Exchange API.

```
01_panels_and_classification/   fetch scripts; per-question classification of
                                18,000 questions in python, java and javascript;
                                the bin-by-month panels
02_estimation/                  dose-response, FE-PPML, share-ratio, event study,
                                pre-trend test and power, placebo cutoffs,
                                permutation and BH-FDR batteries, answer margin
03_validation/                  second-rater agreement; criterion-validity rounds
                                1 and 2; the human gold standard end to end
04_crosssite_engine/            the cross-site design that failed: fetch and
                                estimation scripts, and the 25-check Monte Carlo
                                validation harness
05_additional_checks/           cross-family relabelling, frontier-tier rescoring,
                                GLM answering runs
06_sampling_window_test/        direct test of the within-month sampling window
                                (Supplementary Section S19)
07_blind_reclassification/      the blind re-classification of the python panel on
                                which every python estimate rests, its
                                date-visible diagnostic arm, and a same-model
                                blind run of the earlier classifier
                                (Supplementary S20)
08_criterion_round3/            the third criterion-validity round, the one the
                                manuscript reports (Section 6.3, Supplementary S13)
09_downstream_rerun/            every python check re-run on both label sets, with
                                the outputs, logs and comparison files
```

**Read this first.** The python panel was classified twice. The labels in
`01_panels_and_classification/data/` are the *earlier* classification, whose batch
files carried each question's date, vote score and answer count (Supplementary
Section S20.1 explains how this was found). Every python estimate in the manuscript
now rests on the *blind* classification in `07_blind_reclassification/labels/`;
the earlier labels are kept as a second rating of the same questions, and they are
the only labels the javascript and java panels have. The earlier classifier was
later re-run blind on the same batches as a check
(`07_blind_reclassification/same_model_sonnet46/`, Supplementary Section S20.6);
no estimate rests on that run.

Total size 65 MB.

---

## What each directory contains

### 01_panels_and_classification

Fetch: `fetch_so_questions.py` takes the first 100 questions created in each
calendar month in creation order, which is the sampling rule Section 4.1
describes; `fetch_so_activity.py` holds the shared throttling and key handling;
`fetch_so_tags.py` retrieves platform monthly totals.

Classification pipeline: `split_batches.py` cuts the panel into per-month
batches, each batch is scored, and `aggregate_labels.py` assembles the
per-question CSVs and the monthly panels. Estimators `run_within_so_llm.py` and
`run_within_so.py` fit the dose-response, the binary contrast and the event
study.

`CLASSIFY_RUBRIC.md` is the operative rubric, in its original Chinese.
`CLASSIFY_RUBRIC_EN_translation.md` is an English translation prepared for
readers of this package; no rater saw it, and where the two differ the original
governs.

`data/` holds the raw question text for 6,000 questions in each of the three
languages, the per-question labels, and the 60-month panels. The panel values
were checked cell by cell against the published panels: 1,440 cells, no
disagreement.

`data/rationale_batches_*` holds the classifier's stated reason for each
question. **This is complete for java and javascript across all 60 months and
for python through 2024-06 (37 of 60 months, 3,700 questions). The 2,300-question
python extension from 2024-07 onward retains the final score and label but not
the per-item rationale.** The analysis reads the stored labels, so the gap is in
the audit trail of one segment of the labelling step, not in the input to any
estimate. The data availability statement in the manuscript states this limit.

### 02_estimation

The estimation and robustness scripts, including
`review_r1_reviewer_response_scripts/`, which holds the scripts written for a
round of pre-submission review. Two of those scripts were missing from earlier
versions of this package although the manuscript used their output, and have been
added unchanged with the outputs they produced at the time:
`p1_12_ninety_day_window.py` (the ninety-day duplicate-closure table of
Supplementary Section S17) and `p1_parallel_trends_sensitivity.py` (the pre-period
drift and breakdown values of Section 6.2). As shipped, the scripts in this
directory read the earlier classification; `09_downstream_rerun/` re-runs them on
both label sets. `bh_fdr_table1_family.py` computes the
Benjamini–Hochberg correction reported in Section 7.1 of the manuscript from the
p values printed in its Table 1; the BH block inside `phaseA_composition.py` is an
earlier, different family. `asker_cohort_prelim.py` and `asker_rival_test.py` are
superseded (Supplementary Section S16) and their shipped outputs predate a later
edit of the scripts, so re-running them does not reproduce those outputs; the
manuscript cites only `asker_rival_exact.py` and `asker_tenure.py`, whose outputs
re-run exactly.

### 03_validation

- `second_rater_kappa/` — the 200-question comparison between the second rater
  and the earlier classification, with both sets of per-item scores.
  `kappa_results.json`, written at the time, names the two raters
  (`sonnet-4.6 (primary)`, `opus-4.8 (independent, blind)`); it is the record on
  which the manuscript's attribution of the earlier classification to Claude
  Sonnet 4.6 rests (Supplementary Section S3).
- `criterion_validity_rounds1_2/` — the first two rounds in full: scripts, the
  blind answer and judgment batches for all four answering models, and the
  results. Both are superseded by the third round in `08_criterion_round3/`.
  The second round's sample was drawn through an API call whose default page size
  of 30 truncated each lookup and ordered it by activity, so 316 of its 320
  questions came from after the event; it is kept because the manuscript
  describes it, not because any reported figure rests on it.
- `gold_standard/` — the 300-question human coding. The two coders' completed
  sheets under the revised questionnaire (`coding_sheet_A_v2.csv`,
  `coding_sheet_B_v2.csv`; the coders are identified only as A and B), the
  completed adjudication record (`裁决记录表.csv`), the classifier's labels for
  the 300 questions (`answer_key_封存勿开.csv`, named for having been sealed
  from the coders while they worked), the question files, and the list of the
  four questions with dates written into their text. `score_gold_v2.py`
  reproduces the reliability figures of Section 4.4 and `score_adjudication.py`
  the comparison of the adjudicated standard with the classifier; both run from
  this directory as shipped. The subfolders hold the questionnaire in both
  versions, the adjudication questionnaire with its blank record, and the blank
  post-adjudication forms. Coder-facing material is in Chinese.

### 04_crosssite_engine

`run_so_did.py`, `run_so_did_v2.py` (whose `--simulate` flag is the entry point
to the 25-check Monte Carlo harness) and `honest_did.py`.
`monte_carlo_harness_output/` holds the harness pass table and the output for
the real three-site design, which matches the table in the manuscript digit for
digit. `data/` holds the three sites used in the final design; four sites that
were fetched during exploration but did not enter it are kept separately under
`data/exploratory_not_in_final_3site_design/` rather than removed.

### 05_additional_checks

Cross-family relabelling, frontier-tier rescoring and the GLM answering runs.
The script that scanned answers for misalignment (Supplementary Section S15) is
not in this package. The one batch it corrected ships in
`03_validation/criterion_validity_rounds1_2/batches_haiku45/` in its original
(`answer_out_9_preswapfix.json`) and corrected (`answer_out_9.json`) form, with
the re-judgment (`judge_batch_swapfix.json`, `judgment_out_swapfix.json`). The
outputs of the discarded empty-completion GLM-4.6 answering run are not in this
package either. The blind batches for the four answering models live with the
criterion-validity tree in `03_validation` and are not duplicated here.

### 06_sampling_window_test

The direct test of the within-month sampling window reported in Supplementary
Section S19: the month-uniform draw, the blind batches and labels for both
designs, the analysis and sensitivity scripts with their result files, the
verbatim rating instruction (`PROMPT.md`), and a run log (`RUN_LOG.md`) giving
dates, model, instance count, and the sampling parameters that were not set.
That directory has its own README.

### 07_blind_reclassification

The re-classification of all 6,000 python questions by Claude Sonnet 5 under full
blinding (Supplementary Section S20).

- `design/` — three files. `R2_design_document_zh.md` is the design document,
  written before any new label existed, in its original Chinese; it may only be
  appended to, and its departure record now holds sixteen entries.
  `R2_design_sha256.txt` records the document's SHA-256 before the first batch was
  dispatched and after each of fourteen appends, two of which added entries that were
  later overwritten; the headings inside the document count only the appends that
  survive. `R2_design_document_zh_overwritten_20260923.md` is the version holding
  those two entries, recovered from the coding assistant's file checkpoint; they
  were overwritten when the working session was rolled back to a point before the
  decision they recorded. The desktop application's log records that rewind, and
  the session logs record no write to the document between the second of those
  appends and the rollback (Supplementary Section S20.5). The hash file and the document refer to these two documents by their
  working names, `R2_设计书_盲重标与效标重抽_20260923.md` and
  `R2_blind\R2_设计书_被覆盖版本_20260923_2127.md`. Every hash in the hash file
  equals the SHA-256 of a prefix of the current document or of the overwritten
  version. Lines of the hash file end in LF or CRLF depending on the tool that
  appended them; no hash depends on this.
- `blind_batches/` — the fifty input batches (fields `id`, `title`, `tags`,
  `body` only), the instruction template, the token map from opaque token to
  question identifier, and the token-to-month map used only at analysis time.
- `labels/` — the fifty model output files, one per batch, and the assembled
  per-question labels and monthly panel.
- `armB_date_visible/` — the diagnostic arm: eighteen whole months in exactly the
  format the earlier classification read, the instruction, and the outputs.
- `scripts/` — batch construction with its blinding checks (`R2_build_blind.py`),
  assembly (`R2_collect.py`), the pre-specified analysis (`R2_analyze.py`, which
  first reproduces the earlier classification's published estimate), and the
  diagnostic arm (`R2v_build.py`, `R2v_analyze.py`).
- `dispatch_log.jsonl` — the verbatim task text of every model session launched
  for this round, the diagnostic arm and the third criterion round, with the
  dispatch time and the model tier requested, exported from the working-session
  records by `09_downstream_rerun/scripts/R2_export_dispatch.py`. A first export
  ended before the GLM-5.3 judging sessions ran; the log was exported again to
  include them and the judgment of the top-up answer, and the re-export reproduces
  the first export's entries exactly. Five dispatch attempts that were refused by a
  concurrency limit and never ran are not listed.
- `same_model_sonnet46/` — the blind re-run of the earlier classifier, Claude
  Sonnet 4.6, registered in the design document's thirteenth entry and carried out
  under its fifteenth (Supplementary Section S20.6). No estimate in the manuscript
  rests on it. `instruction/` holds the task template (the blind classification's,
  with only the input and output paths changed), the fifty task texts as issued
  with their SHA-256, and `input_manifest.json`, whose hashes show that the input
  batches are byte-identical to those in `blind_batches/`, so they are not
  duplicated here. `labels/` holds the fifty output files, the assembled
  per-question labels and monthly panel, and, in `_superseded/`, the first output of
  batch 34, set aside because the verification script could not identify the turn
  that wrote it; that batch was run again with the same task text. In `scripts/`,
  `R2s46_verify.py` reads the model identifier logged for every step of every
  sub-session and checks each label file (`results/R2s46_verify_result.json`);
  `R2s46_export_dispatch_log.py` exports `dispatch_log_s46.jsonl` from the launching
  session's record and checks each task text against
  `instruction/dispatch_prompts.json`; `R2s46_analyze.py` runs the three
  pre-specified analyses after first reproducing the earlier classification's
  published gradient and *κ* and the blind classification's estimates and *κ*
  (`results/R2s46_analyze_result.json`, which also lists each batch's writing model
  and number of launches); and `R2s46_numbers.py` records the conversions behind the
  figures the manuscript quotes (`results/R2s46_numbers_result.json`). The first two
  read the working-session records, which are not in the package, from a path given
  on the command line. In `dispatch_log_s46.jsonl` the probe's `launched` field is
  false because the probe ran in the foreground, so the export found its reply
  rather than a launch notice; the probe's sub-session appears in
  `R2s46_verify_result.json`.

### 08_criterion_round3

The criterion-validity round the manuscript reports (Section 6.3, Supplementary
Sections S2 and S13). `scripts/R2c_fetch_criterion.py` draws 80 questions per bin
of the blind labels from all sixty months, excluding both earlier rounds, and
fetches the questions and reference answers with an explicit page size of 100,
asserting on every call that nothing was truncated; `data/criterion_sample_v3_meta.json`
records the draw and every API call. `R2c_split_and_glm.py` cuts the sample into
sixteen answering batches and runs the two GLM answerers by script with the second
round's instruction and parameters (it resumes, skipping questions already
answered). `R2c_build_judge.py` builds the judging batches, which carry no
substitutability score and no month; `R2c_align_scan.py` is the misfiling scan;
`R2c_analyze.py` and `R2c_labelsets.py` produce the results. `data/batches_*/`
hold, per answerer, every answer and judgment batch, including the Haiku 4.5 items
corrected after the scan, before and after correction. The Claude answerers and
all judges ran in model sessions; their task text is in
`07_blind_reclassification/dispatch_log.jsonl`. The GLM-5.3 answering run took
four passes and a top-up, and was stopped twice when the vendor account ran out of
credit. `data/glm53_run_1_*.log` to `glm53_run_4_*.log` are the passes in order:
the first ends at the credit error, the second resumes it, the third and fourth
retry unanswered questions with the same parameters, and the fourth ends at the
second credit error in batch 12; `glm53_run.log` is a copy of the fourth.
`glm53_run_5_补跑.log` is the top-up (`scripts/R2c_glm53_topup.py`), run under a
rule entered in the design document before any call: it brought every question
still unanswered to at least four attempts and recovered one answer, which is in
`batches_glm53/answer_out_topup.json` with its own judgment batch
(`judge_batch_topup.json`, `judgment_out_topup.json`) and a per-attempt record
(`topup_attempts.json`). The Chinese in the file names reads: 余额中断, stopped by
credit exhaustion; 首轮续跑, first pass resumed; 重试, retry; 补跑, top-up. Seven
of 320 questions have no GLM-5.3 answer, and every answerer is evaluated on the
313 questions all four completed (Supplementary S13 and S15). Four judging sessions,
one per answerer and all on the same forty questions, switched from Claude Opus 5.5
to Claude Opus 4.8 partway through (Supplementary S15). Their judgments, and a second
Opus 4.8 pass over the same batches, are kept under each answerer's
`_superseded_opus48/`; the thirty-nine questions re-judged by Opus 5.5 are in
`judge_batch_89b.json` and `judgment_out_89b.json`, and the one question whose four
judgments remain Opus 4.8's is in `judgment_out_89c.json`.

### 09_downstream_rerun

Every python check in the manuscript re-run on both label sets.
`scripts/R2d_downstream.py` builds two copies of the analysis tree that differ
only in the three label files, runs every label-dependent script in both, and
compares the outputs; the copy on the earlier labels reproduces every published
figure it can be checked against before the blind-label figures are used.
`R2d_extra.py`, `R2d_kappa.py`, `R2d_more.py`, `R2d_gold.py` and `R2d_r1.py`
cover figures whose scripts were not in the package or that read the earlier
labels through another file, each again reproducing the earlier figures first.
`orig/` and `blind/` hold each copy's outputs and logs (not its data, which is
the package's own); `results/paired_logs.md` sets the two logs side by side line
by line, and `results/R2d_compare.json` records every output value that differs.
`R2_collect_numbers.py` gathers the blind copy's outputs and the printed lines of
the scripts that write no JSON into one file, shipped as
`results/R2_numbers_result.json`, and computes the few manuscript figures that are
derived from them (ratios, shares and percentage conversions), with the formula
for each. It runs in the working tree it was written in, whose paths it carries,
and writes its output beside itself. `R2_export_dispatch.py`
produced `07_blind_reclassification/dispatch_log.jsonl` from the working-session
records, which are not in the package; it reads their location from the
environment variable `R2_SESSION_DIR`. `R2m_model_identity.py` reads, from the same records, the model
identifier logged for every step of the third round's judging and answering
sessions and of the sampling-window ratings, and computes the judging agreement
and the two robustness checks of Supplementary Sections S15 and S19.2
(`results/R2m_result.json`, `results/R2m_s19_excl05.json`).
`make_figures_ipm.py` renders the manuscript's figures from these outputs; it is
generated from an older figure script by `R2_make_fig_patch.py`. In the blind
copy's log of `s17_bound_both_samples.py` the sample sizes printed as headings
(5,640 and 5,930) are constants in the script that describe the earlier
classification's samples; the blind samples the figures below them come from
hold 5,201 and 5,467 questions (Supplementary Section S17). These scripts
carry absolute paths from the machine they were written on, like the rest of the
package.

---

## What a replicator should know before starting

**The model calls do not regenerate.** The runs with Claude models (both
classifications, same-family second rating, Claude answering and judging, the
diagnostic arm, the same-model blind run, and the S19 ratings) were done in model sessions, so their stored batch files carry only the per-item
output — score, label and rationale — with no endpoint, no call-level timestamp
and no model version string. The runs with GLM models (cross-family rating,
frontier-tier re-scoring and GLM answering) were scripted calls to the vendor's
endpoint at temperature 0 or 0.2; those scripts are in `05_additional_checks/`
and their outputs in `05_additional_checks/glm_relabel/`. Language-model endpoints are also non-deterministic
and are retired on roughly annual cycles. The package therefore ships the model
outputs themselves rather than only the prompts that produced them, and a fresh
run would draw different outputs rather than recover these. The provenance record
is the month of each run and the model named for it in Section 4.3 of the
manuscript, together with the verbatim instruction and run log shipped with the
S19 test and the verbatim dispatch log in `07_blind_reclassification/`.

**The numbers have not been regenerated end to end by re-running every script.**
Many estimation scripts require live API access, and several rating scripts would
need model snapshots that may no longer exist. What has been verified is
structural: the scripts are present, the data are present, and the aggregated
panel values match the published panels cell for cell. A full re-run has not been
performed and this package does not claim one.

Some scripts carry absolute paths from the machine they were written on. Adjust
the path constants at the top of a script before running it.

**The analysis code was written with an AI coding assistant.** As Section 4.3 of
the manuscript states, the scripts in this package were written with Claude Code
(Anthropic) at the author's direction, running
Claude models of the Opus, Sonnet and Fable families. Which model version wrote a
given script was not recorded. Comments and docstrings are working notes from
that process and are partly in Chinese.

**Two model names appear in this package in roles the manuscript does not report
individually.**
Neither enters a reported number.

`Fable 5` answered 28 questions from batches 4 and 5 of the *first* round of the
criterion-validity test, alongside the round's primary answerer, as a check on
whether the result depended on which model was used to operationalize
answerability (`03_validation/criterion_validity_rounds1_2/cross_model_check.py`).
Fable 5 had in fact been launched on all six batches of that round on 24 July
2026; the account's usage credits ran out while the instances were working, and
only the instances for batches 4 and 5 had written their answer files. The next
day those two files were renamed to `answer_out_fable_4.json` and
`answer_out_fable_5.json` and kept, and Haiku 4.5 answered all six batches as the
round's primary answerer.
That first round, at N = 88, is described in the manuscript as diagnostic and was
replaced by a second round and then by a third, each at N = 320 with four
answerers; the third is the round every reported criterion-validity figure comes
from. The round-1 files are
shipped rather than removed because the manuscript discusses that round.

`Fable 5.1` appears in the docstrings of three robustness scripts
(`edit_exposure_check.py`, `memorization_check.py`, `s17_length_conditioned.py`)
recording that the check in question was designed or reviewed by a model instance
separate from the one that wrote the analysis, following a working rule that the
party making a change and the party judging it be different. These instances
produced no estimate: every number those scripts report is computed by the script
from the shipped data, and re-running them reproduces it without any model in the
loop.
