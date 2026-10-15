"""Docs 07 (DMAIC), 08 (executive readout), 09 (methodology), 10 (portfolio summary) and README."""
from __future__ import annotations

import pandas as pd

from .docs_common import BANNER, md_table, num, pct


def dmaic(c) -> str:
    p, H, E, m = c.p, c.H, c.E, c.mcs_i
    b, e = c.dmaic["baseline"], c.dmaic["event"]
    fa = c.fa_i
    od_fa = fa.loc[("contacts by category (daily)", "event: delivery_delay"), "bias_pct"]
    ret_fa = fa.loc[("contacts by category (daily)", "event: returns_refunds"), "bias_pct"]
    meas = pd.DataFrame([
        ("Contacts handled", num(b["contacts"]), num(e["contacts"])),
        ("Defects (contacts not answered within threshold)", num(b["defects"]), num(e["defects"])),
        ("Defect rate", pct(b["rate"] * 100), pct(e["rate"] * 100)),
        ("DPMO", num(b["dpmo"]), num(e["dpmo"])),
        ("Sigma level (1.5-shift convention, illustrative)", f"{b['sigma']:.2f}", f"{e['sigma']:.2f}"),
        ("SLA attainment", pct(H["baseline_week_sla_pct"]), pct(H["event_week_sla_pct"])),
    ], columns=["Measure", "Baseline week (B1-B7)", "Event week (E1-E7)"])
    sc = c.mcs[["scenario", "description", "sla_overall_mean", "sla_overall_p10", "sla_overall_p90", "paired_delta_sla_mean", "end_backlog_mean", "extra_paid_agent_hours"]]
    ctrl = pd.DataFrame([
        ("Daily SLA attainment (by queue)", f">= {p.sla_target*100:.0f}%; amber < {p.sla_target*100:.0f}%; red < 60%", "Customer Support Ops Manager", "Hourly during event; daily review", "Two consecutive hours < 70% in a queue -> Program Manager; red day -> Sponsor same day"),
        ("End-of-day backlog", "<= 100 contacts amber at 100, red at 150", "Customer Support Ops Manager", "Daily 22:30", "Red -> activate recovery roster and overflow capacity"),
        ("Queue-hour capacity gap", "0 agents short; amber 1-2; red >= 3", "Workforce Planning Lead", "Twice daily (10:00, 16:00)", "Same hour short on 3 consecutive days -> roster change request"),
        ("Contact forecast error (day-to-date, by queue)", "within +/-10%", "Workforce Planning Analyst", "Twice daily", "Outside +/-10% -> apply rolling correction; > +/-20% -> escalate"),
        ("Fulfilment exceptions (daily count)", "<= 2x baseline-day average", "Fulfilment Ops Manager", "Daily 10:00 feed", "> 2x -> lagged contact uplift added to next-day forecast"),
        ("Absence rate", "<= 8% of scheduled shifts", "Customer Support Ops Manager", "Daily 08:00", "> 10% -> standby pool / shift swaps"),
        ("AHT vs plan", "within +5%", "Customer Support Quality Lead", "Daily", "> 8% -> macro/FAQ fix; update planning AHT"),
        ("Cross-trained headcount", f">= {p.flex_share*100:.0f}% certified by T-7", "Customer Support Training Manager", "Weekly until T-7", "< 15% at T-7 -> Sponsor"),
    ], columns=["Metric", "Threshold", "Owner (role)", "Cadence", "Escalation rule"])
    od_e2 = c.svc[(c.svc.day_label == "E2") & (c.svc.skill_group == "OD")].iloc[0]
    trig = (f"in this run OD SLA on E2 was {od_e2.sla_attainment_pct:.0f}% (below the 70% trigger) and OD backlog at close was {od_e2.end_of_day_backlog_contacts:.0f} contacts "
            f"({'above' if od_e2.end_of_day_backlog_contacts > 100 else 'below'} the 100-contact amber line)")
    return f"""# 07 - Six Sigma DMAIC (simulated exercise)

{BANNER}

> This is a **simulated DMAIC exercise** on synthetic data, an application of the framework to a hypothetical operation. It is **not** a real company process-improvement engagement and makes no claim about delivered results.

## Define

**Problem statement.** During the 7-day "Winter Mega Sale", the hypothetical retailer's customer-support plan fails to hold service levels: event-week SLA is {pct(H['event_week_sla_pct'])} against an {p.sla_target*100:.0f}% target, and {H['days_meeting_target']} of {p.n_event_days} event days meet it.

**Business objective.** Hold at least {p.sla_target*100:.0f}% of contacts answered within {p.sla_threshold_sec} seconds on at least 6 of 7 event days, with no end-of-day backlog above 100 contacts, within existing approval limits.

**Critical-to-quality (CTQ).** (1) Speed of answer (SLA); (2) no standing backlog; (3) staffing matched to workload by queue and hour; (4) forecast reliable enough to staff against.

**Scope.** Customer-contact staffing and forecasting for two queues (OD, RP) over 14 days. Out of scope: fulfilment redesign, pricing/promotions, tooling.

**SIPOC (high level).**

| Supplier | Input | Process | Output | Customer |
|---|---|---|---|---|
| Fulfilment Ops, Inventory, Marketing, Finance | Orders, exceptions, stock-outs, promo calendar, approvals | Forecast contacts -> compute requirement -> roster -> operate -> monitor/re-forecast | Answered contacts within SLA | Shoppers; Leadership |

## Measure

Defect definition: a contact not answered within {p.sla_threshold_sec}s (arrival-weighted from the hourly queue model).

{md_table(meas, None, None, {k: str for k in meas.columns})}

The sigma level uses the conventional 1.5-sigma shift and is illustrative only. Baseline-week performance shows the plan works at normal volume; the event week is where it fails.

Other baseline measures (all from the simulated data): contact forecast WAPE {pct(E['contact_wape_event'])} / bias {pct(E['contact_bias_event'], sign=True)} (event week); {H['understaffed_group_hours_event']} of {H['group_hours_event']} event group-hours understaffed; worst day {H['worst_sla_day']} at {pct(H['worst_sla_pct'])}; E7 close backlog {num(H['end_backlog_E7'])} contacts.

## Analyze

Plausible root causes, each tied to modelled evidence (and what the evidence does *not* show):

| # | Root cause | Evidence in the simulation | Caveat |
|---|---|---|---|
| 1 | **Contact-mix forecast error.** The forecast applies baseline contacts-per-order to forecast orders | OD workload {pct(E['od_workload_var_pct'], 0, True)} vs forecast; RP {pct(E['rp_workload_var_pct'], 0, True)}; category biases range from returns {pct(ret_fa, 0, True)} to delivery delay {pct(od_fa, 0, True)} | Planted by design; real mix error would need to be measured |
| 2 | **Lagged contact drivers not in the plan.** Exceptions and stock-outs generate contacts 1-2 days later | E1 SLA held but E2 collapsed; exceptions peaked at {num(E['peak_exceptions'])} on {E['peak_exceptions_day']}; delay contacts {pct(E['delay_uplift_pct'], 0, True)} vs baseline day | Lags are model assumptions |
| 3 | **Siloed queues.** Surplus in RP cannot serve OD | RP surplus {num(E['rp_surplus_hours'])} agent-hours while OD short {num(E['od_shortfall_hours'])} gross | Cross-skill feasibility not tested |
| 4 | **Weekly balance masks hourly/daily gaps** | OD net gap about zero for the week yet {E['od_understaffed_hours']} understaffed hours | Hourly rounding inflates small-volume gaps |
| 5 | **Roster shape.** Few shift templates; one template covers the 19:00 peak | Top short hours: {E['top_short_hours']}; reallocating within templates (S1) changed SLA {pct(E['s1_delta_pp'], 1, True)[:-1]} pp | Template set is a design choice |
| 6 | **Handling-time drift (incl. mix shift) and absence** | Workload variance: volume {c.vol_hours:+.0f} vs AHT {c.aht_hours:+.0f} agent-hours; event absence {pct(E['event_absence_pct'])} of shifts vs {p.baseline_absence_rate*100:.0f}% planned (E3 spike {p.event_absence_rate[2]*100:.0f}%) | The queue-level "AHT effect" combines the +{(p.event_aht_complexity_factor-1)*100:.0f}% complexity factor with a shift toward longer-handling categories (e.g. delivery delay); the two are not separated. Absence alone is a minor contributor here |

Of the event-week workload variance, volume explains {c.vol_hours / c.var_hours * 100:.0f}% and queue-level AHT (complexity plus category-mix shift) {c.aht_hours / c.var_hours * 100:.0f}%. SLA is generated by a queue model from staffing and load, so the staffing-to-service link is true by construction; the *relative size* of the causes is a property of the assumptions.

## Improve

Seven options compared across {c.R['mc_replications']} Monte Carlo replications. **All results are modelled estimates**; no cost, productivity or SLA improvement is claimed for any real operation.

{md_table(sc, None, {'scenario':'ID','description':'Option','sla_overall_mean':'Mean event SLA %','sla_overall_p10':'p10','sla_overall_p90':'p90','paired_delta_sla_mean':'Change vs S0 (pp)','end_backlog_mean':'End backlog','extra_paid_agent_hours':'Extra paid agent-h'}, {'sla_overall_mean':lambda v:f'{v*100:.1f}','sla_overall_p10':lambda v:f'{v*100:.1f}','sla_overall_p90':lambda v:f'{v*100:.1f}','paired_delta_sla_mean':lambda v:f'{v*100:+.1f}','end_backlog_mean':lambda v:f'{v:.0f}','extra_paid_agent_hours':lambda v:num(v)})}

Selection logic (a simple impact vs cost/feasibility view, not a financial model):

- **Pilot first:** S2 cross-training: {m.loc['S2','paired_delta_sla_mean']*100:+.1f} pp, no extra paid hours, but unmodelled training cost and lead time.
- **Approve if budget allows:** S4 targeted capacity: {m.loc['S4','paired_delta_sla_mean']*100:+.1f} pp for +{num(m.loc['S4','extra_paid_agent_hours'])} paid agent-hours; better than the same hours spread evenly (S3 {m.loc['S3','paired_delta_sla_mean']*100:+.1f} pp).
- **Best modelled outcome:** S6 (S2 + S4): mean {m.loc['S6','sla_overall_mean']*100:.1f}% SLA, {m.loc['S6','days_meeting_target_mean']:.1f} of 7 days meeting target.
- **Do not rely on:** S1 reallocation within the current shift templates (no measurable gain).
- Even the best option does not reach target in every replication (p10 {m.loc['S6','sla_overall_p10']*100:.0f}%), so the control plan below still matters.

## Control

Monitoring thresholds, owners, cadence and escalation (hypothetical roles):

{md_table(ctrl, None, None, {k: str for k in ctrl.columns})}

**Review cadence.** Hourly queue check by the Ops Manager during the event; twice-daily forecast review; daily 22:30 status to the Program Manager; weekly executive readout; post-event review at T+7 with the control plan handed to a named owner.

**Sustaining the gain (if this were real).** Update planning AHT and contact rates by queue from the event; keep the lag-aware forecast; re-run scenarios before the next peak; verify that thresholds would have triggered: {trig}.
"""


