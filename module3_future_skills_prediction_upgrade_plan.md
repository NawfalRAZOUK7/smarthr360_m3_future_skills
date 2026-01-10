# Module 3 - Advanced Professional Upgrade Plan (Future Skills Prediction)

## 1) Scope and guardrails (keep Module 3 clean)
- [x] Confirm the sole objective is Future Skills Need (foresight).
- [x] Exclude attrition/salary/performance predictions from Module 3.
- [x] Upgrade via formulation + governance + data lifecycle, not extra targets.
- [x] Keep Module 3 aligned with: market trends -> emerging skills by sector -> internal alignment -> long-term investment recommendations.

## 2) Credibility blockers (must fix)
- [x] Stop training on predictions-as-labels (e.g., FutureSkillPrediction.level).
- [x] Remove labels derived from rules using the same features used for training (rules can remain as baseline/fallback, not ground truth).
- [x] Formalize label provenance for every training label (BRONZE/SILVER/GOLD).
- [x] Ensure the training dataset is built from signals at time T only; labels must represent outcomes observed at T+H (no leakage).

## 3) Label strategy: Provenance ladder (Bronze / Silver / Gold)
- [x] BRONZE: keep current rule-engine labels for baseline and cold start only.
- [x] SILVER: derive labels from forward observed outcomes over horizon H months (no human required).
- [x] SILVER: compute deltas between T and T+H (trend_score, internal_usage, training_requests).
- [x] SILVER: keep scarcity_index/hiring_difficulty as features or decision-policy inputs, not part of label computation.
- [x] SILVER: bucket LOW/MED/HIGH via per-snapshot quantiles (p33/p66), with rank-based fallback when thresholds collapse.
- [x] GOLD: collect human-validated labels on uncertain/high-impact cases (active learning).
- [x] Train/evaluate on SILVER/GOLD; use BRONZE only for baseline comparisons.
- [x] Track label provenance distribution over time (how much SILVER/GOLD vs BRONZE).

## 4) Time and horizon (foresight)
- [x] Persist snapshots with as_of_date (explicit temporal indexing).
- [x] Add horizon_months (start with 12; optionally 36/60).
- [x] Add as_of_date, horizon_months, and label_provenance columns to the ML dataset export.
- [x] Interpret predictions as "need level at horizon H months, estimated at time T".
- [x] Ensure all features used for prediction are available at time T (no post-hoc fields).
- [x] Define and document the snapshot frequency (monthly/quarterly) and acceptable missing-data policy.
- [x] Policy: monthly snapshots by default; if T or T+H snapshot is missing for a (job_role, skill), skip that row and log the missing count.

## 5) Formulation upgrades (same objective, more professional)
- [x] Produce a continuous need_score (0-1 or 0-100) as the core output (for prioritization and budget allocation).
- [x] Derive LOW/MED/HIGH as a presentation layer via thresholds/quantiles (policy-controlled, stable across time).
- [x] Provide Top-N ranking per sector/department/job_role (executive-friendly output).
- [x] Normalize Top-N within each group to avoid size bias and improve comparability.
- [x] Normalization policy: min-max normalization per group on need_score.
- [x] Optional: forecast key signals (trend/internal/training) if time-series depth exists; map forecasts -> need_score/levels.
- [x] Keep the rules engine as:
  - [x] Baseline comparator (BRONZE).
  - [x] Fallback path when ML confidence is low.
  - [x] Fallback reason codes, separate from model explanations.

## 6) Feature engineering for foresight (dynamics)
- [x] Add trend_momentum (slope), trend_acceleration, trend_volatility, trend_persistence.
- [x] Add rolling means and lags (t-1, t-2) for macro indicator and internal signals.
- [x] Add stability flags to avoid reacting to one-off spikes (hype vs persistent trend).
- [x] Add sector/role interaction features (skill relevance differs by context).
- [x] Add data quality flags (missingness, stale values, low sample counts) to support abstain policies.

## 7) Output contract (API payload)
- [x] predicted_level (LOW/MED/HIGH).
- [x] need_score (continuous).
- [x] probabilities (p_low, p_medium, p_high) if model supports probabilistic output; otherwise provide a calibrated confidence score.
- [x] confidence (explicit, actionable thresholding).
- [x] Define calibration method for probabilities or confidence (and how thresholds map to abstain/fallback).
- [x] Policy: fallback to rules_v1 if confidence < 0.60 (or HIGH confidence < 0.70); reason code stored in decision_policy.
- [x] top_drivers (explanations of main factors and their direction of impact).
- [x] recommended_actions (hire vs train vs internal upskilling) with rationale and optional policy mapping.
- [x] label_provenance_used (BRONZE/SILVER/GOLD) for the training dataset and/or the evaluated cohort.
- [x] model_version, data_window, as_of_date, horizon_months.
- [x] decision_policy metadata (thresholds used, abstain rules, fallback reason codes).
- [x] audit payload persisted per prediction (inputs hash, outputs, explanations, versioning).

