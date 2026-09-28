# review_r1_reviewer_response_scripts

Scripts written during a round of pre-submission review of the manuscript, with their
archived outputs. Each script first reproduces the published values of the quantity
it re-examines and stops, printing `!!`, if it cannot; only then does it compute
anything new. The scripts carry absolute paths from the machine they were written on;
adjust the path constants before running.

## Running

```bash
python p0_2_staging_ground.py         # Staging Ground split, recomputed at the official date
python p0_3_placebo_overlap.py        # placebo-cutoff windows and their overlap with the treated period
python p0_6_pretrends.py              # event-study rebuild and joint pre-period test
python p0_6_ref_sensitivity.py        # sensitivity of that test to the reference month
python p1_14_bin_dummies.py           # bin dummies in place of the linear score
python p2_coder_exact_agreement.py    # exact five-bin agreement between the two coders over all 300 questions (reproduces kappa 0.533 / 76.7%)
```

---

## p0_2_staging_ground.py: the Staging Ground split

Staging Ground opened to all new askers on 4 June 2024. An earlier split placed the
break at July 2024; this script recomputes it at June 2024.

Pipeline check: both the pre-/post-ChatGPT closure-rate columns and the columns at
the earlier July 2024 split reproduce the percentages published for them, so the
rebuild is correct rather than coincidentally aligned.

| | Closure rate %, s1/s2/s3/s4 | Gradient before / after |
|---|---|---|
| Earlier split, 2024-07 | before 3.3/4.6/5.0/13.4; after 6.3/5.9/9.4/17.3 | −0.350 (.081) / −0.470 (.074) |
| Corrected split, 2024-06 | before 3.24/4.68/4.15/13.49; after 6.21/5.76/9.87/17.08 | −0.341 (.082) / −0.472 (.073) |

The gradient conclusion is unchanged. The s3 closure rate before the split moves most
(4.99% to 4.15%) because questions are reassigned between the two periods; the bin
total is conserved (1,406 = 1,406).

## p0_3_placebo_overlap.py: placebo windows and the treated period

| Window | Candidates | Before the event | Window entirely before treatment | Rank of the true event |
|---|---|---|---|---|
| ±9 months (used in the manuscript) | 43 | 9 | 1 (2022-03 only) | 2 of 43 (4.7th percentile) |
| ±12 months | 37 | 6 | 0 | 2 of 37 (5.4th percentile) |

Per-candidate windows and overlap counts are in `placebo_overlap_w9.csv` and
`placebo_overlap_w12.csv`. The overlap pulls the contaminated candidates toward the
true estimate, which makes the comparison conservative.

## p0_6_pretrends.py and p0_6_ref_sensitivity.py: the pre-period test

Pipeline check: the monthly event-study coefficients reproduce
`within_so_llm_eventstudy.csv` for all 59 months (maximum difference 1.5 × 10⁻¹⁴).
Month-clustered standard errors for single-month coefficients are degenerate (the
first five come out as 0/0/0/0/NaN), which is why Figure 5A reports the event-study
path as point estimates only.

First pass: splitting the pre-period into three windows of five to six months and
testing their dose slopes jointly, with the windowed specification the manuscript
applies to the post period, gives W = 48.38, df = 3, p = 1.8 × 10⁻¹⁰; the three
window slopes are −0.335 (.098), −0.343 (.114) and −0.366 (.070).

Second pass: all three windows are measured against the single reference month
2022-11, whose mean score is 2.980 against 2.723 (SD 0.133) for the neighbouring six
months, z = 1.93. The same test against references that do not rest on that month:

| Reference | W | df | p |
|---|---|---|---|
| Single month 2022-11 | 48.38 | 3 | 1.8 × 10⁻¹⁰ |
| Three-month mean, 2022-09 to 2022-11 | 1.11 | 3 | 0.775 |
| Six-month mean, 2022-06 to 2022-11 | 0.09 | 2 | 0.958 |
| Windows against each other (no reference) | 0.09 | 2 | 0.958 |

Only the single-month reference finds a pre-period gradient, and the manuscript
reports none (Section 6.2 of the manuscript).

## p1_14_bin_dummies.py: the linear score against bin dummies

Specification: `lc ~ sum over b in {2,3,4} of 1[bin=b] x post + C(bin) + C(ym)`,
month-clustered, s1 as reference; otherwise identical to the main specification. The
continuous gamma is reproduced first in each language.

| Language | Continuous gamma | delta_s2 | delta_s3 | delta_s4 | Linearity chi2(2) | p |
|---|---|---|---|---|---|---|
| python | −0.4156 | −0.258 (p = .16) | −0.630 (p < .001) | −1.261 (p < .001) | 3.675 | 0.159 |
| javascript | −0.2288 | −0.311 (p = .27) | −0.641 (p = .006) | −0.653 (p = .004) | 3.879 | 0.144 |
| java | −0.1233 | −0.170 (p = .25) | −0.288 (p = .024) | −0.372 (p = .034) | 0.113 | 0.945 |

Linearity (delta_3 = 2 delta_2 and delta_4 = 3 delta_2) is not rejected in any
language. With 240 observations in 60 monthly clusters the test has limited power, so
linearity is not rejected rather than confirmed. The headline magnitude does not
depend on it: the saturated s4-versus-s1 contrast in python is −71.7%, against
−71.3% from exp(3 gamma) − 1. In javascript s3 and s4 nearly coincide (−0.641 /
−0.653); in python the steps grow from s2 to s4. Both are within noise and are
descriptive only.

---

## Files

```
README.md                           this file
p0_2_staging_ground.py / .json      Staging Ground split at the official date, with pipeline check
p0_3_placebo_overlap.py / .json     placebo windows (+-9, +-12 months) and their overlap
placebo_overlap_w9.csv / _w12.csv   per-candidate detail
p0_6_pretrends.py / .json           event-study rebuild, three pre-period windows, first-pass joint test
p0_6_ref_sensitivity.py / .json     reference-month sensitivity of that test
p1_14_bin_dummies.py / .json        bin dummies and the linearity test
p2_coder_exact_agreement.py / .json exact five-bin agreement between the two coders over all 300
                                    questions; written after a check found that a 44% exact-agreement
                                    figure described the first 50 questions rather than all 300
check_detrend_ci.py                 interval for an earlier linear-detrending column (superseded by the
                                    p0_6 scripts; kept for comparison)
check_cap_sensitivity.py            truncation sensitivity (still valid: excluding questions at the cap
                                    leaves gamma almost unchanged)
check_pooled_logit.py               question-clustered SE for the pooled four-answerer logit (still valid)
_superseded_by_p0_2.py              exploratory version of the Staging Ground split
_superseded_by_p0_3.py              exploratory version of the placebo-overlap check
```