def executive_readout(c) -> str:
    p, H, E, m = c.p, c.H, c.E, c.mcs_i
    due = pd.Timestamp(c.event_start) - pd.Timedelta(days=14)
    trade = pd.DataFrame([
        ("S0 Do nothing (plan as built)", 0, m.loc["S0", "sla_overall_mean"], m.loc["S0", "end_backlog_mean"], "None", "Baseline"),
        ("S2 Cross-train 20% of agents", 0, m.loc["S2", "sla_overall_mean"], m.loc["S2", "end_backlog_mean"], "Training time and cost not modelled; certification by T-7", "Training"),
        ("S4 Targeted extra peak cover (OD)", m.loc["S4", "extra_paid_agent_hours"], m.loc["S4", "sla_overall_mean"], m.loc["S4", "end_backlog_mean"], "Approval by T-14; hiring/overtime route not modelled", "Finance approval"),
        ("S6 Both S2 + S4", m.loc["S6", "extra_paid_agent_hours"], m.loc["S6", "sla_overall_mean"], m.loc["S6", "end_backlog_mean"], "Both sets of dependencies", "Best modelled"),
        ("S1 Re-shape existing rosters", 0, m.loc["S1", "sla_overall_mean"], m.loc["S1", "end_backlog_mean"], "Low effort, no measurable gain", "Not recommended"),
    ], columns=["Option", "Extra paid agent-h", "Mean event SLA % (modelled)", "End backlog (modelled)", "Main trade-off / risk", "Note"])
    return f"""# 08 - Executive Readout

{BANNER}

**Event:** 7-day sale, {c.event_start} to {c.event_end} (hypothetical). **Audience:** Leadership Sponsor. **Basis:** simulated data; scenario figures are modelled estimates.

## Headline

The support plan holds at normal volume ({pct(H['baseline_week_sla_pct'])} SLA) but not at event volume: **{pct(H['event_week_sla_pct'])} SLA vs an {p.sla_target*100:.0f}% target, with {H['days_meeting_target']} of 7 days on target** (one simulated run; the mean over {c.R['mc_replications']} replications for the as-planned case is {m.loc['S0','sla_overall_mean']*100:.0f}%, p10-p90 {m.loc['S0','sla_overall_p10']*100:.0f}-{m.loc['S0','sla_overall_p90']*100:.0f}%). The gap is concentrated in one queue (Order & Delivery) on specific days and evening hours, not spread evenly.

## What the evidence shows

1. **A decent total forecast hid a bad mix.** Event-week contact forecast was {pct(E['contact_wape_event'])} off in total (bias {pct(E['contact_bias_event'], sign=True)}), but Order & Delivery workload ran {abs(E['od_workload_var_pct']):.0f}% {'above' if E['od_workload_var_pct']>0 else 'below'} forecast while the other queue finished with {num(E['rp_surplus_hours'])} agent-hours to spare.
2. **Trouble arrives a day late.** Launch day E1 met SLA; E2 collapsed after stock-outs and exceptions generated contacts 1-2 days later. The finale E7 closed with the largest backlog ({num(H['end_backlog_E7'])} contacts carried over; SLA {pct(c.svc_t[c.svc_t.day_label=='E7'].sla_attainment_pct.iloc[0])}; the lowest-SLA day was {H['worst_sla_day']} at {pct(H['worst_sla_pct'])}). E7 also had {num(c.orders[c.orders.day_label=='E7'].fulfilment_exceptions.iloc[0])} fulfilment exceptions.
3. **Weekly balance is a trap.** Order & Delivery had enough agent-hours for the week in total, yet was short in {E['od_understaffed_hours']} of 112 hours; spare capacity on quiet days and in the other queue cannot be banked.

## Options and trade-offs (modelled, mean of {c.R['mc_replications']} replications)

{md_table(trade, None, None, {'Extra paid agent-h':lambda v:num(v),'Mean event SLA % (modelled)':lambda v:f'{v*100:.0f}','End backlog (modelled)':lambda v:f'{v:.0f}'})}

Reading it: targeting the same extra hours at the bottleneck queue beats spreading them; cross-training helps without extra paid hours but has costs this model does not capture; re-shaping rosters inside the current shift patterns does not help. Ranges overlap between neighbouring options (see `E2_scenario_monte_carlo_summary.csv`), and even the best option misses target in some replications.

## Decisions needed

| # | Decision | Owner | By |
|---|---|---|---|
| 1 | Approve ~{num(m.loc['S4','extra_paid_agent_hours'])} paid agent-hours of extra 17:00-22:00 capacity, assigned to Order & Delivery | Finance / Leadership Sponsor | {due:%Y-%m-%d} (T-14) |
| 2 | Approve cross-training of {p.flex_share*100:.0f}% of agents and fund a cost/lead-time estimate | Support Training Manager / Sponsor | {due:%Y-%m-%d} (T-14) |
| 3 | Mandate a by-queue, lag-aware forecast with twice-daily re-forecast and the escalation triggers in `07_Six_Sigma_DMAIC.md` | Workforce Planning Lead | {pd.Timestamp(c.event_start) - pd.Timedelta(days=7):%Y-%m-%d} (T-7) |

## Next steps

1. Owners confirm dependencies D01-D09 (`04b_Dependency_Tracker.csv`); go/no-go at T-1.
2. Cost the cross-training and extra-capacity routes; re-run scenarios with those costs and with sensitivity on forecast bias and absence.
3. Stand up the control plan (daily SLA, backlog, queue-hour gap, forecast error, exception feed).

## What could prevent success

Late approval (R10), cross-training not certified (R08), late exception/promo data (R02, R03), larger absence than assumed (R04, R12). Full register: `04_Risk_and_Mitigation_Register.csv`.

## How success will be verified

Event-week SLA >= {p.sla_target*100:.0f}% with at least 6 of 7 days on target, no end-of-day backlog above 100, queue-hour gaps trending to zero; measured from daily SLA/backlog actuals against the thresholds in the control plan.
"""


