"""Compact Streamlit dashboard for the SIMULATED peak-season case study.

Run from the project root:   streamlit run dashboard/app.py
Reads the CSVs produced by `python -m src.run_pipeline` (no calculations are re-implemented here
beyond simple filtering and threshold flags).
"""
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DATA, AN, DOCS = ROOT / "data", ROOT / "analysis", ROOT / "docs"
SLA_TARGET = 80.0

st.set_page_config(page_title="Peak-Season Ops & WFM (Simulated)", layout="wide")


@st.cache_data
def read(path: str) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


if not (AN / "results.json").exists():
    st.error("Outputs not found. Run `python -m src.run_pipeline` from the project root first.")
    st.stop()

dd = read(str(AN / "A1_demand_daily_summary.csv"))
mix = read(str(AN / "A3_contact_mix_by_category.csv"))
fa = read(str(AN / "A2_forecast_accuracy.csv"))
hp = read(str(AN / "A5_hourly_profile_event.csv"))
cap_d = read(str(AN / "B1_capacity_daily_by_group.csv"))
svc = read(str(AN / "C1_service_daily_by_group.csv"))
svc_t = read(str(AN / "C2_service_daily_total.csv"))
gap_tab = read(str(AN / "C3_sla_by_shortfall_size.csv"))
mcs = read(str(AN / "E2_scenario_monte_carlo_summary.csv"))
staffing = read(str(DATA / "staffing_hourly.csv"))
service = read(str(DATA / "service_hourly.csv"))
reg = read(str(DOCS / "04_Risk_and_Mitigation_Register.csv"))
dep = read(str(DOCS / "04b_Dependency_Tracker.csv"))

st.title("E-commerce Peak-Season Operations & Workforce Capacity Planning")
st.warning("SIMULATED DATA for a hypothetical retailer ('NorthBay Mart'). No Amazon or real company data. "
           "Scenario results are modelled estimates, not measured improvements.")

ev_t = svc_t[svc_t.phase == "event"]
base_t = svc_t[svc_t.phase == "baseline"]
wsla = lambda d: (d.sla_attainment_pct * d.contacts).sum() / d.contacts.sum()
ev_hf = staffing[staffing.phase == "event"]

tabs = st.tabs(["Overview", "Demand", "Capacity", "Service levels", "Risk alerts", "Mitigation scenarios"])

with tabs[0]:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Event-week SLA", f"{wsla(ev_t):.1f}%", f"{wsla(ev_t) - SLA_TARGET:+.1f} pp vs {SLA_TARGET:.0f}% target")
    c2.metric("Baseline-week SLA", f"{wsla(base_t):.1f}%")
    c3.metric("Event days on target", f"{int((ev_t.sla_attainment_pct >= SLA_TARGET).sum())} of {len(ev_t)}")
    c4.metric("Understaffed group-hours", f"{int(ev_hf.understaffed.sum())} of {len(ev_hf)}")
    c5.metric("Backlog at close of E7", f"{ev_t.end_of_day_backlog_contacts.iloc[-1]:.0f} contacts")
    st.subheader("Daily SLA attainment (all contacts)")
    st.line_chart(svc_t.set_index("day_label")[["sla_attainment_pct"]])
    st.caption("Event days are E1-E7; B1-B7 is the baseline week. SLA = share of contacts answered within 300 s, arrival-weighted.")
    st.subheader("Daily summary")
    st.dataframe(dd[["day_label", "forecast_orders", "actual_orders", "order_error_pct", "forecast_contacts", "actual_contacts", "contact_error_pct", "peak_hour"]], hide_index=True)

with tabs[1]:
    st.subheader("Orders: forecast vs actual")
    st.bar_chart(dd.set_index("day_label")[["forecast_orders", "actual_orders"]])
    st.subheader("Contacts: forecast vs actual")
    st.line_chart(dd.set_index("day_label")[["forecast_contacts", "actual_contacts"]])
    st.subheader("Hourly contacts, average event day: forecast vs actual")
    st.line_chart(hp.set_index("hour")[["baseline_avg_contacts", "event_forecast_avg_contacts", "event_avg_contacts"]])
    st.subheader("Contact drivers by issue category")
    st.dataframe(mix[["label", "baseline_avg_daily", "event_avg_daily", "uplift_pct", "event_share_pct", "cumulative_event_share_pct"]], hide_index=True)
    st.subheader("Forecast accuracy (WAPE and bias; negative bias = under-forecast)")
    st.dataframe(fa[["level", "scope", "actual_total", "forecast_total", "wape_pct", "bias_pct"]], hide_index=True)
    st.caption("WAPE is the primary metric (volume-weighted, stable at low-volume hours). Baseline-week accuracy is in-sample.")

