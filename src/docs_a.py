"""Docs 01 (charter), 02 (KPI dictionary), 03 (operational analysis), 05 (status report)."""
from __future__ import annotations

import pandas as pd

from .docs_common import BANNER, md_table, num, pct


def charter(c) -> str:
    p, H, E, m = c.p, c.H, c.E, c.mcs_i
    top = c.reg.head(5)
    return f"""# 01 - Project Charter: E-commerce Peak-Season Operations & Workforce Capacity Planning

{BANNER}

| | |
|---|---|
| **Business (hypothetical)** | NorthBay Mart, an online retailer running a 7-day "Winter Mega Sale" ({c.event_start} to {c.event_end}) |
| **Sponsor / PM (hypothetical roles)** | Finance / Leadership Sponsor; Program Manager (WFM) |
| **Status** | Simulated exercise, fully reproducible from seed {p.seed} |

## 1. The charter at a glance: eight questions

| Question | Answer (all figures SIMULATED) |
|---|---|
| **What is the operational problem?** | The support plan, built from an order-based forecast, does not hold service levels in the event week. Event-week SLA is {pct(H['event_week_sla_pct'])} against an {p.sla_target*100:.0f}% target (baseline week {pct(H['baseline_week_sla_pct'])}); only {H['days_meeting_target']} of {p.n_event_days} event days meet target. |
| **What evidence supports it?** | Contact forecast WAPE {pct(E['contact_wape_event'])} (bias {pct(E['contact_bias_event'], sign=True)}) at daily-total level hides category errors of up to {pct(c.fa[c.fa.level.str.startswith('contacts by category')].wape_pct.max(), 0)}. Order & Delivery (OD) workload ran {pct(E['od_workload_var_pct'], 0, True)} above forecast; the Returns/Payments/Product (RP) queue ended with {num(E['rp_surplus_hours'])} surplus agent-hours. See `03_Operational_Analysis.md`. |
| **What is the impact on service and capacity?** | {H['understaffed_group_hours_event']} of {H['group_hours_event']} event group-hours were understaffed (available agents below requirement). Worst day {H['worst_sla_day']} at {pct(H['worst_sla_pct'])} SLA; backlog at close of E7: {num(H['end_backlog_E7'])} contacts. |
| **What decisions are needed?** | (1) Approve targeted extra peak-cover capacity (+{num(m.loc['S4','extra_paid_agent_hours'])} paid agent-hours). (2) Approve cross-training of {p.flex_share*100:.0f}% of agents. (3) Adopt a by-queue, lag-aware forecast and a daily re-forecast rule. See `08_Executive_Readout.md`. |
| **Who owns each mitigation?** | See `04_Risk_and_Mitigation_Register.csv` (owner per action) and `06_RACI_Matrix.csv`. |
| **Dependencies and deadlines?** | See `04b_Dependency_Tracker.csv`; capacity approval and cross-training certification are needed by {pd.Timestamp(c.event_start) - pd.Timedelta(days=14):%Y-%m-%d} (T-14 days). |
| **What could prevent success?** | Approval lead time (R10), cross-training not certified in time (R08), late exception/promo data hand-offs (R02, R03), and the model itself: assumptions, not observations (see `09_Methodology_and_Limitations.md`). |
| **How is success measured and verified?** | Section 5 below: KPI targets, owners, data source and verification step. |

## 2. Objectives

1. Forecast event demand (orders and customer contacts) and quantify forecast accuracy.
2. Translate demand into required staffing, compare it with scheduled and available staffing, and quantify capacity gaps.
3. Monitor SLA, backlog, response time and handling time; identify when and why service deteriorates.
4. Compare at least three mitigation options with transparent, labelled-as-modelled estimates.
5. Package the work as program-management artifacts: risk register, dependency tracker, RACI, status report, executive readout, DMAIC.

## 3. Scope

**In scope:** daily orders and exceptions; hourly contacts by six issue categories in two skill queues; hourly required/scheduled/available staffing; hourly SLA, response time, backlog; absences; mitigation scenarios; documentation.

**Out of scope:** real company data; cost/financial modelling (only paid agent-hours are tracked); hiring lead times and training cost; omnichannel routing, abandonment and callbacks; individual agent attributes; post-event returns tail beyond E7.

## 4. Stakeholders (hypothetical roles)

| Role | Interest | Engagement |
|---|---|---|
| Finance / Leadership Sponsor | Approves capacity; wants SLA risk and trade-offs | Executive readout, decision log |
| Program Manager (WFM) | Owns plan, risks, status and escalation | Daily stand-up during event |
| Workforce Planning Lead / Analyst | Forecast, requirement, rosters | Daily re-forecast |
| Customer Support Ops Manager / Training Manager | Execution, absence, cross-training | Daily SLA/backlog review |
| Fulfilment Ops Manager | Exceptions and stock-outs that drive contacts | Daily data feed |
| Marketing Ops Liaison | Promo calendar and deal drops | 72-hour notice |
| HR / Scheduling | Shift agreements, absence process | Weekly sync |

## 5. Success criteria and verification (targets for the *simulated* operation)

| Criterion | Target | Verified by | Owner | Modelled as-planned result |
|---|---|---|---|---|
| Event-week SLA attainment | >= {p.sla_target*100:.0f}% | `C2_service_daily_total.csv`; dashboard | Customer Support Ops Manager | {pct(H['event_week_sla_pct'])} (single seed); {pct(m.loc['S0','sla_overall_mean']*100)} mean across {c.R['mc_replications']} replications |
| Event days meeting SLA target | >= 6 of 7 | same | Customer Support Ops Manager | {H['days_meeting_target']} of 7 (single seed) |
| End-of-day backlog | <= 100 contacts any day | `C1_service_daily_by_group.csv` | Customer Support Ops Manager | {num(H['end_backlog_E7'])} at close of E7 |
| Contact forecast accuracy by queue | WAPE <= 10% at queue-hour | `A2_forecast_accuracy.csv` | Workforce Planning Lead | OD {pct(c.fa_i.loc[('contacts by skill group (hourly)','event: OD'),'wape_pct'])}, RP {pct(c.fa_i.loc[('contacts by skill group (hourly)','event: RP'),'wape_pct'])} |
| Understaffed group-hours | trending down vs plan | `B1_capacity_daily_by_group.csv` | Workforce Planning Lead | {H['understaffed_group_hours_event']} of {H['group_hours_event']} |
| Risks with owner and due date | 100% of High/Critical | `04_Risk_and_Mitigation_Register.csv` | Program Manager (WFM) | All {len(c.reg)} risks assigned |

## 6. Milestones (hypothetical calendar; E1 = {c.event_start})

| When | Milestone | Owner |
|---|---|---|
| T-21 | Baseline week analysed; contact rates and profile learned | Workforce Planning Analyst |
| T-14 | Capacity request and cross-training plan submitted with scenario evidence | Program Manager (WFM) |
| T-10 | Promo calendar (incl. deal drops) signed off | Marketing Ops Liaison |
| T-7 | Rosters published; cross-trained agents certified | Workforce Planning Lead / Training Manager |
| T-1 | Go/no-go: dependencies D01-D09 confirmed | Program Manager (WFM) |
| E1-E7 | Daily forecast-vs-actual, SLA and backlog review; escalation per triggers | Customer Support Ops Manager |
| T+7 | Post-event review; control plan handover | Program Manager (WFM) |

## 7. Top risks (full register in `04_Risk_and_Mitigation_Register.csv`)

{md_table(top, ['risk_id','risk','score','rating','owner_role','due_date'], {'risk':'Risk','score':'Score','rating':'Rating','owner_role':'Owner (role)','due_date':'Due','risk_id':'ID'})}

Scoring: probability x impact, each 1-5. Where probability is computed from the Monte Carlo runs the register says so; otherwise it is labelled judgement.

## 8. Assumptions and constraints

All modelling assumptions are in `data/assumptions.csv` ({len(c.R['params'])} parameters, each with unit, basis and rationale). The planted features of the scenario (forecast bias, lagged contact drivers, stock-outs, absence spike) are design choices; they make the case study analytically interesting and are **not** findings about any real business.
"""