## 8) Evaluation protocol (time-aware, leakage-safe)
- [x] Use time-based splits (train on older periods, test on later periods).
- [x] Use blocked/rolling window evaluation (walk-forward) when snapshots are periodic.
- [x] Walk-forward policy: expanding window, max 5 folds, requires >=4 distinct snapshot dates.
- [x] Report metrics by sector, department, job_role (not just global).
- [x] Require a minimum slice size before reporting per-slice metrics (document threshold).
- [x] Track macro-F1 / balanced accuracy for LOW/MED/HIGH.
- [x] Track confusion matrix (overall and per slice).
- [x] Track calibration if probabilities are returned (reliability / Brier score).
- [x] Compare ML vs rules engine (BRONZE baseline).
- [x] Document the final holdout window used for audit.
- [x] Never evaluate on labels derived from prior predictions.
- [x] Explicitly avoid random KFold/StratifiedKFold on time-indexed data (risk of temporal leakage).
- [x] Handle class imbalance via class weights and/or threshold policy; avoid leakage-driven balancing strategies.

### 8.1) Advanced CV strategy (optional, professional-grade)
- [x] Nested CV (recommended only if enough history):
  - [x] Outer loop: time-based blocked split for unbiased estimation.
  - [x] Inner loop: time-based blocked split within the training window for tuning.
- [x] If nested CV is not used:
  - [x] Use a fixed temporal validation window + final holdout window (document the windows explicitly).

### 8.2) Advanced metrics (beyond accuracy)
- [x] Cohen's Kappa as agreement beyond chance (useful under imbalance).
- [x] Weighted Cohen's Kappa (preferred) due to ordinal nature of LOW < MEDIUM < HIGH (penalize LOW <-> HIGH more than MEDIUM <-> HIGH).
- [x] Report per-class precision/recall and macro averages.
- [x] If using need_score regression: N/A (current model is classification + ranking; no regression head).
- [x] If using ranking outputs:
  - [x] Validate Top-N relevance qualitatively with RH and quantitatively with simple hit-rate proxies (if available).

## 9) Production governance (enterprise-grade)
- [x] Implement abstain + fallback to rules when confidence is low (explicit threshold).
- [x] Add drift monitoring for trend/scarcity/macro distributions with alerts.
- [x] Use a lightweight drift metric (e.g., PSI or KS) with documented thresholds for alerts.
- [x] Persist model lineage and audit log (model_version, feature snapshot hash, explanation payload, decision policy).
- [x] Persist dataset metadata in TrainingRun (label provenance counts, as_of_date range, time split used).
- [x] Add retraining triggers:
  - [x] Time-based schedule (e.g., monthly/quarterly).
  - [x] Drift-based triggers (feature shift, label shift, calibration degradation).
- [x] Add monitoring dashboards:
  - [x] Prediction volume, confidence distribution, abstain rate.
  - [x] Slice performance (sector/department/role) over time.
  - [x] Data freshness and missingness.

## 10) Implementation roadmap (phased, minimal refactor)
- [x] Phase A: add snapshots with as_of_date (market + internal).
- [x] Phase A: add label provenance (BRONZE/SILVER/GOLD).
- [x] Phase A: build SILVER labels from 12-month forward outcomes (document exact policy).
- [x] Phase A: keep BRONZE rules baseline and fallback policy.
- [x] Phase B: train on SILVER/GOLD only.
- [x] Phase B: use score-based formulation + derived buckets (LOW/MED/HIGH).
- [x] Phase B: add Top-N ranking outputs.
- [x] Phase B: add explainability payload (top drivers + reason codes).
- [x] Phase C: add time dynamics features (momentum/volatility/persistence).
- [x] Phase C: add scenario/what-if layer (optional, decision-support).
- [x] Phase D: add calibration/confidence thresholds (if probabilities exist).
- [x] Phase D: add drift detection and alerting.
- [x] Phase D: add full audit trail + versioning + monitoring dashboards.
- [x] Phase D: optional nested time-based CV for robust tuning and reporting.

## 11) Final Do / Don't
- [x] Do: keep one objective; enhance time/horizon, score, ranking, governance.
- [x] Do: make label provenance explicit; train/evaluate on SILVER/GOLD.
- [x] Do: use time-aware evaluation; document windows and prevent leakage.
- [x] Do: use weighted kappa + macro metrics for ordinal classification quality.
- [x] Do: keep rules as baseline + fallback, not as ground truth.
- [x] Don't: train on your own prediction table as labels.
- [x] Don't: add attrition/salary/performance prediction types into Module 3.
- [x] Don't: use random splits (KFold/StratifiedKFold) that leak time on foresight datasets.
- [x] Don't: rely on accuracy alone; always report imbalance-robust and ordinal-aware metrics.
