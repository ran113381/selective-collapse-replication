# 10_shap_transparency

The surrogate-model (SHAP) analysis of Section 6.3 (Figure 12) and the data behind two
figures that read results from elsewhere in the package.

| File | What it is |
|---|---|
| `步骤2_SHAP设计说明_20261004.md` | The design note, in its original Chinese, written before any feature, model or SHAP value existed: the 29 features and their regular expressions, the expected sign of each directional feature, the hyperparameters, the folds, the three criteria and the pre- and post-event comparison. |
| `步骤2_SHAP设计说明_sha256.txt` | Its SHA-256 (`d37dc8f8...6562`) with the time it was recorded (2026-10-04 19:36:14 +0900), before the analysis directory existed. `shap_surrogate.py` recomputes the hash of the design note at the start of a run and stops if it differs; `shap_run.log` shows the match. |
| `shap_surrogate.py` | The analysis: LightGBM gradient-boosted trees on the 29 surface features of the 6,000 python questions, five-fold out-of-fold predictions of the blind scores, tree SHAP values, the three criteria (AUC, attribution share of the rubric properties, direction agreement), the drop-the-two-length-features rerun, and the pre- versus post-event ranking comparison. It runs twice and compares the hashes of the out-of-fold predictions and SHAP values. |
| `shap_result.json` | Every number the manuscript quotes from this analysis, with its key path (`C1`, `C2`, `C3`, `group_share`, `per_feature`, `R1`, `S1`). |
| `shap_oof.npz` | The out-of-fold predictions, feature matrix, SHAP values and feature names behind Figure 12. |
| `shap_run.log` | The run log: design-note hash match, the self-checks, the two-pass hash comparison and the criteria values. |
| `fig_forest_rows.csv` | The 19 rows of Figure 6 (estimate, standard error, estimator, and the result file and key each came from). |
| `crosssite_selfcheck.json` | The six percentage changes printed in Section 5.1, recomputed from the cross-site panel before Figure 4 is drawn. |

**Inputs.** `shap_surrogate.py` reads the blind batches, labels and token map that sit in
`07_blind_reclassification/` (it names them under a working-directory folder `R2_blind`) and
the blind labels' per-question CSV; the paths at the top of the script are absolute paths
from the machine it was written on, as elsewhere in the package. Adjust them before running.

**Figure 4 (cross-site).** The function `fig_crosssite()` in `09_downstream_rerun/scripts/make_figures_ipm.py`
reads the monthly question counts of the seven sites in
`04_crosssite_engine/data/so_monthly_panel.csv`; that file is not copied here.
`crosssite_selfcheck.json` records that the six percentage changes recomputed from it equal the
six printed in Section 5.1.

**Which function reads which file.** All in `09_downstream_rerun/scripts/make_figures_ipm.py`, which
finds every input through its `resolve()` table.
`fig_crosssite()` (Figure 4) reads `04_crosssite_engine/data/so_monthly_panel.csv` and writes
`crosssite_selfcheck.json`. `fig_shap()` (Figure 12) reads `shap_result.json` and `shap_oof.npz`.
`fig_forest()` (Figure 6) reads `07_blind_reclassification/results/R2_analyze_result.json`,
`07_blind_reclassification/same_model_sonnet46/results/R2s46_analyze_result.json`,
`09_downstream_rerun/blind/outputs/` (`02_estimation/closure_check.json`,
`02_estimation/review_r1/p0_2_staging_ground.json`, `02_estimation/asker_tenure.json`,
`02_estimation/asker_rival_exact.json`, `05_additional_checks/glm_relabel/cross_family_glm-4.6.json`),
`09_downstream_rerun/blind/logs/check_cap_sensitivity.log` and `09_downstream_rerun/orig/outputs/02_estimation/capability_ramp.json`,
and writes `fig_forest_rows.csv`. `fig_design()` and `fig_placebo()` read no file of their own
beyond the inputs loaded at the top of the script.
