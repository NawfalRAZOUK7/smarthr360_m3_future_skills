# Module 3 Scope Guardrails

Objective
- Future Skills Need (foresight) only.
- Keep the flow: market trends -> emerging skills by sector -> internal alignment -> long-term investment recommendations.

Out of scope
- Attrition, salary, or performance predictions are not part of Module 3.
- Any additional prediction targets belong to their own modules.

Output policy
- The continuous `need_score` is the core signal.
- LOW/MED/HIGH are presentation layers derived from stable score thresholds.
- Interpret predictions as: "need level at horizon H months, estimated at time T".
- Features used for prediction must be available at time T (no post-hoc fields).

Label policy
- Train and evaluate on SILVER/GOLD only.
- BRONZE stays a baseline/fallback, never ground truth.