def kpi_dictionary(c) -> str:
    p = c.p
    rows = [
        ("Orders (forecast / actual)", "Orders placed per day: planner forecast vs simulated actual", "-", "orders/day", "`orders_daily.csv`", "Demand level and trend. Event days are shown as multiples of the baseline-week average."),
        ("Order growth", "Day-over-day change in actual orders", "(Orders_t / Orders_t-1 - 1) x 100", "%", "`orders_daily.csv`", "Launch jump and finale peak."),
        ("Fulfilment exception rate", "Late shipments + failed deliveries + damaged/missing, per 100 orders", "exceptions / orders x 100", "%", "`orders_daily.csv`", "Upstream driver of delivery-delay contacts one to two days later."),
        ("Cancellation rate", "Cancellations (all causes) per 100 orders", "cancellations / orders x 100", "%", "`orders_daily.csv`", "Stock-out cancellations drive cancel/modify contacts."),
        ("Return rate", "Returns initiated per 100 orders placed that day", "returns / orders x 100", "%", "`orders_daily.csv`", "Returns arrive 3-9 days after the order, so the rate on a day mixes earlier orders."),
        ("Customer contacts", "Contacts arriving in an hour by issue category and skill queue", "-", "contacts", "`contacts_hourly.csv`", "Workload driver. Two queues: OD (order status, delay, cancel/modify), RP (returns, payment/promo, product)."),
        ("Contacts per 100 orders", "Contact intensity", "contacts / orders x 100", "contacts", "`A1_demand_daily_summary.csv`", "Rises when exceptions/promo complexity increase."),
        ("WAPE (forecast error)", "Weighted absolute percentage error. **Chosen primary metric**: volume-weighted, stable at low-volume hours where MAPE explodes", f"sum|A-F| / sum A x 100", "%", "`A2_forecast_accuracy.csv`", "Lower is better. Does not show direction, so read with bias."),
        ("Forecast bias", "Signed error; negative = under-forecast", "(sum F - sum A) / sum A x 100", "%", "`A2_forecast_accuracy.csv`", "Direction of the miss. Offsetting errors can make aggregate bias near zero while categories are far off."),
        ("MAPE (contrast only)", "Mean of per-point absolute % error, points with actual < 10 skipped", "mean(|A-F|/A) x 100", "%", "`A2_forecast_accuracy.csv`", "Shown to illustrate why WAPE is preferred."),
        ("Average handling time (AHT)", "Mean agent time per contact (talk + after-contact work)", "workload_seconds / contacts", "seconds", "`contacts_hourly.csv`", "Planned AHT = baseline-week volume-weighted mean; event AHT is higher through a modelled complexity factor."),
        ("Workload hours", "Agent time needed to handle contacts", "contacts x AHT / 3600", "agent-hours", "`staffing_hourly.csv`", "Input to staffing requirement."),
        ("Shrinkage (non-absence)", "Share of present time not on contacts (breaks, coaching, meetings, downtime)", "assumption", f"{p.shrinkage*100:.0f}%", "`assumptions.csv`", "Planner convention, not sourced from any company."),
        ("Planned shrinkage", "Shrinkage used for scheduling = non-absence shrinkage combined with planned absence allowance", f"1 - (1 - {p.shrinkage}) x (1 - {p.baseline_absence_rate}) = {p.planned_shrinkage:.4f}", "fraction", "`assumptions.csv`", "Scheduled-basis requirement."),
        ("Target occupancy", "Planned share of productive time spent on contacts", "assumption", f"{p.target_occupancy*100:.0f}%", "`assumptions.csv`", "Keeps queue stable and SLA attainable."),
        ("Required staffing (agents)", "Agents that must be present (actual basis) or scheduled (planned basis) in an hour", "ceil( workload_hours x (1 + buffer) / ((1 - shrinkage) x occupancy) )", "agents", "`staffing_hourly.csv`", f"Planned requirement uses forecast workload, planned AHT, {p.planning_buffer*100:.0f}% contingency and planned shrinkage. `required_actual` uses actual workload, no buffer, non-absence shrinkage (compare with *available*)."),
        ("Scheduled staffing", "Agents rostered on shift in the hour", "sum of shift-template coverage", "agents", "`staffing_hourly.csv`", "Built by a greedy roster rule against the planned requirement (3 templates, 8-hour shifts)."),
        ("Available staffing", "Scheduled minus absent", "scheduled - absent", "agents", "`staffing_hourly.csv`", "Absence drawn per agent from a shared random lottery."),
        ("Capacity gap", "Positive = shortfall", "required_actual - available", "agents", "`staffing_hourly.csv`", "Hourly, so a surplus at 15:00 cannot offset a shortfall at 19:00."),
        ("Understaffed hour", "Group-hour with capacity gap > 0", "gap > 0", "count", "`staffing_hourly.csv`", "Counts both queues separately (224 group-hours in the event week)."),
        ("Shortfall agent-hours", "Gross sum of positive gaps", "sum max(0, gap)", "agent-hours", "`B1_capacity_daily_by_group.csv`", "Size of the gap. Surplus agent-hours reported separately; net can look balanced while gross is not."),
        ("SLA attainment", "Share of contacts answered within the threshold", f"share with wait <= {p.sla_threshold_sec}s; arrival-weighted when aggregated", "%", "`service_hourly.csv`", f"Target {p.sla_target*100:.0f}%. Modelled, not observed."),
        ("Response time", "Mean wait before an agent picks up", "Erlang C ASA or fluid-queue mean wait (see methodology)", "seconds", "`service_hourly.csv`", "Arrival-weighted when aggregated."),
        ("Backlog", "Contacts waiting at the end of the hour", "backlog_start + arrivals - handled", "contacts", "`service_hourly.csv`", "Carries across hours and overnight."),
        ("Capacity (contacts/hour)", "Contacts the available agents can handle", f"effective agents x {p.max_throughput_occupancy} x 3600 / AHT", "contacts", "`service_hourly.csv`", "Physical throughput ceiling at 95% occupancy."),
        ("Load ratio", "Workload relative to productive agents", "workload_hours / (available x (1 - shrinkage))", "ratio", "`C4_shortfall_sla_correlations.csv`", "> about 0.95 means the queue cannot keep up."),
        ("Absence rate", "Share of scheduled shifts lost to unplanned absence", "absent / scheduled", "%", "`absences_daily.csv`", f"Assumed {p.baseline_absence_rate*100:.0f}% baseline; event-day assumptions in `assumptions.csv`."),
        ("Variance (planned vs actual)", "Actual minus planned and as % of planned", "A - P; (A - P) / P x 100", "unit / %", "`D1_planned_vs_actual_event_days.csv`", "Planned = forecast, plan or target. Ranked in `D2_largest_variances.csv`."),
        ("Volume effect / AHT effect", "Decomposition of workload variance", "(A_c - F_c) x AHT_plan / 3600; A_c x (AHT_act - AHT_plan) / 3600", "agent-hours", "`B5_workload_variance_decomposition.csv`", "Sums exactly to actual minus forecast workload (tested). The AHT effect at queue level also absorbs category-mix shifts within a queue."),
        ("Defect / DPMO / sigma level", "DMAIC measure: a contact not answered within threshold is a defect", "DPMO = defects / contacts x 1e6; sigma = z(1 - defect rate) + 1.5", "-", "`07_Six_Sigma_DMAIC.md`", "Illustrative; uses the conventional 1.5-sigma shift."),
        ("Paid agent-hours", "Rostered hours incl. extra capacity", "sum agents x shift length", "agent-hours", "`E1_scenario_comparison_single_seed.csv`", "Only cost proxy; no currency modelled."),
        ("Risk score", "Probability x impact", "1-5 x 1-5", "1-25", "`04_Risk_and_Mitigation_Register.csv`", "Rating: Critical >= 20, High >= 12, Medium >= 6."),
    ]
    df = pd.DataFrame(rows, columns=["Metric", "Definition", "Formula", "Unit", "Source", "Interpretation / caveat"])
    return f"""# 02 - KPI Dictionary

{BANNER}

All metrics are computed from the simulated datasets by the code in `src/analysis.py`, `src/calc.py` and `src/scenarios.py`.
Hour-level quantities cover operating hours 07:00-22:59 and two skill queues (OD = Order & Delivery; RP = Returns, Payments & Product).

{md_table(df, fmts={k: (lambda v: str(v)) for k in df.columns})}

## Aggregation rules

- **SLA, response time, AHT** are arrival-weighted when rolled up from hours to days/weeks (never a simple average of hourly percentages).
- **Capacity gaps** are computed per group-hour and summed; surplus is never netted against shortfall in the hourly measure.
- **Baseline week** (B1-B7) is used to learn contact rates, the hourly profile and planned AHT, so baseline-week forecast accuracy is in-sample and flattering by design; the event week is out-of-sample.
"""