def methodology(c) -> str:
    p, E = c.p, c.E
    return f"""# 09 - Methodology and Limitations

{BANNER}

## 1. What this is

A transparent simulation of customer-support demand, staffing and service for a hypothetical retailer, built to practise and demonstrate peak-season operations and workforce-planning analysis. Nothing is calibrated to any real business. Findings follow from the assumptions in `data/assumptions.csv` ({len(c.R['params'])} parameters, each with unit, basis and rationale).

## 2. Data generation (`src/generate_data.py`)

1. **Orders.** Baseline {num(p.baseline_orders_per_day)}/day with a weekday pattern and noise; event days at planner-forecast vs actual multiples of baseline (the forecast curve is deliberately smoother and slightly low on launch and finale).
2. **Fulfilment, cancellations, returns.** Orders above {num(p.fulfilment_capacity_orders_per_day)}/day ship late; a carrier disruption (E4-E5) and stock-outs (E1-E2) add exceptions and cancellations; returns are initiated 3-9 days after the order (so returns contacts lag).
3. **Contacts.** Expected daily contacts per category are driven by orders, exceptions (1-2 day lag), stock-out cancellations and returns; they are spread over 16 operating hours with an evening-weighted profile (plus unforecast evening deal drops on E1, E4, E7) and drawn from a Poisson distribution with day-level over-dispersion.
4. **Handling time.** Category AHT of 240-540 s, +{(p.event_aht_complexity_factor-1)*100:.0f}% in the event, with hour-level noise.
5. **Forecast.** Baseline-week contacts-per-order x forecast orders x baseline hourly profile; planned AHT from the baseline week. It cannot anticipate lags, promo complexity, mix shifts or deal drops. Baseline-week forecast is in-sample.
6. **Roster and absence.** Greedy roster (3 eight-hour templates) against the forecast requirement. Absence is drawn per agent from a uniform lottery shared by all scenarios, so scenario differences are not noise.
7. **Reproducibility.** `numpy.random.SeedSequence(seed)` spawns independent streams for orders, contacts and absences. Same seed and parameters give identical CSVs (tested against the committed `data/`).

## 3. Core calculations (`src/calc.py`)

- Workload hours = contacts x AHT / 3600.
- Required agents = ceil( workload x (1 + buffer) / ((1 - shrinkage) x occupancy) ). Planned (scheduled basis) uses planned shrinkage {p.planned_shrinkage:.4f} = 1 - (1 - {p.shrinkage}) x (1 - {p.baseline_absence_rate}) and a {p.planning_buffer*100:.0f}% buffer; actual (present basis) uses {p.shrinkage*100:.0f}% shrinkage and no buffer.
- **Queue model, hour by hour per queue.** Capacity = effective agents x {p.max_throughput_occupancy} x 3600 / AHT. If offered load is below capacity, SLA = min(Erlang C, fluid-queue) and response = max(Erlang ASA, fluid wait); otherwise a fluid FIFO queue accumulates backlog. Backlog carries across hours and overnight. Fractional agent counts interpolate between integer Erlang results.
- **Forecast accuracy.** WAPE and bias; MAPE shown only for contrast.
- **Cross-training (S2).** {p.flex_share*100:.0f}% of available agents may move to the other queue in an hour if their own queue stays at or below target occupancy and the other cannot clear its demand; they are {p.flex_aht_penalty*100:.0f}% slower there.
- **Scenarios** (`src/scenarios.py`): S1 re-rosters existing headcount with a rolling-corrected forecast using only prior days' actuals (tested for no look-ahead); S3/S4 add a 17:00-22:00 shift; S5 = S1+S2+S4; S6 = S2+S4. **Monte Carlo:** {c.R['mc_replications']} replications re-draw the whole world; scenarios within a replication share demand and absences.

## 4. Validation performed

- **{len(list(c.R.get('tests', [])) ) or 'Automated'} tests** (`pytest`): hand-calculated staffing; Erlang B/C known values; monotonicity; contact conservation through the queue; WAPE/bias hand calculation; roster rules; flex-penalty exactness; absence-lottery monotonicity; no look-ahead; accounting identities; the workload-variance identity; determinism; reproduction of committed data; RACI has one accountable owner per activity.
- **Mutation check:** the core formulas (shrinkage, WAPE, capacity, Erlang C, flex penalty, S1 look-ahead, absence lottery) were deliberately broken one at a time in a scratch copy; the tests failed for each. Two initial survivors led to a stronger flex test and a corrected mutation.
- **Not validated:** the simulation against any real data. That is impossible here by design.

## 5. Calibration log (what I changed after seeing results)

This matters for honesty: some parameters were adjusted *after* a first run, so the case study's story is partly a function of calibration.

| # | First run | Problem seen | Change | Alternatives rejected |
|---|---|---|---|---|
| 1 | Single 18% shrinkage; planner ignored expected absence | Baseline week SLA only 49-87%, so event-week degradation could not be attributed to the event | Split shrinkage into 12% non-absence + planned absence allowance (planned shrinkage {p.planned_shrinkage:.3f}) | - |
| 2 | 5% planning buffer; roster over-cover weight 0.35 | Baseline still short in places; Order & Delivery queue collapsed from E2 onward and never recovered (degenerate: no scenario could be compared) | Buffer 10%, over-cover weight 0.15 (planner-policy parameters) | Variants that softened the *demand-side* drivers (stock-out contacts, delay contacts) were tested and **rejected** as they tune the outcome rather than planner behaviour |
| 3 | Scenarios S0-S4 | S1 showed no effect and the queue imbalance was visible | Added S4 (targeted capacity, same hours as S3) and S6 (ablation) **post hoc** to separate effects | - |
| 4 | Planned-vs-actual table included returns initiated | Same-day plan vs lagged returns was a timing artifact, not a variance | Removed that row | - |

Even after calibration, the event-week outcome varies a lot by seed (event SLA p10-p90 for the as-planned case: {c.mcs_i.loc['S0','sla_overall_p10']*100:.0f}-{c.mcs_i.loc['S0','sla_overall_p90']*100:.0f}%), which is why scenarios are reported as Monte Carlo ranges.

## 6. Limitations

1. **Synthetic by construction.** Planted features (forecast bias, lags, stock-outs, absence spike, deal drops) make the results *properties of the assumptions*, not discoveries about e-commerce operations.
2. **Simplified staffing maths.** Steady-state hour; single shrinkage and occupancy constants; per-hour integer rounding; no intra-hour burstiness, abandonment, callbacks, breaks scheduling, skills routing or multichannel differences.
3. **Queue approximations.** Erlang C assumes Poisson arrivals, exponential service and infinite patience; fractional agents are interpolated; the fluid model approximates overload. Backlog is never abandoned and carries overnight.
4. **Causation.** SLA is generated from staffing and load, so correlation analyses demonstrate method, not causal proof.
5. **Scenario scope.** No training or hiring cost and lead time, overtime premiums, attrition or morale effects; paid agent-hours are the only cost proxy. Cross-training shows an upper-bound-style benefit for that reason. S3 vs S4 differences are small relative to run-to-run spread.
6. **Single event, 14 days, two queues.** Returns after E7 are outside the window. Sensitivity analysis on key parameters (absence, bias, AHT) is not yet done.
7. **Planner behaviour is assumed.** Rosters are built by a rule, not by real planners with judgement and constraints.

## 7. Reproduce

```bash
pip install -r requirements.txt
python -m src.run_pipeline      # data, analysis, scenarios, charts, risk register (about 30 s)
python -m src.build_docs        # regenerates the docs from the outputs
python -m pytest -q             # tests
streamlit run dashboard/app.py  # optional dashboard
```
"""


