# Audit trail

This file accompanies the manuscript and the replication package's README. It
holds the process record that the manuscript states in compressed form: how and
when each model run was made, what the session runs received before they started,
how the scripts were written, how the human-coded standard was built, and what
happened in the two criterion rounds that preceded the reported one, and how
the pipeline failures were handled. Every fact
recorded here is also stated, in shorter form, in the section of the manuscript
named under each heading; this file adds the detail, not new facts.

```
1  Run dates and provenance of the model runs        manuscript Section 4.3
2  Start-up content of the session runs              manuscript Section 4.3
3  How the scripts were written                      manuscript Section 4.3
4  The human-coded standard: coding history          manuscript Section 4.4
5  The two earlier criterion rounds                  manuscript Section 4.6
6  The sampling-window test: what the designer knew  manuscript Section 7.1
7  Pipeline failures and their handling              manuscript Section 4.6
8  The October 2026 rounds                           manuscript Section 7.1
```

---

## 1. Run dates and provenance of the model runs

Runs span June 2026 (the earlier classification and the same-family second
rating) to 22–25 September 2026 (the sampling-window ratings, the blind runs and
the third criterion round).

The Claude runs were done in model sessions, not by scripts calling an endpoint,
so they carry no call-level timestamp, version string or sampling parameter.
Their provenance is the run date, the model named and, for the sampling-window
test and both blind python runs, the verbatim instruction, the blinded batch
files and the design document.

The model behind every step of the 22–25 September sessions was checked against
their session logs (manuscript Section 4.6). The June runs left no session log
that could be found, so their models are those named in the agreement results
written at the time (`03_validation/second_rater_kappa/kappa_results.json`).

The GLM runs were scripted endpoint calls at temperature 0 or 0.2
(`05_additional_checks/`).

## 2. Start-up content of the session runs

At start-up, before any tool call, each session run of 22–25 September received
the operator's standing instructions and an index of the operator's project
notes that recorded some results. Which version of the index each group of
sessions received:

- The blind classification, its diagnostic arm, the Claude answerers and judges,
  and the blind re-run of the earlier classifier received a version that gave the
  first and third sampling-window results (+0.199 and −0.002; manuscript
  Section 7.1).
- The sampling-window rating sessions received a version that did not give them.
- Nine of the eleven sessions judging the GLM-5.3 answerer received the only
  version that gave any value of *γ*: −0.42 and −0.30, the headline on both
  classifications. Judges never see a label.

No version stated a hypothesis about which questions should change or any
question's date.

The file-access lists (`07_blind_reclassification/session_access_audit/`) cover
tool calls only. In them, no blind-classification or sampling-window rating
session opened the token map, the month map or the raw draw, though fifteen of
the twenty rating sessions listed a directory showing the draw's token-map and
raw-draw file names. What a session received at start-up is not visible in those
lists and is recorded only here and in the manuscript.

The index itself is not in the replication package.

## 3. How the scripts were written

