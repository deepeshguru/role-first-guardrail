# Guardrail Metrics

- Total requests: **38**
- Allow: **18**, Deny: **20**
- Latency p50: **13.48 ms**, p95: **19.39 ms**
- Policy version(s): `1.0.0`

## Allow rate by role

| Role | Samples | Allow rate |
|---|---:|---:|
| admin | 10 | 0.60 |
| hr_manager | 8 | 0.25 |
| intern | 8 | 0.50 |
| engineer | 6 | 0.33 |
| finance_analyst | 6 | 0.67 |

## Allow rate by intent

| Intent | Samples | Allow rate |
|---|---:|---:|
| retrieve_hr_payroll | 10 | 0.20 |
| admin_override | 8 | 0.50 |
| ask_metrics_finance | 6 | 1.00 |
| write_code | 6 | 0.67 |
| retrieve_customer_pii | 4 | 0.00 |
| ask_public_policy | 2 | 1.00 |
| unknown | 2 | 0.00 |

## Top deny reasons

| Reason | Count |
|---|---:|
| explicit_deny | 6 |
| missing_attr:org_unit | 4 |
| not_in_allow | 4 |
| break_glass_missing | 4 |
| unknown_intent | 2 |

## Role × Intent (allow rate)

| Role | admin_override | ask_metrics_finance | ask_public_policy | retrieve_customer_pii | retrieve_hr_payroll | unknown | write_code |
|---|---|---|---|---|---|---|---|
| admin | 0.50 (4/8) | 1.00 (2/2) | — | — | — | — | — |
| engineer | — | — | — | 0.00 (0/2) | 0.00 (0/2) | — | 1.00 (2/2) |
| finance_analyst | — | 1.00 (4/4) | — | — | — | — | 0.00 (0/2) |
| hr_manager | — | — | — | 0.00 (0/2) | 0.33 (2/6) | — | — |
| intern | — | — | 1.00 (2/2) | — | 0.00 (0/2) | 0.00 (0/2) | 1.00 (2/2) |