def portfolio(c) -> str:
    p, H = c.p, c.H
    m = c.mcs_i
    ats = pd.DataFrame([
        ("E-commerce Operations", "Simulated order, exception, cancellation, return and contact workflows", "`data/orders_daily.csv`, `operational_events_log.csv`", "Supported (simulated, not professional experience)"),
        ("Program Management", "Charter, milestones, status report, decisions log, RACI", "`docs/01`, `05`, `06`, `08`", "Supported as documents; no real programme delivered"),
        ("Workforce Management / WFM", "Requirement, rostering, absence, scheduled vs available", "`staffing_hourly.csv`, `src/calc.py`", "Supported (simulated)"),
        ("Demand Forecasting", "Rate-based forecast built and evaluated against actuals", "`A2_forecast_accuracy.csv`", "Supported at a basic level (no time-series modelling)"),
        ("Capacity Planning", "Workload to agents, gaps by queue-hour, scenarios", "`B*` and `E*` tables", "Supported"),
        ("Staffing Gaps", "Shortfall and surplus agent-hours by queue and hour", "`B1`, `B2`, `B3` tables", "Supported"),
        ("SLA Management", "SLA, response time and backlog monitoring, thresholds, escalation", "`C*` tables, `07` Control", "Supported (modelled SLA)"),
        ("KPI Reporting / Operational Reporting", "KPI dictionary, daily tables, dashboard, status report", "`docs/02`, `05`, dashboard", "Supported"),
        ("Forecast Accuracy", "WAPE and bias with rationale", "`A2`", "Supported"),
        ("Variance Analysis", "Planned vs actual, ranked, volume vs AHT decomposition", "`D1`, `D2`, `B5`", "Supported"),
        ("Resource Utilization", "Occupancy, shrinkage, load ratio", "`02` KPI dictionary", "Supported (assumption-based)"),
        ("Risk Management / Dependency Tracking", "Prioritised register with owners, triggers; dependency tracker", "`04`, `04b`", "Supported"),
        ("Root Cause Analysis", "Causes tied to modelled evidence", "`07` Analyze", "Supported (simulated)"),
        ("Process Improvement / Six Sigma DMAIC", "Simulated DMAIC with DPMO and control plan", "`07`", "Supported (simulated; complements Yellow Belt badge)"),
        ("Stakeholder Coordination", "Hypothetical RACI and communication plan only", "`06`, `05`", "**Do not claim from this project.** Your real coordination experience is the SimplyPhi internship"),
    ], columns=["ATS term", "What the project actually does", "Evidence", "Status"])
    return f"""# 10 - Portfolio Summary

{BANNER}

## Project description (short)

An independent case study that simulates how a hypothetical online retailer prepares customer support for a seven-day sale. Using fully synthetic data, it forecasts demand, translates it into required, scheduled and available staffing by queue and hour, tracks SLA, backlog and handling time, and compares seven mitigation scenarios with Monte Carlo modelling. It is documented as a program: charter, KPI dictionary, risk and dependency registers, RACI, status report, executive readout and a simulated Six Sigma DMAIC. Built with Python (Pandas, NumPy, SciPy, Matplotlib), Streamlit and pytest; every figure is reproducible from a fixed seed.

## CV bullets (truthful, ATS-friendly)

- Built an independent, simulation-based e-commerce peak-season capacity-planning case study (Python, Pandas, NumPy, SciPy, Matplotlib, Streamlit) on a fully synthetic dataset for a hypothetical retailer, analysing demand forecast accuracy (WAPE, bias), required vs scheduled vs available staffing, and SLA, backlog and handling-time trends to identify staffing gaps by queue and hour.
- Authored program-management artifacts (project charter, KPI dictionary, prioritised risk and dependency registers, RACI, status report, executive readout) and applied a simulated Six Sigma DMAIC analysis comparing seven mitigation scenarios through Monte Carlo modelling, with documented assumptions, limitations and automated tests; all outcomes labelled as modelled estimates.

*Shorter variant (if space is tight):* Built a synthetic-data e-commerce peak-season workforce capacity-planning case study (Python, Pandas, Streamlit): forecast accuracy, staffing-gap and SLA analysis, scenario modelling, risk register and Six Sigma DMAIC; independent project, no real company data.

## Honest framing for interviews

- **Say:** "This is an independent simulation I built to learn WFM and peak-season planning. The data is synthetic, so the findings illustrate method, not real results."
- **Strongest transferable points:** separating forecast error by category and hour instead of trusting the total; noticing that a balanced weekly total hid hourly and cross-queue gaps; testing a lever (reallocation) that did *not* help and reporting that; showing ranges instead of single numbers; being explicit about what the model cannot say.
- **Do not say:** that it improved SLA, saved cost or raised productivity; that it reflects Amazon (or any real company's) operations; that you have professional WFM or e-commerce operations experience; that the Six Sigma work was a real engagement.
- **If asked "what would you do next with real data?":** validate the forecast by category on historical peaks, measure real shrinkage/occupancy/AHT by queue, test cross-skilling feasibility, and add cost and lead-time to scenarios.

## ATS term alignment (only where the work supports it)

{md_table(ats, None, None, {k: str for k in ats.columns})}

## Key facts (generated from the outputs)

- Event week: {num(H['event_orders_total'])} orders; SLA {pct(H['event_week_sla_pct'])} vs {p.sla_target*100:.0f}% target; baseline week {pct(H['baseline_week_sla_pct'])}.
- Best modelled option (S6): mean event SLA {m.loc['S6','sla_overall_mean']*100:.1f}% (p10-p90 {m.loc['S6','sla_overall_p10']*100:.0f}-{m.loc['S6','sla_overall_p90']*100:.0f}%) vs {m.loc['S0','sla_overall_mean']*100:.1f}% as planned. *Modelled estimate on synthetic data; do not quote on a CV as an achieved improvement.*
"""


