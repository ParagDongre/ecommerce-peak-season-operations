# 02 - KPI Dictionary

> **SIMULATED DATA / HYPOTHETICAL BUSINESS.** This is an independent portfolio case study about a fictional retailer ("NorthBay Mart"). It uses no Amazon data, metrics or processes, and makes no claim about any real operation. Scenario results are *modelled estimates*, not measured improvements.

All metrics are computed from the simulated datasets by the code in `src/analysis.py`, `src/calc.py` and `src/scenarios.py`.
Hour-level quantities cover operating hours 07:00-22:59 and two skill queues (OD = Order & Delivery; RP = Returns, Payments & Product).

| Metric | Definition | Formula | Unit | Source | Interpretation / caveat |
|---|---|---|---|---|---|
| Orders (forecast / actual) | Orders placed per day: planner forecast vs simulated actual | - | orders/day | `orders_daily.csv` | Demand level and trend. Event days are shown as multiples of the baseline-week average. |
| Order growth | Day-over-day change in actual orders | (Orders_t / Orders_t-1 - 1) x 100 | % | `orders_daily.csv` | Launch jump and finale peak. |
| Fulfilment exception rate | Late shipments + failed deliveries + damaged/missing, per 100 orders | exceptions / orders x 100 | % | `orders_daily.csv` | Upstream driver of delivery-delay contacts one to two days later. |
| Cancellation rate | Cancellations (all causes) per 100 orders | cancellations / orders x 100 | % | `orders_daily.csv` | Stock-out cancellations drive cancel/modify contacts. |
| Return rate | Returns initiated per 100 orders placed that day | returns / orders x 100 | % | `orders_daily.csv` | Returns arrive 3-9 days after the order, so the rate on a day mixes earlier orders. |
| Customer contacts | Contacts arriving in an hour by issue category and skill queue | - | contacts | `contacts_hourly.csv` | Workload driver. Two queues: OD (order status, delay, cancel/modify), RP (returns, payment/promo, product). |
| Contacts per 100 orders | Contact intensity | contacts / orders x 100 | contacts | `A1_demand_daily_summary.csv` | Rises when exceptions/promo complexity increase. |
| WAPE (forecast error) | Weighted absolute percentage error. **Chosen primary metric**: volume-weighted, stable at low-volume hours where MAPE explodes | sum|A-F| / sum A x 100 | % | `A2_forecast_accuracy.csv` | Lower is better. Does not show direction, so read with bias. |
| Forecast bias | Signed error; negative = under-forecast | (sum F - sum A) / sum A x 100 | % | `A2_forecast_accuracy.csv` | Direction of the miss. Offsetting errors can make aggregate bias near zero while categories are far off. |
| MAPE (contrast only) | Mean of per-point absolute % error, points with actual < 10 skipped | mean(|A-F|/A) x 100 | % | `A2_forecast_accuracy.csv` | Shown to illustrate why WAPE is preferred. |
| Average handling time (AHT) | Mean agent time per contact (talk + after-contact work) | workload_seconds / contacts | seconds | `contacts_hourly.csv` | Planned AHT = baseline-week volume-weighted mean; event AHT is higher through a modelled complexity factor. |
| Workload hours | Agent time needed to handle contacts | contacts x AHT / 3600 | agent-hours | `staffing_hourly.csv` | Input to staffing requirement. |
| Shrinkage (non-absence) | Share of present time not on contacts (breaks, coaching, meetings, downtime) | assumption | 12% | `assumptions.csv` | Planner convention, not sourced from any company. |
| Planned shrinkage | Shrinkage used for scheduling = non-absence shrinkage combined with planned absence allowance | 1 - (1 - 0.12) x (1 - 0.06) = 0.1728 | fraction | `assumptions.csv` | Scheduled-basis requirement. |
| Target occupancy | Planned share of productive time spent on contacts | assumption | 85% | `assumptions.csv` | Keeps queue stable and SLA attainable. |
| Required staffing (agents) | Agents that must be present (actual basis) or scheduled (planned basis) in an hour | ceil( workload_hours x (1 + buffer) / ((1 - shrinkage) x occupancy) ) | agents | `staffing_hourly.csv` | Planned requirement uses forecast workload, planned AHT, 10% contingency and planned shrinkage. `required_actual` uses actual workload, no buffer, non-absence shrinkage (compare with *available*). |
| Scheduled staffing | Agents rostered on shift in the hour | sum of shift-template coverage | agents | `staffing_hourly.csv` | Built by a greedy roster rule against the planned requirement (3 templates, 8-hour shifts). |
| Available staffing | Scheduled minus absent | scheduled - absent | agents | `staffing_hourly.csv` | Absence drawn per agent from a shared random lottery. |
| Capacity gap | Positive = shortfall | required_actual - available | agents | `staffing_hourly.csv` | Hourly, so a surplus at 15:00 cannot offset a shortfall at 19:00. |
| Understaffed hour | Group-hour with capacity gap > 0 | gap > 0 | count | `staffing_hourly.csv` | Counts both queues separately (224 group-hours in the event week). |
| Shortfall agent-hours | Gross sum of positive gaps | sum max(0, gap) | agent-hours | `B1_capacity_daily_by_group.csv` | Size of the gap. Surplus agent-hours reported separately; net can look balanced while gross is not. |
| SLA attainment | Share of contacts answered within the threshold | share with wait <= 300s; arrival-weighted when aggregated | % | `service_hourly.csv` | Target 80%. Modelled, not observed. |
| Response time | Mean wait before an agent picks up | Erlang C ASA or fluid-queue mean wait (see methodology) | seconds | `service_hourly.csv` | Arrival-weighted when aggregated. |
| Backlog | Contacts waiting at the end of the hour | backlog_start + arrivals - handled | contacts | `service_hourly.csv` | Carries across hours and overnight. |
| Capacity (contacts/hour) | Contacts the available agents can handle | effective agents x 0.95 x 3600 / AHT | contacts | `service_hourly.csv` | Physical throughput ceiling at 95% occupancy. |
| Load ratio | Workload relative to productive agents | workload_hours / (available x (1 - shrinkage)) | ratio | `C4_shortfall_sla_correlations.csv` | > about 0.95 means the queue cannot keep up. |
| Absence rate | Share of scheduled shifts lost to unplanned absence | absent / scheduled | % | `absences_daily.csv` | Assumed 6% baseline; event-day assumptions in `assumptions.csv`. |
| Variance (planned vs actual) | Actual minus planned and as % of planned | A - P; (A - P) / P x 100 | unit / % | `D1_planned_vs_actual_event_days.csv` | Planned = forecast, plan or target. Ranked in `D2_largest_variances.csv`. |
| Volume effect / AHT effect | Decomposition of workload variance | (A_c - F_c) x AHT_plan / 3600; A_c x (AHT_act - AHT_plan) / 3600 | agent-hours | `B5_workload_variance_decomposition.csv` | Sums exactly to actual minus forecast workload (tested). The AHT effect at queue level also absorbs category-mix shifts within a queue. |
| Defect / DPMO / sigma level | DMAIC measure: a contact not answered within threshold is a defect | DPMO = defects / contacts x 1e6; sigma = z(1 - defect rate) + 1.5 | - | `07_Six_Sigma_DMAIC.md` | Illustrative; uses the conventional 1.5-sigma shift. |
| Paid agent-hours | Rostered hours incl. extra capacity | sum agents x shift length | agent-hours | `E1_scenario_comparison_single_seed.csv` | Only cost proxy; no currency modelled. |
| Risk score | Probability x impact | 1-5 x 1-5 | 1-25 | `04_Risk_and_Mitigation_Register.csv` | Rating: Critical >= 20, High >= 12, Medium >= 6. |

## Aggregation rules

- **SLA, response time, AHT** are arrival-weighted when rolled up from hours to days/weeks (never a simple average of hourly percentages).
- **Capacity gaps** are computed per group-hour and summed; surplus is never netted against shortfall in the hourly measure.
- **Baseline week** (B1-B7) is used to learn contact rates, the hourly profile and planned AHT, so baseline-week forecast accuracy is in-sample and flattering by design; the event week is out-of-sample.