def operational_analysis(c) -> str:
    p, H, E, m = c.p, c.H, c.E, c.mcs_i
    dd = c.dd.copy()
    ev_dd = dd[dd.phase == "event"]
    fa = c.fa
    cat_fa = fa[fa.level == "contacts by category (daily)"].copy()
    cat_fa["scope"] = cat_fa.scope.str.replace("event: ", "")
    mix = c.mix
    gap, corr = c.gap, c.corr
    overall_gap = gap[gap.analysis == "overall"]
    strat = gap[gap.analysis != "overall"]
    big = c.big.head(10)
    bridge = c.bridge.set_index("skill_group")
    b = lambda g, k: bridge.loc[g][k]
    cap_ev = c.cap_d[c.cap_d.phase == "event"].groupby("skill_group")[["understaffed_hours", "shortfall_agent_hours", "surplus_agent_hours", "available_agent_hours", "required_actual_agent_hours"]].sum().reset_index()
    svc_ev = c.svc[c.svc.phase == "event"].pivot(index="day_label", columns="skill_group", values=["sla_attainment_pct", "end_of_day_backlog_contacts", "hours_below_sla_target"])
    svc_tab = pd.DataFrame({
        "Day": svc_ev.index,
        "OD SLA %": svc_ev[("sla_attainment_pct", "OD")].values, "RP SLA %": svc_ev[("sla_attainment_pct", "RP")].values,
        "OD end backlog": svc_ev[("end_of_day_backlog_contacts", "OD")].values, "OD hours below target": svc_ev[("hours_below_sla_target", "OD")].values,
    })
    epis = c.epis
    ep_n = len(epis)
    ep_short = int(epis.shortfall_within_prior_2_hours_or_start.sum())
    r_same = corr.iloc[0]
    r_load = corr.iloc[4]
    r_dem = corr.iloc[3]
    top_peak = c.peaks.iloc[0]
    wape_ord = fa.set_index(["level", "scope"]).loc[("orders (daily)", "event week"), "wape_pct"]
    return f"""# 03 - Operational Analysis

{BANNER}

All numbers below are produced by `python -m src.run_pipeline` (seed {p.seed}) and read from `analysis/*.csv`. Charts are in `analysis/charts/`.

## A. E-commerce demand

**Orders.** Event orders total {num(H['event_orders_total'])} over {p.n_event_days} days against a baseline-week average of {num(H['baseline_orders_avg'])} orders/day. The peak is {H['peak_orders_day']} at {num(H['peak_orders'])} orders ({H['peak_orders_vs_baseline_x']:.1f}x baseline). Launch (E1) and finale (E7) are the order peaks; E4 is the trough (see table).

![Orders forecast vs actual](../analysis/charts/01_orders_forecast_vs_actual.png)

{md_table(ev_dd, ['day_label','forecast_orders','actual_orders','order_error_pct','forecast_contacts','actual_contacts','contact_error_pct','contacts_per_100_orders','peak_hour'], {'day_label':'Day','forecast_orders':'Forecast orders','actual_orders':'Actual orders','order_error_pct':'Order error %','forecast_contacts':'Forecast contacts','actual_contacts':'Actual contacts','contact_error_pct':'Contact error %','contacts_per_100_orders':'Contacts / 100 orders','peak_hour':'Peak hour'}, {'forecast_orders':lambda v:num(v),'actual_orders':lambda v:num(v),'forecast_contacts':lambda v:num(v),'actual_contacts':lambda v:num(v),'order_error_pct':lambda v:f'{v:+.1f}','contact_error_pct':lambda v:f'{v:+.1f}','contacts_per_100_orders':lambda v:f'{v:.1f}','peak_hour':lambda v:f'{int(v):02d}:00'})}

(Error % = (actual - forecast) / forecast; positive = under-forecast.)

**Peak hours.** The single busiest hour is {top_peak.day_label} {int(top_peak.hour):02d}:00 with {int(top_peak.actual_contacts)} contacts, {top_peak.error_pct:+.0f}% against forecast. Contacts concentrate in the evening (18:00-21:00) and the evening hour error on deal-drop days drives the intraday miss (20:00-21:59 contacts {E['eve_hour_error_pct']:+.0f}% vs forecast across the event week).

![Contacts heatmap](../analysis/charts/02_contacts_hourly_heatmap_event.png)

**Forecast accuracy.** Chosen metric: **WAPE** (sum of absolute errors / sum of actuals), reported with **bias**. WAPE is volume-weighted and stays stable at low-volume hours where MAPE explodes (see `A2_forecast_accuracy.csv` for both). Event-week orders WAPE is {pct(wape_ord)}. Event-week daily-total contacts WAPE is {pct(E['contact_wape_event'])} with bias {pct(E['contact_bias_event'], sign=True)}.

The daily total looks tolerable but hides larger, offsetting category errors:

{md_table(cat_fa, ['scope','actual_total','forecast_total','wape_pct','bias_pct'], {'scope':'Category (event week)','actual_total':'Actual','forecast_total':'Forecast','wape_pct':'WAPE %','bias_pct':'Bias %'}, {'actual_total':lambda v:num(v),'forecast_total':lambda v:num(v),'wape_pct':lambda v:f'{v:.1f}','bias_pct':lambda v:f'{v:+.1f}'})}

Returns are *over*-forecast because the forecast applies a same-day contact rate while returns arrive 3-9 days after the order; delivery-delay, payment/promo and product contacts are *under*-forecast because they rise with exceptions, promo codes and event complexity that the baseline-week rates do not contain. Baseline-week accuracy is in-sample (rates learned from that week), so only the event week is a fair test.

![Forecast error](../analysis/charts/04_forecast_error_event.png)

**Contact drivers.** Order status is the largest category, but delivery delay, payment/promo and cancel/modify grew fastest.

{md_table(mix, ['label','baseline_avg_daily','event_avg_daily','uplift_pct','event_share_pct','cumulative_event_share_pct'], {'label':'Issue category','baseline_avg_daily':'Baseline avg/day','event_avg_daily':'Event avg/day','uplift_pct':'Uplift %','event_share_pct':'Share of event contacts %','cumulative_event_share_pct':'Cumulative %'}, {'baseline_avg_daily':lambda v:num(v),'event_avg_daily':lambda v:num(v),'uplift_pct':lambda v:f'{v:+.0f}','event_share_pct':lambda v:f'{v:.1f}','cumulative_event_share_pct':lambda v:f'{v:.1f}'})}

![Contact mix](../analysis/charts/03_contact_mix_by_category.png)

## B. Workforce capacity

**Method.** Required agents per queue-hour = workload hours x (1 + {p.planning_buffer*100:.0f}% buffer) / ((1 - planned shrinkage {p.planned_shrinkage:.3f}) x occupancy {p.target_occupancy}), rounded up. Rosters are built from the *forecast* requirement using three 8-hour shift templates (07-15, 11-19, 15-23). *Available* = scheduled minus simulated absences. Gap = actual present-basis requirement - available.

{md_table(cap_ev, ['skill_group','required_actual_agent_hours','available_agent_hours','understaffed_hours','shortfall_agent_hours','surplus_agent_hours'], {'skill_group':'Queue','required_actual_agent_hours':'Required (actual) agent-h','available_agent_hours':'Available agent-h','understaffed_hours':'Understaffed hours (of 112)','shortfall_agent_hours':'Shortfall agent-h (gross)','surplus_agent_hours':'Surplus agent-h (gross)'}, {'required_actual_agent_hours':lambda v:num(v),'available_agent_hours':lambda v:num(v),'understaffed_hours':lambda v:str(int(v)),'shortfall_agent_hours':lambda v:num(v),'surplus_agent_hours':lambda v:num(v)})}

**What the numbers say.**

- **The weekly total hides the problem.** OD had {num(b('OD','7_available_agent_hours'))} available vs {num(b('OD','8_required_present_agent_hours_on_actual_(rounded)'))} required agent-hours (net {b('OD','9_net_surplus_(+)_or_gap_(-)_agent_hours'):+.0f}), yet it was short in {int(cap_ev[cap_ev.skill_group=='OD'].understaffed_hours.iloc[0])} of 112 hours ({num(b('OD','10_hourly_shortfall_agent_hours_(gross)'))} gross agent-hours short), because surplus on calm days and hours cannot be banked for E2, E3, E6 and E7 evenings. Most shortfall sits at {E['top_short_hours']}.
- **The surplus sits in the wrong queue.** RP had {num(b('RP','7_available_agent_hours'))} available vs {num(b('RP','8_required_present_agent_hours_on_actual_(rounded)'))} required ({b('RP','9_net_surplus_(+)_or_gap_(-)_agent_hours'):+.0f} net) because the contact-mix forecast over-called returns and under-called order/delivery workload.
- **Workload variance decomposition** (event week, both queues): actual workload is {c.var_hours:+.0f} agent-hours vs forecast, of which volume explains {c.vol_hours:+.0f} and AHT {c.aht_hours:+.0f} (exact identity, tested). The queue-level AHT effect includes both the modelled complexity factor and the shift toward longer-handling categories within a queue; the two are not separated.

![Capacity shortfall heatmap](../analysis/charts/05_capacity_shortfall_heatmap.png)

![Required vs scheduled vs available](../analysis/charts/06_required_vs_scheduled_vs_available_OD.png)

**Limitations of simplified staffing calculations.** (1) Workload/occupancy maths assumes a stable, steady-state hour; it ignores arrival burstiness within the hour, abandonment and skill-based routing. (2) Shrinkage and occupancy are single constants. (3) Integer rounding per hour inflates requirements at small volumes. (4) Shortfall is measured against the *planner's* occupancy target, not a hard limit. See `09_Methodology_and_Limitations.md`.

## C. Service levels

{md_table(svc_tab, None, None, {'Day':str,'OD SLA %':lambda v:f'{v:.1f}','RP SLA %':lambda v:f'{v:.1f}','OD end backlog':lambda v:num(v),'OD hours below target':lambda v:str(int(v))})}

![SLA and backlog](../analysis/charts/07_sla_and_backlog_daily.png)

**Staffing gaps and service deterioration.** Hours with a shortfall have far worse service than hours without:

{md_table(overall_gap, ['gap_bin','group_hours','mean_sla_pct','share_hours_below_target_pct','mean_response_sec','mean_end_backlog'], {'gap_bin':'Shortfall size','group_hours':'Group-hours','mean_sla_pct':'Mean SLA %','share_hours_below_target_pct':'Hours below target %','mean_response_sec':'Mean response (s)','mean_end_backlog':'Mean end backlog'}, {'group_hours':lambda v:str(int(v)),'mean_sla_pct':lambda v:f'{v:.1f}','share_hours_below_target_pct':lambda v:f'{v:.0f}','mean_response_sec':lambda v:num(v),'mean_end_backlog':lambda v:f'{v:.0f}'})}

![SLA by shortfall bin](../analysis/charts/08_sla_by_shortfall_bin.png)

{ep_short} of the {ep_n} below-target SLA episodes (contiguous below-target hours, `C5_sla_breach_episodes.csv`) began in, or within two hours after, an understaffed hour.

**Correlation is not proven causation.** Spearman rank correlation between shortfall and same-hour SLA is {r_same.spearman_rho:.2f}; between load ratio and SLA {r_load.spearman_rho:.2f}; demand alone vs SLA {r_dem.spearman_rho:.2f}. Two cautions:

1. *Confounding:* shortfalls cluster in high-demand hours, so demand and shortfall move together. The stratified view below compares hours of similar workload with and without a shortfall.
2. *By construction:* SLA here is **generated** by a queue model from staffing and load, so the relationship is built in. In real data you would need a design (e.g. before/after a roster change, or comparison across comparable queues) to argue causation. The scenario runs (section E) are the closest this project gets: same demand, same absences, only staffing changed.

{md_table(strat, ['gap_bin','group_hours','mean_sla_pct','share_hours_below_target_pct'], {'gap_bin':'Workload tercile / shortfall flag','group_hours':'Group-hours','mean_sla_pct':'Mean SLA %','share_hours_below_target_pct':'Hours below target %'}, {'group_hours':lambda v:str(int(v)),'mean_sla_pct':lambda v:f'{v:.1f}','share_hours_below_target_pct':lambda v:f'{v:.0f}'})}

(Metric assumptions: SLA = share of contacts answered within {p.sla_threshold_sec}s, arrival-weighted; response time = Erlang-C ASA or fluid-queue mean wait; backlog carries overnight. See `02_KPI_Dictionary.md`.)

## D. Variance and risk

Largest planned-vs-actual variances in the event week (planned = forecast, plan or SLA target; backlog excluded because its plan is zero):

{md_table(big, ['rank','day_label','metric','planned','actual','variance_pct'], {'rank':'#','day_label':'Day','metric':'Metric','planned':'Planned','actual':'Actual','variance_pct':'Variance %'}, {'rank':lambda v:str(int(v)),'planned':lambda v:num(v,1),'actual':lambda v:num(v,1),'variance_pct':lambda v:f'{v:+.0f}'})}

Fulfilment exceptions dominate the list: orders exceeded the {num(p.fulfilment_capacity_orders_per_day)}/day fulfilment capacity on {E['over_capacity_days']}, and the carrier disruption added exceptions on E4-E5. Those exceptions feed delivery-delay contacts one to two days later, which is why the service collapse follows the exceptions rather than coinciding with them (E1 launch day held SLA; E2 did not).

![Workload variance decomposition](../analysis/charts/10_workload_variance_decomposition.png)

**Risk register.** {len(c.reg)} risks, ranked by probability x impact, are in `04_Risk_and_Mitigation_Register.csv`, with owner, mitigation, linked scenario, dependencies, due date and escalation trigger. Cross-team dependencies between Operations, Workforce Planning and Customer Support are in `04b_Dependency_Tracker.csv`.

## E. Mitigation scenarios (MODELLED ESTIMATES)

Single-seed and {c.R['mc_replications']}-replication Monte Carlo results are in `E1_...csv`, `E2_...csv`, `E3_...csv`. Mean and p10-p90 are across replications that each re-draw orders, contacts, handling times and absences; scenarios within a replication share the same demand and absence draws, so differences are paired.

{md_table(c.mcs, ['scenario','description','sla_overall_mean','sla_overall_p10','sla_overall_p90','sla_OD_mean','paired_delta_sla_mean','end_backlog_mean','days_meeting_target_mean','extra_paid_agent_hours'], {'scenario':'ID','description':'Scenario','sla_overall_mean':'Mean event SLA %','sla_overall_p10':'p10','sla_overall_p90':'p90','sla_OD_mean':'OD SLA %','paired_delta_sla_mean':'Paired change vs S0 (pp)','end_backlog_mean':'End backlog','days_meeting_target_mean':'Days meeting target (of 7)','extra_paid_agent_hours':'Extra paid agent-h'}, {'sla_overall_mean':lambda v:f'{v*100:.1f}','sla_overall_p10':lambda v:f'{v*100:.1f}','sla_overall_p90':lambda v:f'{v*100:.1f}','sla_OD_mean':lambda v:f'{v*100:.1f}','paired_delta_sla_mean':lambda v:f'{v*100:+.1f}','end_backlog_mean':lambda v:f'{v:.0f}','days_meeting_target_mean':lambda v:f'{v:.1f}','extra_paid_agent_hours':lambda v:num(v)})}

![Scenario comparison](../analysis/charts/09_scenario_comparison.png)

**Reading the scenarios (all modelled; none is a measured gain):**

- **S1 reallocation** (same headcount, re-shaped across the three shift templates using a rolling-corrected forecast): paired change {m.loc['S1','paired_delta_sla_mean']*100:+.1f} pp, better than S0 in {m.loc['S1','share_reps_better_than_S0']*100:.0f}% and worse in {m.loc['S1','share_reps_worse_than_S0']*100:.0f}% of replications (by more than 0.5 pp). With so few shift shapes and a fixed headcount, the surplus is in the *other queue* and *other days*, which this lever cannot reach.
- **S2 cross-training** ({p.flex_share*100:.0f}% of agents, {p.flex_aht_penalty*100:.0f}% slower on the other queue): {m.loc['S2','paired_delta_sla_mean']*100:+.1f} pp at no extra paid hours. Training time and cost are **not** modelled, so this overstates net benefit.
- **S3 / S4 extra peak-cover capacity** (+{num(m.loc['S3','extra_paid_agent_hours'])} paid agent-hours; evenly split vs all to OD): {m.loc['S3','paired_delta_sla_mean']*100:+.1f} pp vs {m.loc['S4','paired_delta_sla_mean']*100:+.1f} pp. Same cost, targeting the bottleneck queue is worth about {(m.loc['S4','paired_delta_sla_mean']-m.loc['S3','paired_delta_sla_mean'])*100:.1f} pp more; the p10-p90 ranges overlap, so treat the difference as indicative.
- **S5 vs S6** isolate S1 inside the combined option: {m.loc['S5','sla_overall_mean']*100:.1f}% vs {m.loc['S6','sla_overall_mean']*100:.1f}% mean SLA, so reallocation adds nothing measurable on top of cross-training and targeted capacity.
- Single-seed results (`E1_scenario_comparison_single_seed.csv`) are one draw of the same model and differ from the Monte Carlo means; prefer the Monte Carlo view.
"""


