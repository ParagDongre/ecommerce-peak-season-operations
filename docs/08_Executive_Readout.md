# 08 - Executive Readout

> **SIMULATED DATA / HYPOTHETICAL BUSINESS.** This is an independent portfolio case study about a fictional retailer ("NorthBay Mart"). It uses no Amazon data, metrics or processes, and makes no claim about any real operation. Scenario results are *modelled estimates*, not measured improvements.

**Event:** 7-day sale, 2026-11-16 to 2026-11-22 (hypothetical). **Audience:** Leadership Sponsor. **Basis:** simulated data; scenario figures are modelled estimates.

## Headline

The support plan holds at normal volume (92.5% SLA) but not at event volume: **67.4% SLA vs an 80% target, with 3 of 7 days on target** (one simulated run; the mean over 200 replications for the as-planned case is 63%, p10-p90 50-75%). The gap is concentrated in one queue (Order & Delivery) on specific days and evening hours, not spread evenly.

## What the evidence shows

1. **A decent total forecast hid a bad mix.** Event-week contact forecast was 11.5% off in total (bias -7.0%), but Order & Delivery workload ran 24% above forecast while the other queue finished with 544 agent-hours to spare.
2. **Trouble arrives a day late.** Launch day E1 met SLA; E2 collapsed after stock-outs and exceptions generated contacts 1-2 days later. The finale E7 closed with the largest backlog (400 contacts carried over; SLA 42.5%; the lowest-SLA day was E2 at 37.6%). E7 also had 6,911 fulfilment exceptions.
3. **Weekly balance is a trap.** Order & Delivery had enough agent-hours for the week in total, yet was short in 46 of 112 hours; spare capacity on quiet days and in the other queue cannot be banked.

## Options and trade-offs (modelled, mean of 200 replications)

| Option | Extra paid agent-h | Mean event SLA % (modelled) | End backlog (modelled) | Main trade-off / risk | Note |
|---|---|---|---|---|---|
| S0 Do nothing (plan as built) | 0 | 63 | 174 | None | Baseline |
| S2 Cross-train 20% of agents | 0 | 72 | 113 | Training time and cost not modelled; certification by T-7 | Training |
| S4 Targeted extra peak cover (OD) | 420 | 80 | 15 | Approval by T-14; hiring/overtime route not modelled | Finance approval |
| S6 Both S2 + S4 | 420 | 86 | 4 | Both sets of dependencies | Best modelled |
| S1 Re-shape existing rosters | 0 | 63 | 163 | Low effort, no measurable gain | Not recommended |

Reading it: targeting the same extra hours at the bottleneck queue beats spreading them; cross-training helps without extra paid hours but has costs this model does not capture; re-shaping rosters inside the current shift patterns does not help. Ranges overlap between neighbouring options (see `E2_scenario_monte_carlo_summary.csv`), and even the best option misses target in some replications.

## Decisions needed

| # | Decision | Owner | By |
|---|---|---|---|
| 1 | Approve ~420 paid agent-hours of extra 17:00-22:00 capacity, assigned to Order & Delivery | Finance / Leadership Sponsor | 2026-11-02 (T-14) |
| 2 | Approve cross-training of 20% of agents and fund a cost/lead-time estimate | Support Training Manager / Sponsor | 2026-11-02 (T-14) |
| 3 | Mandate a by-queue, lag-aware forecast with twice-daily re-forecast and the escalation triggers in `07_Six_Sigma_DMAIC.md` | Workforce Planning Lead | 2026-11-09 (T-7) |

## Next steps

1. Owners confirm dependencies D01-D09 (`04b_Dependency_Tracker.csv`); go/no-go at T-1.
2. Cost the cross-training and extra-capacity routes; re-run scenarios with those costs and with sensitivity on forecast bias and absence.
3. Stand up the control plan (daily SLA, backlog, queue-hour gap, forecast error, exception feed).

## What could prevent success

Late approval (R10), cross-training not certified (R08), late exception/promo data (R02, R03), larger absence than assumed (R04, R12). Full register: `04_Risk_and_Mitigation_Register.csv`.

## How success will be verified

Event-week SLA >= 80% with at least 6 of 7 days on target, no end-of-day backlog above 100, queue-hour gaps trending to zero; measured from daily SLA/backlog actuals against the thresholds in the control plan.
