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
                                (Section 7.1 of the manuscript)
07_blind_reclassification/      the blind re-classification of the python panel on
                                which every python estimate rests, its
                                date-visible diagnostic arm, and a same-model
                                blind run of the earlier classifier
                                (Section 4.2 of the manuscript)
08_criterion_round3/            the third criterion-validity round, the one the
                                manuscript reports (Section 6.3)
09_downstream_rerun/            every python check re-run on both label sets, with
                                the outputs, logs and comparison files
10_shap_transparency/           the surrogate-model (SHAP) analysis of Section 6.3:
                                pre-registered design note and its hash, script,
                                results, run log, and the data rows behind two figures
```

**Read this first.** The python panel was classified twice. The labels in
`01_panels_and_classification/data/` are the *earlier* classification, whose batch
files carried each question's date, vote score and answer count (Section 4.2 of
the manuscript states this). Every python estimate in the manuscript
now rests on the *blind* classification in `07_blind_reclassification/labels/`;
the earlier labels are kept as a second rating of the same questions, and they are
the only labels the javascript and java panels have. The earlier classifier was
later re-run blind on the same batches as a check
(`07_blind_reclassification/same_model_sonnet46/`, Section 4.2 and Table 4 of the manuscript);
no estimate rests on that run.

Total size 68.5 MB, 1,343 files.

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
languages, the per-question labels, and the 60-month panels.
`question_labels_python_2021-2024.csv` holds all sixty months despite its name;
`question_labels_python_ext_2024-07_2026-05.csv` repeats its 2,300 questions from
July 2024 onward with identical scores and must not be concatenated with it. The panel values
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
Section 7.5 of the manuscript) and `p1_parallel_trends_sensitivity.py` (the pre-period
drift and breakdown values of Section 6.2). As shipped, the scripts in this
directory read the earlier classification; `09_downstream_rerun/` re-runs them on
both label sets. `bh_fdr_table1_family.py` computes the
Benjamini–Hochberg correction reported in Section 7.2 and Table 7 of the manuscript from the
p values printed in its Table 2; the BH block inside `phaseA_composition.py` is an
earlier, different family. `asker_cohort_prelim.py` and `asker_rival_test.py` are
superseded (the asker test of Section 7.4 uses only `asker_rival_exact.py` and
`asker_tenure.py`) and their shipped outputs predate a later
edit of the scripts, so re-running them does not reproduce those outputs; the
manuscript cites only `asker_rival_exact.py` and `asker_tenure.py`, whose outputs
re-run exactly.

### 03_validation

- `second_rater_kappa/` — the 200-question comparison between the second rater
  and the earlier classification, with both sets of per-item scores.
  `kappa_results.json`, written at the time, names the two raters
  (`sonnet-4.6 (primary)`, `opus-4.8 (independent, blind)`); it is the record on
  which the manuscript's attribution of the earlier classification to Claude
  Sonnet 4.6 rests (Section 4.2 of the manuscript).
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
  four questions with dates written into their text. `coder_followup_q5_excerpt.md`
  excerpts the two coders' own-words answer to the post-adjudication question on
  the 2-versus-3 boundary that Section 4.4 of the manuscript condenses as
  *information sufficiency*, with an English translation. `score_gold_v2.py`
  reproduces the reliability figures of Section 4.4 and `score_adjudication.py`
  the comparison of the adjudicated standard with the classifier; both run from
  this directory as shipped. The subfolders hold the questionnaire in both
  versions, the adjudication questionnaire with its blank record, and the blank
  post-adjudication forms. Coder-facing material is in Chinese.

### 04_crosssite_engine

`run_so_did.py`, `run_so_did_v2.py` (whose `--simulate` flag is the entry point
to the 25-check Monte Carlo harness) and `honest_did.py`.
`monte_carlo_harness_output/` holds the harness pass table and the output for
the real three-site design, which matches the figures reported in Section 5.1 of
the manuscript. `data/` holds the three sites used in the final design; four sites that
were fetched during exploration but did not enter it are kept separately under
`data/exploratory_not_in_final_3site_design/` rather than removed.

### 05_additional_checks

Cross-family relabelling, frontier-tier rescoring and the GLM answering runs.
The script that scanned the second round's answers for misalignment is not in
this package; the third round's scan, described in Section 4.6 of the
manuscript, is `08_criterion_round3/scripts/R2c_align_scan.py`. The one batch it corrected ships in
`03_validation/criterion_validity_rounds1_2/batches_haiku45/` in its original
(`answer_out_9_preswapfix.json`) and corrected (`answer_out_9.json`) form, with
the re-judgment (`judge_batch_swapfix.json`, `judgment_out_swapfix.json`). The
outputs of the discarded empty-completion GLM-4.6 answering run are not in this
package either. The blind batches for the four answering models live with the
criterion-validity tree in `03_validation` and are not duplicated here.
`s12_glm_month_sensitivity.py` reproduces, from `glm_relabel/labels_glm-4.6.jsonl`
and the python question labels in `01_panels_and_classification/data`, the
Section 4.6 sensitivity that drops 2022-06 (the one month for which the GLM-4.6
relabelling run returned no parseable score), moving the independent-family
dose-response estimate from −0.227 to −0.226; run it from this directory as
shipped.

### 06_sampling_window_test

The direct test of the within-month sampling window reported in Section 7.1
of the manuscript: the month-uniform draw, the blind batches and labels for both
designs, the analysis and sensitivity scripts with their result files, the
verbatim rating instruction (`PROMPT.md`), and a run log (`RUN_LOG.md`) giving
dates, model, instance count, and the sampling parameters that were not set.
That directory has its own README.

### 07_blind_reclassification

The re-classification of all 6,000 python questions by Claude Sonnet 5 under full
blinding (Section 4.2 of the manuscript).

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
  appends and the rollback. The hash file and the document refer to these two documents by their
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
- `session_access_audit/` — which files each blind rating session touched, exported
  from the working-session records (Section 4.3 of the manuscript):
  the fifty sessions of the blind classification and the twenty rating sessions of
  the sampling-window test. `session_access_summary.csv` has one row per session
  (whether it named a map file in any tool call, opened one with the file-reading
  tool, listed its input directory, or saw a map file name in any tool result);
  `session_file_paths.csv` lists every file path in every tool call, with local
  prefixes replaced by placeholders such as `<workdir>` and `<scratchpad>`; for
  command-line calls the `field` column gives the command's first word, not
  necessarily the verb that acted on the path. `session_access_counts.json` holds
  the totals and the positive control (the batch-building parent sessions, in which
  the same detector finds the map files). `export_session_access.py` produced all
  three from the session records, which are not in the package, reading only tool
  names and inputs, the file names in tool results, model identifiers and
  timestamps; `identification_rules_zh.md`, in Chinese, is the identification rule
  written before the first export, with its four amendments appended.
  The list covers tool calls only; what each session received at start-up,
  before any tool call, is described in Section 4.3 of the manuscript.
- `same_model_sonnet46/` — the blind re-run of the earlier classifier, Claude
  Sonnet 4.6, registered in the design document's thirteenth entry and carried out
  under its fifteenth (Section 4.2 and Table 4 of the manuscript). No estimate in the manuscript
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

The criterion-validity round the manuscript reports (Section 6.3).
`scripts/R2c_fetch_criterion.py` draws 80 questions per bin
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
313 questions all four completed (Section 4.6 of the manuscript). Four judging sessions,
one per answerer and all on the same forty questions, switched from Claude Opus 5.5
to Claude Opus 4.8 partway through (Section 4.6 of the manuscript). Their judgments, and a second
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
the package's own, except that `blind/data/` holds the two per-question label files
`question_labels.csv` (539,408 bytes) and `question_labels_ext_py.csv` (211,686
bytes), which the figure script reads and which had no copy elsewhere in the package); `results/paired_logs.md` sets the two logs side by side line
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
and the two robustness checks of Sections 4.6 and 7.1 of the manuscript
(`results/R2m_result.json`, `results/R2m_s19_excl05.json`).
`R2figbins.py` (in `scripts/`) fits the bin-dummy version of the Table 2 dose-response (s2, s3 and s4
each against s1, with the linear dose term replaced by three bin dummies) on four classifications of
the same 6,000 python questions: the blind one, the earlier one, the earlier classifier re-run blind and
GLM-4.6. It reads the four label files and the two stored `p1_14_bin_dummies.json` files inside the package, and writes
`results/R2figbins_result.json`. Before writing, it asserts as positive controls that the blind and
earlier bin-dummy coefficients equal those stored `p1_14_bin_dummies.json` values and that the four linear
coefficients equal Table 2 to three decimals. `make_figures_ipm.py` renders the manuscript's nineteen figure files (the sixteen in the
text plus `fig_estimators`, `fig3_robustness` and `fig_kappa`, the last three no longer in the text) from files inside this package: it
infers the package root from its own location and finds each input through a small
`resolve()` table (42 entries, mapping to 38 package files), and stops
with the file name if one is missing. Run `python 09_downstream_rerun/scripts/make_figures_ipm.py`;
it writes PNG and PDF files to `09_downstream_rerun/scripts/figures/` (set the environment
variable `P9B_FIG_OUT` to write elsewhere) and rewrites `10_shap_transparency/crosssite_selfcheck.json`
and `fig_forest_rows.csv`. Run from this package, it reproduces the submitted figures
file for file (all 19 PNG files and all 19 PDF files, byte-identical to the submitted ones). It was first generated from an
older figure script by `R2_make_fig_patch.py` and has since been edited by hand, and the
shipped file is the one that rendered the submitted figures. `s17_bound_both_samples.py` prints its sample-size headings from the data it
reads: the earlier-classification copy's log reports 5,640 and 5,930 questions,
and the blind copy's log reports 5,201 and 5,467 (Section 7.5 of the
manuscript), because bin s0 holds many more questions under the blind labels
than under the earlier classification (Section 4.2). These scripts
carry absolute paths from the machine they were written on, like the rest of the
package; `make_figures_ipm.py` is the exception described above.

### 10_shap_transparency

The surrogate-model analysis of Section 6.3 (Figure 12 of the manuscript). A LightGBM model
predicts the blind scores of the 6,000 python questions from 29 surface features, and tree
SHAP values decompose its five-fold out-of-fold predictions. The design note
(`步骤2_SHAP设计说明_20261004.md`, in Chinese) fixed the features, their expected signs, the
hyperparameters and the criteria before any model was fitted; its SHA-256 and recording time
are in `步骤2_SHAP设计说明_sha256.txt`, and `shap_surrogate.py` stops if the hash of the note
differs. `shap_result.json` holds every number the manuscript quotes from this analysis,
`shap_oof.npz` the values behind the figure, `shap_run.log` the run log. The directory also
holds `fig_forest_rows.csv` (the rows of Figure 6) and `crosssite_selfcheck.json` (the six
percentage changes of Section 5.1 recomputed before Figure 4 is drawn); Figure 4 reads the
monthly counts in `04_crosssite_engine/data/so_monthly_panel.csv`. The directory has its own
README.

---

## What a replicator should know before starting

**The model calls do not regenerate.** The runs with Claude models (both
classifications, same-family second rating, Claude answering and judging, the
diagnostic arm, the same-model blind run, and the sampling-window ratings) were done in model sessions, so their stored batch files carry only the per-item
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
sampling-window test and the verbatim dispatch log in `07_blind_reclassification/`.

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
That first round, at N = 88, is described in the manuscript as underpowered and was
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

---

## Exhibit map

Which package files and scripts stand behind each figure and table of the manuscript.
Figures were traced from the code of `09_downstream_rerun/scripts/make_figures_ipm.py`; tables were
traced from the manuscript's table text against the keypath record of the number audit and the
script descriptions above. Where a table row could not be traced to a file, the entry says
**存疑 (not traced)** rather than guessing. Paths are relative to the package root.

### Figures 1 to 16

All sixteen are drawn by `09_downstream_rerun/scripts/make_figures_ipm.py`, which writes
`<name>.png` and `<name>.pdf` to `09_downstream_rerun/scripts/figures/` (or to `P9B_FIG_OUT`). Figures
2, 3, 4, 6, 7, 10, 11, 12, 14, 15 and 16 have their own function (Figure 3 is `fig_protocol()`, a schematic that reads no data file); Figures 1, 5, 8, 9 and 13 are module-level blocks of the
script that end in `save(fig, "<name>")`. Inputs are found through `resolve()`; the table below gives the
package file each input resolves to.

| Fig. | Output file | Drawn by | Package files read |
|---|---|---|---|
| 1 | `fig0_framework` | module-level block "FIGURE (研究模型)" | none (schematic) |
| 2 | `fig_design` | `fig_design()` | none (schematic) |
| 3 | `fig_protocol` | `fig_protocol()` | none (schematic) |
| 4 | `fig_crosssite` | `fig_crosssite()` | `04_crosssite_engine/data/so_monthly_panel.csv`; writes `10_shap_transparency/crosssite_selfcheck.json` |
| 5 | `fig1_main` | module-level block "FIGURE 1 — absolute volume + composition" | `09_downstream_rerun/blind/outputs/02_estimation/absolute_volume_series_python.csv`; `07_blind_reclassification/labels/within_so_llm_panel_python_blind.csv` |
| 6 | `fig_forest` | `fig_forest()` | `07_blind_reclassification/results/R2_analyze_result.json`; `07_blind_reclassification/same_model_sonnet46/results/R2s46_analyze_result.json`; `09_downstream_rerun/blind/outputs/05_additional_checks/glm_relabel/cross_family_glm-4.6.json`; `09_downstream_rerun/orig/outputs/02_estimation/capability_ramp.json`; `09_downstream_rerun/blind/outputs/02_estimation/closure_check.json`, `review_r1/p0_2_staging_ground.json`, `asker_tenure.json`, `asker_rival_exact.json`; `09_downstream_rerun/blind/logs/check_cap_sensitivity.log`; writes `10_shap_transparency/fig_forest_rows.csv` |
| 7 | `fig_bins` | `fig_bins()` | `09_downstream_rerun/results/R2figbins_result.json` (produced by `09_downstream_rerun/scripts/R2figbins.py`) |
| 8 | `fig2_dynamics` | module-level block "FIGURE 2 (was 3) — dynamics + criterion validity" | `09_downstream_rerun/blind/outputs/within_so_llm_eventstudy.csv` (panel A); `08_criterion_round3/results/R2c_result.json` (panel B) |
| 9 | `fig_windows` | module-level block "新图 B：能力窗口" | `09_downstream_rerun/blind/outputs/02_estimation/capability_ramp.json`; `09_downstream_rerun/orig/outputs/02_estimation/capability_ramp.json` |
| 10 | `fig_agree` | `fig_agree()` | `03_validation/gold_standard/coding_sheet_A_v2.csv`; `03_validation/gold_standard/coding_sheet_B_v2.csv`; `07_blind_reclassification/labels/question_labels_python_blind.csv`; `01_panels_and_classification/data/question_labels_python_2021-2024.csv`; `05_additional_checks/glm_relabel/labels_glm-4.6.jsonl` |
| 11 | `fig_outside` (three panels) | `fig_outside()` | Panel A: `09_downstream_rerun/results/R2d_kappa_result.json`; Panel B: `09_downstream_rerun/blind/outputs/02_estimation/memorization_check.json` (human consensus, blind classification) and `09_downstream_rerun/orig/outputs/02_estimation/memorization_check.json` (earlier classification); Panel C: `09_downstream_rerun/results/R2d_extra_result.json` (blind arm, `closure_reasons`) |
| 12 | `fig_shap` | `fig_shap()` | `10_shap_transparency/shap_result.json`; `10_shap_transparency/shap_oof.npz` |
| 13 | `fig_volume` | module-level block "新图 D：绝对量降幅" | `09_downstream_rerun/blind/outputs/02_estimation/absolute_volume.json` |
| 14 | `fig_answer` | `fig_answer()` | `02_estimation/legB_first_answer.csv`; `09_downstream_rerun/blind/data/question_labels.csv`; `09_downstream_rerun/blind/data/question_labels_ext_py.csv`; `01_panels_and_classification/data/so_questions_python_2021-2024.json`; `01_panels_and_classification/data/so_questions_python_ext_2024-07_2026-05.json` |
| 15 | `fig_sampling` | `fig_sampling()` | `02_estimation/platform_monthly_totals.csv`; for each of python, javascript and java, `01_panels_and_classification/data/so_questions_<language>_2021-2024.json` and `so_questions_<language>_ext_2024-07_2026-05.json` |
| 16 | `fig_placebo` | `fig_placebo()`, which reuses the cutoff estimates computed by the block that draws `fig3_robustness` | `07_blind_reclassification/labels/within_so_llm_panel_python_blind.csv` (through that block; 存疑 whether the block reads any further file) |

Figures 1, 2 and 3 carry no data. The three further files the script renders, `fig_estimators`, `fig3_robustness` and `fig_kappa`, are not in the manuscript
(`fig_kappa` was the single-panel Figure 11 before it became Panel A of `fig_outside`).

### Tables 1 to 7

The estimation scripts are in `02_estimation/` and were run on both label sets by
`09_downstream_rerun/scripts/R2d_downstream.py`; their outputs are under
`09_downstream_rerun/blind/` (blind labels, used for python) and `09_downstream_rerun/orig/` (earlier
labels, used for javascript and java). The long names below are the files in `09_downstream_rerun/results/`,
`07_blind_reclassification/results/` and `08_criterion_round3/results/`.

- **Table 1** (the rubric in English). Text, not computed: `01_panels_and_classification/CLASSIFY_RUBRIC_EN_translation.md`
  is its source translation. The two quoted examples per level: 存疑 (not traced to a file).
- **Table 2** (dose-response). Python log-count OLS, FE-PPML and Newey-West rows:
  `07_blind_reclassification/results/R2_analyze_result.json` (keys `blind.ols`, `blind.ppml`, `blind.logratio_nw`), produced by
  `07_blind_reclassification/scripts/R2_analyze.py`. Earlier classifier re-run blind: `07_blind_reclassification/same_model_sonnet46/results/R2s46_analyze_result.json`
  (`R2s46_analyze.py`). GLM-4.6 row: `05_additional_checks/glm_relabel/cross_family_glm-4.6.json` (`05_additional_checks/cross_family_analysis.py`).
  Earlier-classification rows for python, javascript, java: `capability_ramp.json` under `09_downstream_rerun/orig/outputs/02_estimation/`
  (`02_estimation/capability_ramp.py`). The binary generative-versus-verification row and the s4-versus-s1 differential column:
  存疑 (not traced; the differential is computed from the stated formula in the table notes). Benjamini-Hochberg q values cited in Table 7:
  `02_estimation/bh_fdr_table1_family.py`.
- **Table 3** (capability windows). `capability_ramp.json` and `capability_ramp.log`, blind copy for python and earlier-label copy for
  javascript and java (`02_estimation/capability_ramp.py`). The equality tests quoted in the text below the table (`F` = 3.67 and the two
  contrasts): `09_downstream_rerun/results/R2d_extra_result.json`, key `blind.stats.window_tests` (`09_downstream_rerun/scripts/R2d_extra.py`).
- **Table 4** (rater validation). Classification-versus-classification rows: `09_downstream_rerun/results/R2_numbers_result.json`
  (`09_downstream_rerun/scripts/R2_collect_numbers.py`), `07_blind_reclassification/same_model_sonnet46/results/R2s46_numbers_result.json`,
  and `09_downstream_rerun/blind/logs/cross_family_analysis.log` for the GLM-4.6 rows. The 200-question Opus 4.8 row:
  `03_validation/second_rater_kappa/kappa_results.json`. Agreement with the human consensus: `09_downstream_rerun/results/R2d_gold_result.json`
  (`09_downstream_rerun/scripts/R2d_gold.py`; `03_validation/gold_standard/score_gold_v2.py`, `score_adjudication.py`); GLM-5.3 and the
  bootstrap intervals: 存疑 (not traced to one file; see `05_additional_checks/glm_relabel/gold_labels_glm-5.3.jsonl` and `R2d_kappa_result.json`).
  Date-visible minus blind block: `07_blind_reclassification/results/R2v_result.json` (`R2v_analyze.py`) for Sonnet 5 and
  `R2s46_numbers_result.json` for Sonnet 4.6.
- **Table 5** (criterion validity). Panels A to C: `08_criterion_round3/results/R2c_result.json` (`08_criterion_round3/scripts/R2c_analyze.py`,
  `R2c_labelsets.py`) and the criterion numbers gathered in `09_downstream_rerun/results/R2_numbers_result.json`. Which of the three panels
  each key feeds: 存疑 (not traced key by key).
- **Table 6** (absolute-volume reconstruction). `absolute_volume.json` and `absolute_volume.log` (blind copy for python, earlier-label copy
  for javascript and java; `02_estimation/absolute_volume.py`), together with `09_downstream_rerun/results/R2d_extra_result.json`.
  The volume-weighted s4-versus-s1 column: 存疑 (not traced to a key).
- **Table 7** (robustness by threat), by block:
  sampling window, `06_sampling_window_test/results/` (analysis scripts in `06_sampling_window_test/scripts/`);
  placebo cutoffs and bin-label permutation, `02_estimation/review_r1_reviewer_response_scripts/p0_3_placebo_overlap_summary.json` and
  `02_estimation/phaseA_composition.py` (the permutation row: 存疑);
  Benjamini-Hochberg, `02_estimation/bh_fdr_table1_family.py`;
  bin dummies, `p1_14_bin_dummies.json` (same directory, blind copy under `09_downstream_rerun/blind/outputs/02_estimation/`);
  bin dummies, other python classifications (earlier classifier re-run blind; GLM-4.6),
  `09_downstream_rerun/results/R2figbins_result.json` (keys `s46_rerun_blind` and `glm46`; produced by `09_downstream_rerun/scripts/R2figbins.py`);
  moderation and deletion, `closure_check.json` and `review_r1/p0_2_staging_ground.json`;
  asker composition, `asker_rival_exact.json` and `asker_tenure.json`;
  changes in question text, `review_r1/p1_12_ninety_day_window.json`, `bin_stability_test.json`, and `s17_bound_both_samples.py` output;
  the classifier's own properties, `memorization_check.json`, `edit_exposure_check.json`, `s17_length_conditioned.json`;
  the answer margin, `fixed_window_answer.py` and `answer_side_test.py` outputs (blind copies under
  `09_downstream_rerun/blind/outputs/02_estimation/` and `.../logs/`).
  Which individual row maps to which of these: 存疑 where the row is not named above.

### Protocol map

Section 4.7 of the manuscript names six validation steps (Figure 3) and the sections that report them. This map says which package files stand behind each step. It was built from the directory descriptions above and the exhibit entries in this section; where a file could not be traced to a step, the entry says **存疑 (not traced)** rather than guessing. Paths are relative to the package root.

- **1. Blind and audit the scorer** (Sections 4.2, 4.6). Blinding: the design document and its hash record, `07_blind_reclassification/design/`; the blinded batch construction and its blinding checks, `07_blind_reclassification/scripts/R2_build_blind.py` (with `blind_batches/`, `R2_collect.py`, `R2_analyze.py`, `results/R2_analyze_result.json`, `results/R2_build_result.json`); the date-visible diagnostic arm, `07_blind_reclassification/armB_date_visible/` (`scripts/R2v_build.py`, `scripts/R2v_analyze.py`, `results/R2v_result.json`); which files each blind rating session touched, `07_blind_reclassification/session_access_audit/`. Audit of silent run errors: the misfiling scan `08_criterion_round3/scripts/R2c_align_scan.py`; the model identifier logged for every step and the two robustness checks, `09_downstream_rerun/scripts/R2m_model_identity.py` (`09_downstream_rerun/results/R2m_result.json`, `R2m_s19_excl05.json`); the same check for the Sonnet 4.6 re-run, `07_blind_reclassification/same_model_sonnet46/scripts/R2s46_verify.py`. The coverage check named on the card of Figure 3: 存疑 (not traced).
- **2. Replicate across raters** (Sections 4.5, 6.1). The 200-question second rater, `03_validation/second_rater_kappa/` (`kappa_results.json`); the independent-family relabelling, `05_additional_checks/cross_family_analysis.py` with `05_additional_checks/glm_relabel/` (`labels_glm-4.6.jsonl`, `cross_family_glm-4.6.json`); the blind re-run of the earlier classifier, `07_blind_reclassification/same_model_sonnet46/` (`results/R2s46_analyze_result.json`). Results appear in Table 2 and Table 4 and in Figures 6, 7 and 10 (source files in the exhibit entries above). Which of these files belongs to Section 4.5 and which to Section 6.1: 存疑 (not traced).
- **3. Test a behavioural criterion** (Section 6.3). `08_criterion_round3/` as a whole: sample draw `scripts/R2c_fetch_criterion.py`, answering `scripts/R2c_split_and_glm.py`, judging batches `scripts/R2c_build_judge.py`, analysis `scripts/R2c_analyze.py` and `scripts/R2c_labelsets.py`, results `results/R2c_result.json` and `results/R2c_labelsets_result.json`. Reported in Table 5 and Figure 8 (Panel B). The first two rounds, `03_validation/criterion_validity_rounds1_2/`, are superseded and not what the manuscript reports.
- **4. Explain what the score follows** (Section 6.3). `10_shap_transparency/` (`shap_surrogate.py`, `shap_result.json`, `shap_oof.npz`, `shap_run.log`, and the design note with its hash). Reported in Figure 12.
- **5. Step outside the model loop** (Sections 4.4, 6.4). The two human coders and the adjudication, `03_validation/gold_standard/` (`coding_sheet_A_v2.csv`, `coding_sheet_B_v2.csv`, `裁决记录表.csv`, `score_gold_v2.py`, `score_adjudication.py`); agreement with the human consensus, `09_downstream_rerun/results/R2d_gold_result.json` (`09_downstream_rerun/scripts/R2d_gold.py`) and `09_downstream_rerun/results/R2d_kappa_result.json`. Moderators' duplicate closures: `02_estimation/closure_check.py` (output `closure_check.json`, blind copy under `09_downstream_rerun/blind/outputs/02_estimation/`) and, for Figure 11 Panel C, `09_downstream_rerun/results/R2d_extra_result.json` (`closure_reasons`). Reported in Figures 10 and 11 and in Table 4. Which of Sections 4.4 and 6.4 each file feeds: 存疑 (not traced).
- **6. Stress-test over time** (Sections 7.5, 7.6). The classifier's own properties (Section 7.6): `02_estimation/memorization_check.py`, `edit_exposure_check.py` and `s17_length_conditioned.py` with their `.json` outputs (blind copies under `09_downstream_rerun/blind/outputs/02_estimation/`). Changes in question text (Section 7.5): `02_estimation/review_r1_reviewer_response_scripts/p1_12_ninety_day_window.py`, `02_estimation/bin_stability_test.py`, `02_estimation/s17_bound_both_samples.py`. The relabelling element named on the card of Figure 3: 存疑 (not traced). Reported in Table 7.

Two things are not a step of the protocol as Section 4.7 lists them: the sampling-window test (`06_sampling_window_test/`, Section 7.1) and the cross-site design (`04_crosssite_engine/`, Section 5.1). Elements fixed in writing beforehand, per Section 4.7: the blind-classification protocol, `07_blind_reclassification/design/`; the surrogate model's expected feature signs, the design note in `10_shap_transparency/`; the post-adjudication analysis plan (Section 4.4): 存疑 (not traced).
