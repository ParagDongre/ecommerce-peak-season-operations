"""Risk register, dependency tracker and RACI (HYPOTHETICAL roles; SIMULATED evidence).

Probability and impact are scored 1-5. Where a risk has quantitative evidence in the simulation,
the score is derived from it with the explicit rules below; otherwise it is flagged as judgement.

Probability rule (evidence-based risks): share of Monte Carlo replications in which the risk
materialised  ->  <10%:1, 10-30%:2, 30-50%:3, 50-75%:4, >=75%:5.
Impact rule: stated per risk next to its metric.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import DATA_LABEL, Params


def prob_score(share: float) -> int:
    return 1 if share < 0.10 else 2 if share < 0.30 else 3 if share < 0.50 else 4 if share < 0.75 else 5


def rating(score: int) -> str:
    return "Critical" if score >= 20 else "High" if score >= 12 else "Medium" if score >= 6 else "Low"


def mc_materialisation(mc_s0: pd.DataFrame, p: Params) -> dict:
    """Share of Monte Carlo replications (as-planned scenario S0) in which each risk materialised."""
    return {
        "sla_below_target": float((mc_s0.sla_overall < p.sla_target).mean()),
        "end_backlog": float((mc_s0.end_of_event_backlog_contacts > 50).mean()),
        "worst_day_below_60": float((mc_s0.worst_day_sla < 0.60).mean()),
        "sla_OD_below_target": float((mc_s0.sla_OD < p.sla_target).mean()),
        "ge3_days_miss": float((mc_s0.days_meeting_sla_target <= 4).mean()),
    }


def build_register(p: Params, ev: dict, mc_s0: pd.DataFrame, key_dates: dict) -> pd.DataFrame:
    """ev: evidence numbers from the analysis (see run_pipeline). key_dates: hypothetical calendar anchors."""
    mat = mc_materialisation(mc_s0, p)
    E1 = pd.Timestamp(key_dates["event_start"])
    due = lambda days: (E1 + pd.Timedelta(days=days)).strftime("%Y-%m-%d")
    R = []

    def add(rid, title, cat, evidence, prob, prob_basis, impact, impact_basis, owner, mitig, scen, dep, due_date, trigger):
        R.append({
            "risk_id": rid, "risk": title, "category": cat, "evidence_from_simulation": evidence,
            "probability_1to5": prob, "probability_basis": prob_basis, "impact_1to5": impact, "impact_basis": impact_basis,
            "score": prob * impact, "rating": rating(prob * impact), "owner_role": owner, "mitigation_action": mitig,
            "linked_scenario": scen, "dependencies": dep, "due_date": due_date, "escalation_trigger": trigger,
            "status": "Open (hypothetical)", "data_label": DATA_LABEL,
        })

    add("R01", "Contact-mix forecast error: Order & Delivery workload under-forecast while Returns/Payments is over-planned",
        "Forecast / planning",
        f"Event-week OD workload {ev['od_workload_var_pct']:+.0f}% vs forecast; RP {ev['rp_workload_var_pct']:+.0f}%; "
        f"OD queue short in {ev['od_understaffed_hours']} group-hours while RP carries {ev['rp_surplus_hours']:.0f} surplus agent-hours",
        prob_score(mat["sla_OD_below_target"]), f"Computed: OD SLA below target in {mat['sla_OD_below_target']*100:.0f}% of replications",
        5, "OD queue is the bottleneck in the as-planned scenario; see evidence column for magnitude",
        "Workforce Planning Lead", "Re-forecast by queue using exception/stock-out signals; rebalance headcount between queues; cross-train for flex (S2, S4)",
        "S2, S4, S6", "Operations (exception feed) -> Workforce Planning -> Customer Support Team Leads", due(-7),
        "OD queue SLA < 70% for 2 consecutive hours OR backlog > 100 contacts")
    add("R02", "Delivery-delay contacts lag fulfilment exceptions by 1-2 days and are not in the order-based forecast",
        "Forecast / dependency",
        f"Exceptions peaked at {ev['peak_exceptions']:,} on {ev['peak_exceptions_day']}; delivery_delay contacts rose {ev['delay_uplift_pct']:+.0f}% vs baseline avg day",
        4, "Judgement: mechanism built into the simulation (1-2 day lag); materialises whenever exceptions spike",
        4, "Drives the largest category-level forecast miss",
        "Operations Program Manager", "Daily exception-count feed to WFM; apply lagged contact-rate model to next-day forecast",
        "S1 (rolling correction)", "Fulfilment Ops -> Workforce Planning (daily data handoff by 10:00)", due(-5),
        "Late-shipment count > 2x baseline-day average OR carrier-disruption notice")
    add("R03", "Unscheduled evening deal drops shift intraday demand to 20:00-21:59",
        "Forecast / marketing dependency",
        f"Event-week contacts at 20:00-21:59 {ev['eve_hour_error_pct']:+.0f}% vs forecast profile; deal days: {', '.join(ev['deal_days'])}",
        3, "Judgement: 3 deal-drop days in 7", 3, "Evening hours short but total headcount near balance",
        "Marketing Operations Liaison", "Require 72-hour notice of deal drops; add peak-cover shift (S3/S4)",
        "S3, S4", "Marketing -> Workforce Planning (promo calendar sign-off)", due(-10),
        "Deal not on approved promo calendar 24 h before launch")
    add("R04", "Unplanned absence spike during the event",
        "Capacity / supply",
        f"Absence assumed {p.event_absence_rate[2]*100:.0f}% on E3 vs {p.baseline_absence_rate*100:.0f}% baseline; realised event-week absence "
        f"{ev['event_absence_pct']:.1f}% of scheduled shifts",
        3, "Judgement: event-day absence is an assumption in the model", 3, "Each 1 pt of absence ~ 1 agent per 100 scheduled",
        "Customer Support Operations Manager", "Standby/flex pool; overtime and shift-swap protocol; cross-training (S2)",
        "S2, S3", "HR/Scheduling -> Customer Support -> Workforce Planning", due(-3),
        "Same-day absence > 10% of scheduled shifts")
    add("R05", "Shift-template mismatch: single late template covers the 19:00 peak while mid-day overlaps over-cover",
        "Capacity / roster design",
        f"Highest shortfall hours (event, OD): {ev['top_short_hours']}; reallocation within templates changed SLA by {ev['s1_delta_pp']:+.1f} pp (MC mean)",
        4, "Judgement: structural to the template set", 2, "Template reshaping is a limited lever; see evidence column for the modelled S1 effect",
        "Workforce Planning Lead", "Add shifted-start templates / split shifts; evaluate before event",
        "S1 (shows limits), S3/S4", "Workforce Planning -> HR/Scheduling (new shift agreements)", due(-14),
        "Shortfall in same hour on 3 consecutive days")
    add("R06", "Backlog carry-over snowball: overnight backlog is not cleared before next day's peak",
        "Service",
        f"As-planned: end-of-event backlog > 50 contacts in {mat['end_backlog']*100:.0f}% of replications; peak backlog {ev['peak_backlog']:.0f} contacts",
        prob_score(mat["end_backlog"]), f"Computed: {mat['end_backlog']*100:.0f}% of replications", 4, "Backlog means repeat contacts and customer wait",
        "Customer Support Operations Manager", "Targeted overflow capacity at OD evening peak (S4); morning recovery roster",
        "S4, S5", "Customer Support -> Workforce Planning (recovery plan trigger)", due(-5),
        "End-of-day backlog > 150 contacts")
    add("R07", "Promotion-driven AHT inflation not in plan",
        "Capacity / process",
        f"Actual AHT {ev['aht_var_pct']:+.1f}% vs planned across the event week",
        4, "Judgement: modelled +5% complexity factor", 2, "Modest per day, compounds with volume error",
        "Customer Support Quality Lead", "Macro/FAQ updates for promo rules; track AHT daily; update planning AHT",
        "-", "Customer Support -> Workforce Planning (AHT refresh)", due(-4),
        "Daily AHT > 8% over plan")
    add("R08", "Siloed skill queues prevent moving spare capacity to the bottleneck",
        "Capacity / skills",
        f"RP queue had {ev['rp_surplus_hours']:.0f} surplus agent-hours while OD was short; cross-training lifts modelled SLA by {ev['s2_delta_pp']:+.1f} pp (MC mean)",
        prob_score(mat["sla_below_target"]), f"Computed: event SLA below target in {mat['sla_below_target']*100:.0f}% of replications",
        4, "Largest single modelled lever on OD SLA",
        "Customer Support Training Manager", "Cross-train 20% of agents (training time not modelled)", "S2, S5, S6",
        "Training -> Customer Support -> Workforce Planning (certification before E1)", due(-14),
        "Cross-trained headcount < 15% at T-7 days")
    add("R09", "Upstream fulfilment capacity exceeded / carrier disruption inflates exceptions",
        "Dependency (Operations)",
        f"Orders exceeded fulfilment capacity on {ev['over_capacity_days']}; carrier disruption days E4-E5",
        4, "Judgement: modelled capacity limit is breached on peak days", 3, "Feeds R02",
        "Fulfilment Operations Manager", "Pre-position inventory; carrier contingency; early customer comms",
        "-", "Fulfilment Ops -> Customer Support (proactive comms) -> Workforce Planning", due(-10),
        "Orders > 95% of fulfilment capacity forecast OR carrier SLA breach")
    add("R10", "Approval lead time for additional capacity",
        "Dependency / governance",
        f"S3/S4 need approved extra agents ({ev['extra_hours']:.0f} extra paid agent-hours in the model)",
        3, "Judgement: approvals commonly lag planning", 4, "Without approval, S3/S4/S5/S6 cannot be executed",
        "Program Manager (WFM)", "Submit capacity request with scenario evidence by T-14; agree decision date",
        "S3, S4, S5, S6", "Finance/Leadership approval -> Workforce Planning -> HR", due(-14),
        "No decision by T-10 days")
    add("R11", "Forecast refresh cadence too slow to react in-event",
        "Process / reporting",
        f"Event-week contact forecast WAPE {ev['contact_wape_event']:.1f}% (bias {ev['contact_bias_event']:+.1f}%)",
        3, "Judgement", 3, "Late detection lengthens recovery",
        "Workforce Planning Analyst", "Twice-daily forecast vs actual review; rolling correction rule (S1)",
        "S1", "Workforce Planning <-> Operations reporting", due(-2),
        "Cumulative day-to-date contact error > +/-10%")
    add("R12", "Late-event agent fatigue raises absence on E6-E7 (finale peak)",
        "Capacity / people",
        f"Absence assumed {p.event_absence_rate[5]*100:.0f}% on E6-E7 vs {p.baseline_absence_rate*100:.0f}% baseline; E7 is the highest-demand day",
        3, "Judgement: model assumption", 4, "Coincides with the highest volume",
        "Customer Support Operations Manager", "Rotate shifts, cap overtime, plan recovery days",
        "S2, S3", "Customer Support -> HR", due(-3),
        "Overtime > 10% of scheduled hours on any day")
    df = pd.DataFrame(R).sort_values(["score", "impact_1to5"], ascending=False).reset_index(drop=True)
    df.insert(0, "priority_rank", np.arange(1, len(df) + 1))
    return df


def dependency_tracker(key_dates: dict) -> pd.DataFrame:
    E1 = pd.Timestamp(key_dates["event_start"])
    d = lambda k: (E1 + pd.Timedelta(days=k)).strftime("%Y-%m-%d")
    rows = [
        ("D01", "Operations (Fulfilment)", "Workforce Planning", "Daily late-shipment/exception counts by 10:00", "R02, R09", d(-5), "Open"),
        ("D02", "Operations (Inventory)", "Customer Support", "Stock-out alerts for promo items (>= 24 h notice)", "R02", d(-5), "Open"),
        ("D03", "Marketing", "Workforce Planning", "Approved promo calendar incl. deal drops (72 h notice)", "R03", d(-10), "Open"),
        ("D04", "Workforce Planning", "Customer Support", "Corrected daily roster by 14:00 for next day", "R01, R11", d(-1), "Open"),
        ("D05", "Customer Support Training", "Workforce Planning", "Cross-trained agent certification list", "R08", d(-14), "Open"),
        ("D06", "Finance / Leadership", "Workforce Planning", "Approval of additional peak-cover capacity", "R10", d(-14), "Open"),
        ("D07", "HR / Scheduling", "Customer Support", "Absence reporting same-day by 08:00; shift-swap protocol", "R04, R12", d(-3), "Open"),
        ("D08", "Customer Support", "Workforce Planning", "Daily AHT and backlog actuals", "R06, R07", d(0), "Open"),
        ("D09", "Workforce Planning", "Leadership", "Daily SLA/backlog status and escalation notes", "R06, R11", d(0), "Open"),
    ]
    df = pd.DataFrame(rows, columns=["dependency_id", "provider", "consumer", "deliverable", "linked_risks", "needed_by", "status"])
    df["data_label"] = DATA_LABEL
    return df


def raci() -> pd.DataFrame:
    roles = ["Program Manager (WFM)", "Workforce Planning Lead", "Workforce Planning Analyst", "Customer Support Ops Manager",
             "Customer Support Training Manager", "Fulfilment Ops Manager", "Marketing Ops Liaison", "Finance / Leadership Sponsor", "HR / Scheduling"]
    # R=Responsible, A=Accountable, C=Consulted, I=Informed (exactly one A per row)
    table = [
        ("Define charter, scope and success criteria", "R", "C", "I", "C", "I", "C", "C", "A", "I"),
        ("Order and contact demand forecast by queue", "A", "R", "R", "C", "I", "C", "C", "I", "I"),
        ("Staffing requirement and roster plan", "C", "A", "R", "C", "I", "I", "I", "I", "C"),
        ("Daily forecast-vs-actual and variance review", "A", "R", "R", "C", "I", "C", "I", "I", "I"),
        ("Daily exception and stock-out feed", "C", "I", "I", "I", "I", "A", "I", "I", "I"),
        ("Promo calendar and deal-drop notice", "C", "C", "I", "I", "I", "C", "A", "I", "I"),
        ("Cross-training programme", "C", "C", "I", "R", "A", "I", "I", "I", "C"),
        ("Additional-capacity request and approval", "R", "C", "C", "C", "I", "I", "I", "A", "C"),
        ("Absence management and shift swaps", "I", "C", "I", "A", "I", "I", "I", "I", "R"),
        ("SLA, backlog monitoring and escalation", "A", "C", "R", "R", "I", "I", "I", "I", "I"),
        ("Risk and dependency register upkeep", "A", "C", "R", "C", "I", "C", "C", "I", "I"),
        ("Weekly status report and executive readout", "A", "C", "R", "C", "I", "I", "I", "I", "I"),
        ("DMAIC control plan ownership", "A", "R", "R", "R", "I", "I", "I", "I", "I"),
    ]
    df = pd.DataFrame(table, columns=["activity"] + roles)
    df["data_label"] = f"{DATA_LABEL} / HYPOTHETICAL roles (R=Responsible, A=Accountable, C=Consulted, I=Informed)"
    return df
