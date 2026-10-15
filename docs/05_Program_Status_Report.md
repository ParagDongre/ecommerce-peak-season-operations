# 05 - Program Status Report (weekly)

> **SIMULATED DATA / HYPOTHETICAL BUSINESS.** This is an independent portfolio case study about a fictional retailer ("NorthBay Mart"). It uses no Amazon data, metrics or processes, and makes no claim about any real operation. Scenario results are *modelled estimates*, not measured improvements.

**Report period:** event week E1-E7 (2026-11-16 to 2026-11-22), status as of close of E7. **Prepared by:** Program Manager (WFM), hypothetical. **Data:** simulated, seed 42.

## Overall status: **RED** for service levels; AMBER for plan execution

| Area | Status | Summary |
|---|---|---|
| Service levels | RED | Event-week SLA 67.4% vs 80% target; 3 days below 60% (E2, E3, E7). |
| Capacity | RED | 56 of 224 group-hours understaffed; OD short 246 gross agent-hours while RP carried 544 surplus. |
| Forecast | AMBER | Daily-total contact WAPE 11.5% (bias -7.0%); category WAPE up to 51%. |
| Risks and dependencies | AMBER | 12 risks logged, 7 High/Critical; 9 dependencies tracked. |
| Schedule | GREEN | Milestones T-21 to T+7 on plan (hypothetical). |

## Key metrics

| Day | SLA % | RAG | Understaffed group-hours | End backlog |
|---|---|---|---|---|
| E1 | 99.4 | GREEN | 1 | 0 |
| E2 | 37.6 | RED | 11 | 126 |
| E3 | 56.3 | RED | 9 | 0 |
| E4 | 98.7 | GREEN | 1 | 0 |
| E5 | 96.0 | GREEN | 9 | 0 |
| E6 | 62.5 | AMBER | 13 | 33 |
| E7 | 42.5 | RED | 12 | 400 |

## Accomplished

- Built the synthetic dataset, analysis pipeline and dashboard; 60 assumptions documented.
- Quantified forecast accuracy (WAPE/bias), capacity gaps and the shortfall-to-SLA relationship.
- Compared 7 scenarios across 200 Monte Carlo replications (modelled estimates).
- Produced risk register, dependency tracker, RACI, DMAIC and executive readout.

## Issues and variances

1. **Launch day looked healthy, then service broke on E2.** E1 SLA was 99% but E2 38%: stock-out cancellations and exceptions on E1-E2 create contacts 1-2 days later that the order-based forecast does not contain.
2. **The finale (E7) ended with the largest backlog** (42% SLA, 400 contacts carried; lowest-SLA day was E2 at 38%): orders +9% vs forecast, 6,911 fulfilment exceptions, evening deal drop.
3. **Queue imbalance.** Spare RP capacity could not help OD without cross-skilling.

## Top risks (owner / due / escalation trigger)

| ID | Risk | Score | Owner (role) | Due | Escalation trigger |
|---|---|---|---|---|---|
| R01 | Contact-mix forecast error: Order & Delivery workload under-forecast while Returns/Payments is over-planned | 25 | Workforce Planning Lead | 2026-11-09 | OD queue SLA < 70% for 2 consecutive hours OR backlog > 100 contacts |
| R08 | Siloed skill queues prevent moving spare capacity to the bottleneck | 20 | Customer Support Training Manager | 2026-11-02 | Cross-trained headcount < 15% at T-7 days |
| R02 | Delivery-delay contacts lag fulfilment exceptions by 1-2 days and are not in the order-based forecast | 16 | Operations Program Manager | 2026-11-11 | Late-shipment count > 2x baseline-day average OR carrier-disruption notice |
| R06 | Backlog carry-over snowball: overnight backlog is not cleared before next day's peak | 16 | Customer Support Operations Manager | 2026-11-11 | End-of-day backlog > 150 contacts |

## Decisions needed

| # | Decision | Decision owner | Needed by |
|---|---|---|---|
| 1 | Approve +420 paid agent-hours of peak-cover capacity targeted at OD | Finance / Leadership Sponsor | 2026-11-02 |
| 2 | Approve cross-training of 20% of agents (training cost not yet estimated) | Customer Support Training Manager / Sponsor | 2026-11-02 |
| 3 | Adopt by-queue, lag-aware forecast with daily re-forecast and escalation triggers | Workforce Planning Lead | 2026-11-09 |

## Next steps (next 7 days)

1. Run the post-event review and agree the control plan (`07_Six_Sigma_DMAIC.md`, Control).
2. Estimate cross-training cost and lead time (currently unmodelled).
3. Re-run scenarios with sensitivity ranges for absence and forecast bias.
4. Hand daily exception/stock-out feeds to Workforce Planning (dependencies D01-D02).

## Dependencies and deadlines

| ID | Provider | Consumer | Deliverable | Needed by |
|---|---|---|---|---|
| D01 | Operations (Fulfilment) | Workforce Planning | Daily late-shipment/exception counts by 10:00 | 2026-11-11 |
| D02 | Operations (Inventory) | Customer Support | Stock-out alerts for promo items (>= 24 h notice) | 2026-11-11 |
| D03 | Marketing | Workforce Planning | Approved promo calendar incl. deal drops (72 h notice) | 2026-11-06 |
| D04 | Workforce Planning | Customer Support | Corrected daily roster by 14:00 for next day | 2026-11-15 |
| D05 | Customer Support Training | Workforce Planning | Cross-trained agent certification list | 2026-11-02 |
| D06 | Finance / Leadership | Workforce Planning | Approval of additional peak-cover capacity | 2026-11-02 |
| D07 | HR / Scheduling | Customer Support | Absence reporting same-day by 08:00; shift-swap protocol | 2026-11-13 |
| D08 | Customer Support | Workforce Planning | Daily AHT and backlog actuals | 2026-11-16 |
| D09 | Workforce Planning | Leadership | Daily SLA/backlog status and escalation notes | 2026-11-16 |
