# 11_random_redraw

The random redraw and same-panel re-rating of manuscript Section 7.1 (12-13 October 2026):
the month-uniform draw (seed 20261012), the 12,000 blinded questions, the instruction
and batch files, the labels as returned, the session checks, and the analysis. A trial
rating of 400 questions made on 12 October is included as well and is described below
(it is not reported in the manuscript).

The directory layout mirrors the working tree in which the scripts were run, so that
`r1_random_redraw_20261012/` and `R3_blind/` are siblings, as the scripts expect.
Scripts that were run only for the record (sampling, preparation, session checks) are
shipped as run, unchanged; their paths refer to the original working tree, and the
files they read from withheld locations (below) are not in the package. The two analysis scripts
were changed in this copy and re-run here (section "Changes to the two analysis scripts").

```
derived/                              labels joined to the withheld panel mapping, one row per
                                      question (see "Derived tables"); the derivation script and its logs
R3_blind/set12k/                      blind_batch_001-100.json (what the raters received) and
                                      labels_batch_001-100.json (what they returned, as returned)
R3_blind/sa400/                       trial rating, 4 batches of 100: blind_batch_01-04.json and the labels
                                      of both rounds (labels_batch_NN_round1_high.json, ..._round2_xhigh.json)
r1_random_redraw_20261012/
  r1_common.py r1_enumerate.py r1_draw.py r1_fetch_bodies.py run_enum_loop.sh
                                      population listing, draw, body retrieval (Stack Exchange API)
  population/ (60)                    pop_YYYY-MM.json: all python questions of each month
  draw/ (60 + draw_log.json)          draw_YYYY-MM.json: the 100 questions drawn per month
  draw_all.csv                        the 6,000 drawn questions (ym, question_id, creation_date)
  bodies/ (60 + bodies_log.json)      question text retrieved for the draw
  draw_bak_2months/bodies_log_2months.json
                                      retrieval log of two months run first as a trial of the pipeline
  enum_run_*.log draw_run*_full60.log draw_sha_run*.txt bodies_run_full60.log
  r1_full60_summary.py, r1_full60_summary_full60.log, full60_summary.csv
                                      logs of the listing, the two draw runs (identical file hashes)
                                      and the retrieval, and the per-month summary
  r1_rate_api.py                      imported by prep_full12k.py; its API rating stages were never run
  subagent_run/full12k/               prompt_batch_001-100.txt (the verbatim instruction, one per batch),
                                      prep_full12k.py/.log, manifest_full12k.txt (file hashes),
                                      wave_verify.py and wave1-5_verify.log, wave1_verify_negctl.log,
                                      all100_verify.log (model and effort of every session)
  subagent_run/prompt_batch_01-04.txt trial rating instruction
  subagent_run/sa_verify_models.log, sa2_verify.py/.log, r1_verify_models.py
                                      model/effort checks of the trial sessions (round 1, round 2)
  analysis_full12k/                   analyze_full12k.py and log, result_full12k.json, bootstrap_draws.csv,
                                      consistency_by_month.csv, gen_share_by_month.csv;
                                      windows/ (windows.py, log, table, event-study paths, placebo candidates, gate);
                                      recompute/audit_sessions.* (start-up content and tool calls of the 100 sessions)
```

## What was run

- Draw: for each of the 60 months 2021-06 to 2026-05, 100 python questions drawn without
  replacement and uniformly from the month's full listing (`random.Random('<seed>-<ym>')`, seed 20261012).
  Two full draw runs gave identical file hashes (`draw_sha_run1.txt`, `draw_sha_run2.txt`).
- Rating: 12,000 questions (the python panel's 6,000 questions plus the 6,000 newly drawn,
  100 of each per month) were mixed and cut into 100 batches of 120. Each batch was rated by one
  model session with the instruction in `prompt_batch_NNN.txt`, made from the rating instruction of the earlier blind run
  by substituting paths and the identifier format (the restoration check is in `prep_full12k.log`). Model and effort of the 100
  sessions: `claude-sonnet-5`, `xhigh` on all 1,307 assistant records
  (`subagent_run/full12k/all100_verify.log`; `analysis_full12k/recompute/audit_sessions.md`).
  Session records ran from 2026-10-12T23:16Z to 2026-10-13T00:06Z.