The fetch, estimation, validation and checking scripts were written with Claude
Code (Anthropic), an AI coding assistant, at the author's direction, running
Claude models of the Opus, Sonnet and Fable families. Which version wrote which
script was not recorded. Some robustness checks were designed or reviewed by a
separate model instance (see the README, "Two model names appear in this
package"). The reported numbers are computed by those scripts from the stored
artifacts and can be re-run without the assistant.

## 4. The human-coded standard: coding history

**The withdrawn questionnaire.** An earlier coding questionnaire omitted,
through an oversight, the per-bin anchor examples that the classifier's rubric
carries. It was withdrawn after a first round of poor agreement, and none of its
labels enters any analysis. The standard was coded afresh on a rebuilt
questionnaire with the anchors verbatim (`03_validation/gold_standard/`, both
questionnaire versions).

**The staged check.** The first fifty questions of the shuffled sequence served
as a check on scale use and agreement before coding continued. Only coder A's
were checked in this way, since coder B returned all 300 at once. Because coder A
continued beyond the first fifty only after passing that check, those fifty carry
a mild upward selection; without them binary *κ* is 0.520 and weighted *κ*
0.615 (against 0.533 and 0.609 on all 300).

**The adjudication.** The seventy questions on which the two coders fell on
opposite sides of the generative-verification split, 35 in each direction, were
adjudicated in a single joint session without model labels. All seventy reached
consensus; 48 resolved toward one coder's position and 22 toward the other's,
which departs from an even split at binomial *p* = .0025. The manuscript reports
this imbalance without interpreting it (Section 8.3 notes that a noisier standard
would produce the same pattern). The analysis plan for the post-adjudication
comparison was archived before the adjudication data were collected.

## 5. The two earlier criterion rounds

The criterion test reported in manuscript Section 6.3 is the third round
(`08_criterion_round3/`). The first two are in
`03_validation/criterion_validity_rounds1_2/`.

- **Round 1** (*N* = 88) was underpowered and used an answer-existence filter
  that selected an unrepresentatively well-answered s1 stratum.
- **Round 2** (*N* = 320) reported a steeper gradient and a flatter slope at the
  weaker tier, but its sample was not the stratified random draw it was described
  as: the fetching API call returned 30 items per request by default, ordered by
  activity, so 316 of its 320 questions were post-event, and it was stratified on
  the earlier, date-visible labels.

No reported number rests on either round.

## 6. The sampling-window test: what the designer knew

This record stays in full in manuscript Section 7.1 and is listed here only so
that the audit trail is complete: the test's designer knew the predicted
direction, so both designs were scored by separate model instances; a first
comparison, prespecified against the earlier classification's archived labels
with three criteria, changed rater and sampling rule together, drifted by +0.199
across the event and failed two of its three criteria. The run files are in
`06_sampling_window_test/`.

## 7. Pipeline failures and their handling

Manuscript Section 4.6 lists these in brief. A token-overlap scan found one
Haiku 4.5 answer filed under another question; it was re-answered and
re-judged, and the displaced question and one skipped question were answered
separately. GLM-5.3 returned nothing for 7 of 320 questions after at least four
attempts each. Four judging sessions, one per answerer and all on the same forty
questions, switched from Claude Opus 5.5 to Claude Opus 4.8 when the newer
model's safety filter stopped on one question, a debugging request about a
credential-guessing script; the other thirty-nine were re-judged with Opus 5.5,
that question's four judgments remain Opus 4.8's, and dropping it moves none of
the per-answerer rank correlations or the pooled slope of the criterion test by
more than 0.005. Two judging sessions consulted the web, each on one item, and
one sampling-window rating session also switched model.

## 8. The October 2026 rounds

Files: `11_random_redraw/`, which has its own README. This section records dates and what each run was; the
statements in the manuscript's Section 7.1 are the ones that carry the findings.

**Instruction and batch files.** The verbatim instruction given to each of the 100 rating sessions is
`11_random_redraw/r1_random_redraw_20261012/subagent_run/full12k/prompt_batch_001.txt` to `..._100.txt`; the batch files are
`11_random_redraw/R3_blind/set12k/blind_batch_001.json` to `..._100.json`; the labels as returned are `labels_batch_001.json` to `..._100.json` in the same directory.
The trial rating's instruction and batches are `subagent_run/prompt_batch_01.txt` to `..._04.txt` and `R3_blind/sa400/blind_batch_01.json` to `..._04.json`.

**Dates** (file modification times are the machine's local time; session times are UTC from the session records).
- 12 October, 18:46: the listing and retrieval pipeline run on two months (2022-09, 2024-06).
- 12 October, 11:11-11:23Z and 13:00-13:05Z: the trial rating of 400 questions, two rounds of four sessions each,
  effort `high` and then `xhigh`, model `claude-sonnet-5` in every assistant record (52 and 53 records;
  `subagent_run/sa_verify_models.log`, `subagent_run/sa2_verify.log`). The start-up content and tool calls of these
  eight sessions were not audited. The trial is not reported in the manuscript.
- 13 October, 07:56-07:58: the 60-month listing, the two draw runs (identical file hashes) and the question-text retrieval, by the
  modification times of their logs. 08:13: batch, prompt and manifest files written.
- 12 October 23:16Z to 13 October 00:06Z: the 100 rating sessions of the 12,000 questions, one per batch of 120. Model
  `claude-sonnet-5` and effort `xhigh` in all 1,307 assistant records (`subagent_run/full12k/all100_verify.log`). The same check run with
  a wrong expected effort (`high`) on batches 1 to 25 fails (`wave1_verify_negctl.log`).
- 13 October: the label files were committed (commit 19bb4b2e, 09:15:48 +0900); the analysis script was written at 09:21:22 and its log
  at 09:24:36 (file modification times).

**Start-up content of the 100 sessions** (`analysis_full12k/recompute/audit_sessions.md`). Every session started in a working directory whose name contains the Chinese words for "random redraw";
the working-tree listing injected at start-up named `draw/`, `draw_all.csv` and `bodies/` in all 100 sessions; `rate_private\` and `panel_map` did not appear in the start-up content. Of 788 tool calls, none had an input naming those paths; in 14 sessions a tool result contained the directory
name inside a log-file path written by a hook.

The start-up working-tree listing also named four earlier label files, those of the 12 October trial rating, listed at the time as
`R3_blind/sa400/labels_batch_01.json` to `labels_batch_04.json`. The listing itself is not in the package (raw session transcripts
are withheld); the four names are taken from the operator's record of the start-up context. The four files are the round-2 (`xhigh`)
label files of the trial rating, held in this package under the names below (the original files and the package copies are byte-identical):

| Name at start-up | Name in this package (`11_random_redraw/R3_blind/sa400/`) | sha256 |
|---|---|---|
| `labels_batch_01.json` | `labels_batch_01_round2_xhigh.json` | `9f8249ca914d089e1f6c3062060cbc4eb6b46a91df93cc13479cf24e36c30e50` |
| `labels_batch_02.json` | `labels_batch_02_round2_xhigh.json` | `ca2e69be53c35a5ac14da8abb8815f11318d53d0dd04289f1ea8175ca7735ca3` |
| `labels_batch_03.json` | `labels_batch_03_round2_xhigh.json` | `586cbc2a747d28f882fba6e3d0b0a462b80e8fcecd79b00aa2927a50aea82a67` |
| `labels_batch_04.json` | `labels_batch_04_round2_xhigh.json` | `fb6be44c50472b34d7c41711d7f17dd5f250f4288d80f1a4380aa4c696f177fa` |

No tool call of the 100 sessions named them: `audit_sessions_paths.csv` has 0 rows containing `sa400`, against 133 rows containing
`labels_batch` (the positive control).

**Scripts.** The sampling, preparation and checking scripts are shipped as run. The two analysis scripts were
changed for this package (the panel mapping is withheld) and re-run in the package; the changes and the re-run
results are in `11_random_redraw/README.md`. The API rating stages of `r1_rate_api.py` were not run.

**Derived tables.** The mapping from rater identifiers to panel, question and month is not in the package. The per-question tables in `11_random_redraw/derived/`
were made on 13 October after the label files had been returned and committed; the README of that directory states what they disclose.

**Not included.** The API key file, raw session transcripts, internal working notes, checkpoint files of the listing, and the numbering
tables and batches of an API rating route that was prepared and not run.