def status_report(c) -> str:
    p, H, E, m = c.p, c.H, c.E, c.mcs_i
    ev = c.svc_t[c.svc_t.phase == "event"]
    rag = lambda sla: "RED" if sla < 60 else "AMBER" if sla < p.sla_target * 100 else "GREEN"
    day_rows = pd.DataFrame({"Day": ev.day_label, "SLA %": ev.sla_attainment_pct, "RAG": [rag(x) for x in ev.sla_attainment_pct],
                             "Understaffed group-hours": ev.understaffed_group_hours, "End backlog": ev.end_of_day_backlog_contacts})
    red = [d for d, x in zip(ev.day_label, ev.sla_attainment_pct) if x < 60]
    top = c.reg.head(4)
    return f"""# 05 - Program Status Report (weekly)

{BANNER}

**Report period:** event week E1-E7 ({c.event_start} to {c.event_end}), status as of close of E7. **Prepared by:** Program Manager (WFM), hypothetical. **Data:** simulated, seed {p.seed}.

## Overall status: **RED** for service levels; AMBER for plan execution

| Area | Status | Summary |
|---|---|---|
| Service levels | RED | Event-week SLA {pct(H['event_week_sla_pct'])} vs {p.sla_target*100:.0f}% target; {len(red)} days below 60% ({', '.join(red)}). |
| Capacity | RED | {H['understaffed_group_hours_event']} of {H['group_hours_event']} group-hours understaffed; OD short {num(E['od_shortfall_hours'])} gross agent-hours while RP carried {num(E['rp_surplus_hours'])} surplus. |
| Forecast | AMBER | Daily-total contact WAPE {pct(E['contact_wape_event'])} (bias {pct(E['contact_bias_event'], sign=True)}); category WAPE up to {pct(c.fa[c.fa.level.str.startswith('contacts by category')].wape_pct.max(), 0)}. |
| Risks and dependencies | AMBER | {len(c.reg)} risks logged, {int((c.reg.rating.isin(['Critical','High'])).sum())} High/Critical; {len(c.dep)} dependencies tracked. |
| Schedule | GREEN | Milestones T-21 to T+7 on plan (hypothetical). |

## Key metrics

{md_table(day_rows, None, None, {'Day':str,'SLA %':lambda v:f'{v:.1f}','RAG':str,'Understaffed group-hours':lambda v:str(int(v)),'End backlog':lambda v:num(v)})}

## Accomplished

- Built the synthetic dataset, analysis pipeline and dashboard; {len(c.R['params'])} assumptions documented.
- Quantified forecast accuracy (WAPE/bias), capacity gaps and the shortfall-to-SLA relationship.
- Compared {len(c.mcs)} scenarios across {c.R['mc_replications']} Monte Carlo replications (modelled estimates).
- Produced risk register, dependency tracker, RACI, DMAIC and executive readout.

## Issues and variances

1. **Launch day looked healthy, then service broke on E2.** E1 SLA was {ev.sla_attainment_pct.iloc[0]:.0f}% but E2 {ev.sla_attainment_pct.iloc[1]:.0f}%: stock-out cancellations and exceptions on E1-E2 create contacts 1-2 days later that the order-based forecast does not contain.
2. **The finale (E7) ended with the largest backlog** ({ev.sla_attainment_pct.iloc[6]:.0f}% SLA, {num(H['end_backlog_E7'])} contacts carried; lowest-SLA day was {H['worst_sla_day']} at {H['worst_sla_pct']:.0f}%): orders {c.dd[c.dd.day_label=='E7'].order_error_pct.iloc[0]:+.0f}% vs forecast, {num(c.orders[c.orders.day_label=='E7'].fulfilment_exceptions.iloc[0])} fulfilment exceptions, evening deal drop.
3. **Queue imbalance.** Spare RP capacity could not help OD without cross-skilling.

## Top risks (owner / due / escalation trigger)

{md_table(top, ['risk_id','risk','score','owner_role','due_date','escalation_trigger'], {'risk_id':'ID','risk':'Risk','score':'Score','owner_role':'Owner (role)','due_date':'Due','escalation_trigger':'Escalation trigger'})}

## Decisions needed

| # | Decision | Decision owner | Needed by |
|---|---|---|---|
| 1 | Approve +{num(m.loc['S4','extra_paid_agent_hours'])} paid agent-hours of peak-cover capacity targeted at OD | Finance / Leadership Sponsor | {pd.Timestamp(c.event_start) - pd.Timedelta(days=14):%Y-%m-%d} |
| 2 | Approve cross-training of {p.flex_share*100:.0f}% of agents (training cost not yet estimated) | Customer Support Training Manager / Sponsor | {pd.Timestamp(c.event_start) - pd.Timedelta(days=14):%Y-%m-%d} |
| 3 | Adopt by-queue, lag-aware forecast with daily re-forecast and escalation triggers | Workforce Planning Lead | {pd.Timestamp(c.event_start) - pd.Timedelta(days=7):%Y-%m-%d} |

## Next steps (next 7 days)

1. Run the post-event review and agree the control plan (`07_Six_Sigma_DMAIC.md`, Control).
2. Estimate cross-training cost and lead time (currently unmodelled).
3. Re-run scenarios with sensitivity ranges for absence and forecast bias.
4. Hand daily exception/stock-out feeds to Workforce Planning (dependencies D01-D02).

## Dependencies and deadlines

{md_table(c.dep, ['dependency_id','provider','consumer','deliverable','needed_by'], {'dependency_id':'ID','provider':'Provider','consumer':'Consumer','deliverable':'Deliverable','needed_by':'Needed by'})}
"""