- Start-up content: `analysis_full12k/recompute/audit_sessions.md` lists what each session received
  before it started and every tool call it made. In all 100 sessions the working directory name (which
  contains the Chinese words for "random redraw") and the working-tree listing at start-up named
  `draw/`, `draw_all.csv` and `bodies/`; neither `rate_private\` nor `panel_map` appeared in the start-up content.
  The 788 tool calls had 0 inputs naming any of those paths; tool results contained the directory name in 14 sessions,
  in log-file paths written by a hook, and nothing else from that list.
- Trial rating (not reported in the manuscript): 400 questions (200 from the python panel,
  200 from the two-month trial draw; months 2022-09 and 2024-06), 4 batches, rated twice by `claude-sonnet-5`: round 1 on 2026-10-12
  11:11-11:23Z with effort `high` (52 assistant records), round 2 on 2026-10-12 13:00-13:05Z with
  effort `xhigh` (53 assistant records). The start-up content and tool calls of the trial sessions were not audited.
  In round 2 the exact-score agreement with round 1 was 255 of 400 (`derived/derive_trial400.log`).

## Withheld files and why

- The panel mappings (`panel_map_full12k.json`, `panel_map_trial400.json`; rater identifier to panel, question id, month, batch and position) stay in the private
  directory in which they were made.
- `r1_token_map.json`, `r1_ym_map.json` and the batch files of an API rating route that was prepared and never run.
- The Stack Exchange API key file; raw session transcripts (they contain the operator's start-up context and the
  batch text); internal working notes and run records; the per-month checkpoint files of the listing; backups of the two-month trial.
- Path text `C:\Users\<user>` replaces the operator's user name in `sa2_verify.log` and
  `audit_sessions.log/.md`; no other change was made to any shipped file.

## Derived tables

`derived/labels_by_question_full12k.csv` (12,000 rows) joins the labels to the withheld mapping:
columns `panel` (`panel` = the python panel's 6,000 questions as re-rated, `redraw` = the 6,000 newly drawn questions),
`question_id`, `ym`, `score`, `label`. Rows are sorted by panel, month, question id. It carries no rater identifier,
batch number or position within batch. 326 question ids occur in both panels; the key is (panel, question_id).
`derived/labels_by_question_trial400.csv` (400 rows) does the same for the trial, with the scores of both rounds.
`derived/derive_labels_by_question.py` is the derivation; it needs the withheld mapping and cannot be run from the package.

Whether the tables can unblind a rater: each row states which panel a question belongs to and the score it
received. For a rater who has not yet rated, that is disclosure of panel membership; for the ratings reported
here it is not, because the tables were made after all 100 label files had been returned, and the label files
had been committed (commit 19bb4b2e, 2026-10-13 09:15:48 +0900) before the analysis script was written
(09:21:22) and run. The tables do not alter any label. Any later blind rating of these questions needs new
identifiers, a new mixing, and a start-up directory that does not carry the redraw's name. The package also holds
the blind batches, `draw_all.csv` and `bodies/`; together these allow most identifier-to-question correspondences to be
recovered by text comparison (not those of the 326 shared question ids, whose panel cannot be recovered that way),
as the decoding tables of `06_sampling_window_test/` and `07_blind_reclassification/` already do for the September runs.

## Changes to the two analysis scripts

Both scripts were changed in this copy only; the working-tree originals are unchanged.

`analysis_full12k/analyze_full12k.py` (original sha12 c4bf2d7db6c1; this copy 87e222d0c7c9): reads
`derived/labels_by_question_full12k.csv` instead of the withheld mapping; paths are relative to the package root
(published labels now from `07_blind_reclassification/labels/`); gate 2 now checks the 100 label files against their
blind batches and the derived table against the label files' score distribution. The estimators, gate 3, the
bootstrap and the outputs are unchanged. Re-run here: gate 3 passes; the log `analyze_full12k.log`
differs from the original run (`analyze_full12k.original_run.log`) only in the script/table hash lines and the gate-2 text;
`bootstrap_draws.csv`, `consistency_by_month.csv`, `gen_share_by_month.csv` are byte-identical to the original outputs.
`result_full12k.json` differs from the original (sha12 56f2e3f3e199; this copy c9a5c14217a1) in the 9th to 10th decimal
of the three PPML coefficients, the three PPML standard errors and the C-B PPML point difference (largest absolute difference 1.6e-10); no four-decimal figure differs.

`analysis_full12k/windows/windows.py` (original sha12 bf7b26f0ee94; this copy 64af72456c8e): the assertion on the manuscript's hash was
removed, paths made relative, and the B-C intervals from resampling months inside each window were removed; the B-C
column now holds the point difference. Estimators and the ten gate checks are unchanged and all pass. The C-column
values of the two rows for the first window and the first six months are identical to the original run
(-0.087 (0.051) p=0.0885 and -0.176 (0.070) p=0.0114). The original `windows.log` and `windows_table.md` are not shipped
because they carry the removed intervals.