def readme(c) -> str:
    p, H, E, m = c.p, c.H, c.E, c.mcs_i
    return f"""# E-commerce Peak-Season Operations & Workforce Capacity Planning: Case Study

{BANNER}

An end-to-end, reproducible simulation of how an online retailer's support operation prepares for a 7-day sale: demand forecasting, workforce capacity, SLA monitoring, risk and dependency management, mitigation scenarios and a simulated Six Sigma DMAIC. Built as an independent portfolio project to demonstrate e-commerce operations and workforce-management analysis. **The author has no professional e-commerce operations or WFM experience; this project does not claim any.**

## Business context (hypothetical)

NorthBay Mart runs a "Winter Mega Sale" ({c.event_start} to {c.event_end}) after a baseline week. Customer contacts split into two skill queues: **Order & Delivery** (order status, delivery delay, cancel/modify) and **Returns, Payments & Product**. Support runs 07:00-23:00 on three 8-hour shift templates. Target: {p.sla_target*100:.0f}% of contacts answered within {p.sla_threshold_sec} seconds.

## Findings (all on SIMULATED data; properties of the stated assumptions)

1. **A reasonable total forecast hid a poor category mix.** Event contact forecast WAPE {pct(E['contact_wape_event'])} (bias {pct(E['contact_bias_event'], sign=True)}) in total, but Order & Delivery workload was {pct(E['od_workload_var_pct'], 0, True)} vs forecast while the other queue ended with {num(E['rp_surplus_hours'])} surplus agent-hours. Order & Delivery had enough agent-hours over the week yet was short in {E['od_understaffed_hours']} of 112 hours.
2. **Service failed a day *after* the trigger.** Launch day E1 met SLA; E2 collapsed (stock-outs and exceptions create contacts 1-2 days later), and the finale E7 closed with the largest backlog. Event-week SLA {pct(H['event_week_sla_pct'])} vs {p.sla_target*100:.0f}% target; {H['days_meeting_target']} of 7 days on target.
3. **Where capacity sits matters more than how much.** Modelled over {c.R['mc_replications']} replications: reshaping rosters inside existing shifts changed SLA by {m.loc['S1','paired_delta_sla_mean']*100:+.1f} pp; cross-training {m.loc['S2','paired_delta_sla_mean']*100:+.1f} pp; the same extra hours spread evenly {m.loc['S3','paired_delta_sla_mean']*100:+.1f} pp vs targeted at the bottleneck queue {m.loc['S4','paired_delta_sla_mean']*100:+.1f} pp (*modelled estimates*; training cost unmodelled).

## Repository layout

```
data/        synthetic datasets (CSV) + assumptions.csv + operational_events_log.csv
src/         config, generator, calculations, queue simulation, analysis, scenarios, risk, charts, doc builders
analysis/    analysis tables (A-E), results.json, charts/*.png
docs/        01-10 deliverables (charter, KPI dictionary, analysis, risk register, status, RACI, DMAIC, readout, methodology, portfolio)
tests/       pytest unit and integration tests
dashboard/   Streamlit dashboard
```

## Run it

```bash
pip install -r requirements.txt
python -m src.run_pipeline      # generates data, analysis, scenarios (Monte Carlo), charts, risk register (~30 s)
python -m src.build_docs        # regenerates docs/*.md and this README from the outputs
python -m pytest -q             # run tests
streamlit run dashboard/app.py  # optional dashboard
```

Everything is deterministic for the seed in `src/config.py` (seed {p.seed}). Changing any assumption and re-running regenerates data, tables, charts and documents consistently.

## Methodology in brief

Orders and exceptions drive contacts (with lags); contacts x handling time give workload; required agents = workload / ((1 - shrinkage) x occupancy); rosters are built from the forecast; absences are drawn from a shared lottery; an hourly queue model (Erlang C when stable, fluid queue when overloaded, backlog carried over) produces SLA, response time and backlog. Forecast accuracy uses WAPE and bias. Scenarios are compared with paired Monte Carlo replications. Full detail, a calibration log and limitations: `docs/09_Methodology_and_Limitations.md`.

## Key assumptions

All {len(c.R['params'])} parameters, with unit, basis and rationale, are in `data/assumptions.csv`. Headline ones: shrinkage {p.shrinkage*100:.0f}% (+ absence), target occupancy {p.target_occupancy*100:.0f}%, planning buffer {p.planning_buffer*100:.0f}%, baseline absence {p.baseline_absence_rate*100:.0f}%, SLA {p.sla_target*100:.0f}/{p.sla_threshold_sec}s, fulfilment capacity {num(p.fulfilment_capacity_orders_per_day)} orders/day.

## Limitations (summary)

Synthetic by construction; planted effects mean findings illustrate method rather than reveal reality; simplified staffing and queue maths; correlation between shortfall and SLA is built in; no training/hiring cost or lead time; single 14-day event; some parameters were calibrated after a first run (documented). See `docs/09_Methodology_and_Limitations.md`.

## Documents

| File | Purpose |
|---|---|
| `docs/01_Project_Charter.md` | Objectives, scope, stakeholders, milestones, success criteria |
| `docs/02_KPI_Dictionary.md` | Metric definitions and formulas |
| `docs/03_Operational_Analysis.md` | Demand, capacity, SLA, variance and scenario findings |
| `docs/04_Risk_and_Mitigation_Register.csv` (+ `04b_Dependency_Tracker.csv`) | Prioritised risks, owners, dependencies, triggers |
| `docs/05_Program_Status_Report.md` | Weekly status |
| `docs/06_RACI_Matrix.csv` | Hypothetical responsibilities |
| `docs/07_Six_Sigma_DMAIC.md` | Simulated DMAIC |
| `docs/08_Executive_Readout.md` | Leadership summary and decisions |
| `docs/09_Methodology_and_Limitations.md` | Assumptions, limits, reproducibility |
| `docs/10_Portfolio_Summary.md` | Project description and CV bullets |
"""