with tabs[2]:
    c1, c2 = st.columns(2)
    q = c1.selectbox("Queue", ["OD", "RP"], format_func=lambda x: {"OD": "Order & Delivery", "RP": "Returns, Payments & Product"}[x])
    d = c2.selectbox("Day", list(staffing.day_label.unique()), index=8)
    x = staffing[(staffing.skill_group == q) & (staffing.day_label == d)].set_index("hour")
    st.subheader(f"Required vs scheduled vs available agents: {q}, {d}")
    st.line_chart(x[["required_actual", "scheduled", "available"]])
    st.caption("Required = agents needed present for the actual workload; shortfall = required - available.")
    st.subheader("Event-week capacity by day and queue (agent-hours)")
    ce = cap_d[cap_d.phase == "event"]
    st.dataframe(ce[["day_label", "skill_group", "required_actual_agent_hours", "available_agent_hours", "understaffed_hours", "max_shortfall_agents", "shortfall_agent_hours", "surplus_agent_hours"]], hide_index=True)
    st.bar_chart(ce.pivot(index="day_label", columns="skill_group", values="shortfall_agent_hours"))
    st.caption("Gross shortfall per day. Surplus on one day or in the other queue cannot offset it.")

with tabs[3]:
    st.subheader("Daily SLA by queue")
    st.line_chart(svc[svc.phase.isin(["baseline", "event"])].pivot(index="day_label", columns="skill_group", values="sla_attainment_pct").loc[svc.day_label.unique()])
    st.subheader("End-of-day backlog by queue (contacts)")
    st.bar_chart(svc.pivot(index="day_label", columns="skill_group", values="end_of_day_backlog_contacts").loc[svc.day_label.unique()])
    st.subheader("SLA by staffing shortfall size (event week)")
    st.dataframe(gap_tab[gap_tab.analysis == "overall"][["gap_bin", "group_hours", "mean_sla_pct", "share_hours_below_target_pct", "mean_response_sec", "mean_end_backlog"]], hide_index=True)
    st.info("Association, not proven causation: in this simulation SLA is generated from staffing and load by a queue model, so the link is built in.")

with tabs[4]:
    st.subheader("Control-plan alerts (event week, thresholds from docs/07_Six_Sigma_DMAIC.md)")
    ev_s = svc[svc.phase == "event"].copy()
    ev_s["alert"] = ""
    ev_s.loc[ev_s.sla_attainment_pct < 70, "alert"] += "SLA<70%  "
    ev_s.loc[ev_s.sla_attainment_pct < 60, "alert"] += "RED day  "
    ev_s.loc[ev_s.end_of_day_backlog_contacts > 100, "alert"] += "Backlog>100  "
    alerts = ev_s[ev_s.alert != ""][["day_label", "skill_group", "sla_attainment_pct", "end_of_day_backlog_contacts", "hours_below_sla_target", "alert"]]
    st.dataframe(alerts, hide_index=True)
    st.subheader("Hours with 3+ agents short (escalation: same hour on 3 consecutive days)")
    big = ev_hf[ev_hf.capacity_gap_agents >= 3].groupby(["skill_group", "hour"]).day_label.apply(lambda s: ", ".join(s)).reset_index(name="days")
    big["n_days"] = big.days.str.count(",") + 1
    st.dataframe(big.sort_values("n_days", ascending=False), hide_index=True)
    st.subheader("Prioritised risk register")
    st.dataframe(reg[["priority_rank", "risk_id", "risk", "probability_1to5", "impact_1to5", "score", "rating", "owner_role", "due_date", "escalation_trigger"]], hide_index=True)
    st.subheader("Cross-team dependencies")
    st.dataframe(dep[["dependency_id", "provider", "consumer", "deliverable", "linked_risks", "needed_by"]], hide_index=True)

with tabs[5]:
    st.subheader("Modelled event-week SLA by scenario (200 Monte Carlo replications)")
    show = mcs[["scenario", "description", "sla_overall_mean", "sla_overall_p10", "sla_overall_p90", "paired_delta_sla_mean", "sla_OD_mean", "end_backlog_mean", "days_meeting_target_mean", "extra_paid_agent_hours"]].copy()
    for col in ("sla_overall_mean", "sla_overall_p10", "sla_overall_p90", "paired_delta_sla_mean", "sla_OD_mean"):
        show[col] = (show[col] * 100).round(1)
    show["end_backlog_mean"] = show["end_backlog_mean"].round(0)
    show["days_meeting_target_mean"] = show["days_meeting_target_mean"].round(1)
    show = show.rename(columns={"sla_overall_mean": "mean SLA %", "sla_overall_p10": "p10 %", "sla_overall_p90": "p90 %", "paired_delta_sla_mean": "change vs S0 (pp)", "sla_OD_mean": "OD SLA %"})
    st.dataframe(show, hide_index=True)
    st.bar_chart(show.set_index("scenario")[["mean SLA %"]])
    st.warning("MODELLED ESTIMATES on simulated data. Training cost/lead time, hiring and overtime effects are not modelled; "
               "p10-p90 ranges overlap between neighbouring scenarios.")
