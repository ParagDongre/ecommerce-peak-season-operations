"""Demand, capacity, service-level and variance analysis on the SIMULATED datasets (pandas)."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from . import calc
from .config import CATEGORIES, CATEGORY_LABELS, DATA_LABEL, GROUP_LABELS, Params

KEYS = ["date", "hour", "skill_group"]


def _wavg(x: pd.Series, w: pd.Series) -> float:
    return float((x * w).sum() / w.sum()) if w.sum() > 0 else np.nan


def hourly_frame(staffing: pd.DataFrame, service: pd.DataFrame) -> pd.DataFrame:
    """Join staffing and service tables at (date, hour, skill_group)."""
    sv = service.drop(columns=["day_index", "day_label", "phase", "data_label", "aht_sec"])
    return staffing.merge(sv, on=KEYS, how="inner")


# ------------------------------------------------------------------ A. demand -----------
def demand_daily(orders: pd.DataFrame, contacts: pd.DataFrame) -> pd.DataFrame:
    d = contacts.groupby(["day_index", "day_label", "phase", "date"], sort=True).agg(
        forecast_contacts=("forecast_contacts", "sum"), actual_contacts=("actual_contacts", "sum")
    ).reset_index()
    hr = contacts.groupby(["date", "hour"], as_index=False)["actual_contacts"].sum()
    idx = hr.groupby("date")["actual_contacts"].idxmax()
    peak = hr.loc[idx].rename(columns={"hour": "peak_hour", "actual_contacts": "peak_hour_contacts"})
    d = d.merge(peak, on="date")
    d = d.merge(
        orders[["date", "weekday", "forecast_orders", "actual_orders", "order_growth_dod_pct",
                "orders_vs_baseline_avg", "fulfilment_exceptions", "cancellations", "returns_initiated"]],
        on="date",
    )
    d["order_error_pct"] = ((d.actual_orders - d.forecast_orders) / d.forecast_orders * 100).round(2)
    d["contact_error_pct"] = ((d.actual_contacts - d.forecast_contacts) / d.forecast_contacts * 100).round(2)
    d["contacts_per_100_orders"] = (d.actual_contacts / d.actual_orders * 100).round(2)
    d["forecast_contacts"] = d.forecast_contacts.round(1)
    d["peak_hour_share_pct"] = (d.peak_hour_contacts / d.actual_contacts * 100).round(1)
    d["data_label"] = DATA_LABEL
    cols = ["date", "day_index", "day_label", "phase", "weekday", "forecast_orders", "actual_orders", "order_error_pct",
            "order_growth_dod_pct", "orders_vs_baseline_avg", "forecast_contacts", "actual_contacts", "contact_error_pct",
            "contacts_per_100_orders", "peak_hour", "peak_hour_contacts", "peak_hour_share_pct",
            "fulfilment_exceptions", "cancellations", "returns_initiated", "data_label"]
    return d[cols]


def forecast_accuracy(orders: pd.DataFrame, contacts: pd.DataFrame, staffing: pd.DataFrame) -> pd.DataFrame:
    rows = []

    def add(level, scope, a, f, note="", with_mape=False):
        a, f = np.asarray(a, float), np.asarray(f, float)
        rows.append({"level": level, "scope": scope, "n_points": len(a), "actual_total": round(float(a.sum()), 1),
                     "forecast_total": round(float(f.sum()), 1), "wape_pct": round(calc.wape(a, f) * 100, 2),
                     "bias_pct": round(calc.bias(a, f) * 100, 2),
                     "mape_pct": round(calc.mape(a, f, 10) * 100, 2) if with_mape else np.nan, "note": note})

    for ph, g in [("all days", orders), ("baseline week", orders[orders.phase == "baseline"]),
                  ("event week", orders[orders.phase == "event"])]:
        add("orders (daily)", ph, g.actual_orders, g.forecast_orders)
    cd = contacts.groupby(["date", "phase"], as_index=False)[["actual_contacts", "forecast_contacts"]].sum()
    for ph, g in [("all days", cd), ("baseline week", cd[cd.phase == "baseline"]), ("event week", cd[cd.phase == "event"])]:
        add("contacts (daily total)", ph, g.actual_contacts, g.forecast_contacts,
            "baseline week is in-sample (rates learned from it)" if ph != "event week" else "out-of-sample")
    ch = contacts.groupby(["date", "hour", "phase"], as_index=False)[["actual_contacts", "forecast_contacts"]].sum()
    for ph, g in [("baseline week", ch[ch.phase == "baseline"]), ("event week", ch[ch.phase == "event"])]:
        add("contacts (hourly total)", ph, g.actual_contacts, g.forecast_contacts, "MAPE shown for contrast only", True)
    ev = contacts[contacts.phase == "event"]
    for c in CATEGORIES:
        g = ev[ev.issue_category == c].groupby("date", as_index=False)[["actual_contacts", "forecast_contacts"]].sum()
        add("contacts by category (daily)", f"event: {c}", g.actual_contacts, g.forecast_contacts)
    for sg in ("OD", "RP"):
        g = staffing[(staffing.phase == "event") & (staffing.skill_group == sg)]
        add("contacts by skill group (hourly)", f"event: {sg}", g.actual_contacts, g.forecast_contacts, "", True)
    return pd.DataFrame(rows)


def contact_mix(contacts: pd.DataFrame) -> pd.DataFrame:
    base_days = contacts[contacts.phase == "baseline"].date.nunique()
    ev_days = contacts[contacts.phase == "event"].date.nunique()
    t = contacts.groupby(["issue_category", "phase"])["actual_contacts"].sum().unstack()
    out = pd.DataFrame({
        "issue_category": t.index,
        "label": [CATEGORY_LABELS[c] for c in t.index],
        "baseline_avg_daily": (t["baseline"] / base_days).round(1).values,
        "event_avg_daily": (t["event"] / ev_days).round(1).values,
        "event_total": t["event"].values,
    })
    out["event_share_pct"] = (out.event_total / out.event_total.sum() * 100).round(2)
    out["uplift_avg_daily"] = (out.event_avg_daily - out.baseline_avg_daily).round(1)
    out["uplift_pct"] = ((out.event_avg_daily / out.baseline_avg_daily - 1) * 100).round(1)
    out["share_of_total_uplift_pct"] = (out.uplift_avg_daily / out.uplift_avg_daily.sum() * 100).round(2)
    out = out.sort_values("event_total", ascending=False).reset_index(drop=True)
    out["cumulative_event_share_pct"] = out.event_share_pct.cumsum().round(2)
    out["rank_by_event_contacts"] = np.arange(1, len(out) + 1)
    out["data_label"] = DATA_LABEL
    return out


def contacts_by_category_daily(contacts: pd.DataFrame) -> pd.DataFrame:
    t = contacts.pivot_table(index=["date", "day_label", "phase"], columns="issue_category", values="actual_contacts", aggfunc="sum")
    t = t[list(CATEGORIES)].reset_index()
    t["total"] = t[list(CATEGORIES)].sum(axis=1)
    t["data_label"] = DATA_LABEL
    return t


def hourly_profile_event(contacts: pd.DataFrame) -> pd.DataFrame:
    g = contacts.groupby(["phase", "hour"])["actual_contacts"].sum().unstack(0)
    nb = contacts[contacts.phase == "baseline"].date.nunique()
    ne = contacts[contacts.phase == "event"].date.nunique()
    out = pd.DataFrame({"hour": g.index, "baseline_avg_contacts": (g["baseline"] / nb).round(1).values,
                        "event_avg_contacts": (g["event"] / ne).round(1).values})
    ev = contacts[contacts.phase == "event"].groupby("hour")[["actual_contacts", "forecast_contacts"]].sum()
    out["event_forecast_avg_contacts"] = (ev.forecast_contacts.values / ne).round(1)
    out["event_hour_error_pct"] = ((out.event_avg_contacts - out.event_forecast_avg_contacts) / out.event_forecast_avg_contacts * 100).round(1)
    out["data_label"] = DATA_LABEL
    return out


def peak_hours(contacts: pd.DataFrame, top: int = 10) -> pd.DataFrame:
    h = contacts.groupby(["date", "day_label", "hour"], as_index=False)[["actual_contacts", "forecast_contacts"]].sum()
    h["forecast_contacts"] = h.forecast_contacts.round(1)
    h["error_pct"] = ((h.actual_contacts - h.forecast_contacts) / h.forecast_contacts * 100).round(1)
    out = h.sort_values("actual_contacts", ascending=False).head(top).reset_index(drop=True)
    out.insert(0, "rank", np.arange(1, len(out) + 1))
    out["data_label"] = DATA_LABEL
    return out


# ------------------------------------------------------------------ B. capacity ---------
def capacity_daily(hf: pd.DataFrame, p: Params) -> pd.DataFrame:
    g = hf.groupby(["date", "day_label", "phase", "skill_group"], sort=False)
    out = g.apply(lambda x: pd.Series({
        "planned_required_agent_hours": x.required_planned.sum(),
        "scheduled_agent_hours": x.scheduled.sum(),
        "available_agent_hours": x.available.sum(),
        "required_actual_agent_hours": x.required_actual.sum(),
        "understaffed_hours": int((x.capacity_gap_agents > 0).sum()),
        "max_shortfall_agents": int(max(0, x.capacity_gap_agents.max())),
        "shortfall_agent_hours": float(np.maximum(0, x.capacity_gap_agents).sum()),
        "surplus_agent_hours": float(np.maximum(0, -x.capacity_gap_agents).sum()),
    }), include_groups=False).reset_index()
    out["net_gap_agent_hours"] = out.required_actual_agent_hours - out.available_agent_hours
    out["pct_hours_understaffed"] = (out.understaffed_hours / hf.hour.nunique() * 100).round(1)
    out["data_label"] = DATA_LABEL
    return out


def capacity_by_hour_event(hf: pd.DataFrame) -> pd.DataFrame:
    ev = hf[hf.phase == "event"]
    out = ev.groupby(["skill_group", "hour"]).agg(
        mean_required_actual=("required_actual", "mean"), mean_scheduled=("scheduled", "mean"),
        mean_available=("available", "mean"), days_understaffed=("understaffed", "sum"),
        shortfall_agent_hours=("capacity_gap_agents", lambda s: float(np.maximum(0, s).sum())),
        surplus_agent_hours=("capacity_gap_agents", lambda s: float(np.maximum(0, -s).sum())),
    ).round(2).reset_index()
    out["data_label"] = DATA_LABEL
    return out


def understaffed_ranked(hf: pd.DataFrame, top: int = 25) -> pd.DataFrame:
    ev = hf[(hf.phase == "event") & (hf.capacity_gap_agents > 0)].copy()
    ev["sla_pct"] = (ev.sla_attainment * 100).round(1)
    cols = ["date", "day_label", "hour", "skill_group", "required_actual", "scheduled", "available",
            "capacity_gap_agents", "contacts_arrived", "sla_pct", "response_time_sec", "backlog_end_contacts"]
    out = ev.sort_values(["capacity_gap_agents", "contacts_arrived"], ascending=False)[cols].head(top).reset_index(drop=True)
    out["data_label"] = DATA_LABEL
    return out


def capacity_bridge(hf: pd.DataFrame, p: Params) -> pd.DataFrame:
    """Event-week agent-hour bridge per skill group: forecast requirement -> actual requirement."""
    rows = []
    ev = hf[hf.phase == "event"]
    for g, x in ev.groupby("skill_group"):
        fc_wl = (x.forecast_contacts * x.planned_aht_sec / 3600).sum()
        act_wl = (x.actual_contacts * x.actual_aht_sec / 3600).sum()
        req_f = fc_wl / ((1 - p.planned_shrinkage) * p.target_occupancy)
        rows.append({
            "skill_group": g,
            "1_forecast_workload_hours": round(fc_wl, 1),
            "2_actual_workload_hours": round(act_wl, 1),
            "3_required_agent_hours_on_forecast_(scheduled_basis)": round(req_f, 1),
            "4_planned_required_agent_hours_(incl_buffer_and_hourly_rounding)": float(x.required_planned.sum()),
            "5_scheduled_agent_hours": float(x.scheduled.sum()),
            "6_absence_agent_hours_lost": float((x.scheduled - x.available).sum()),
            "7_available_agent_hours": float(x.available.sum()),
            "8_required_present_agent_hours_on_actual_(rounded)": float(x.required_actual.sum()),
            "9_net_surplus_(+)_or_gap_(-)_agent_hours": float(x.available.sum() - x.required_actual.sum()),
            "10_hourly_shortfall_agent_hours_(gross)": float(np.maximum(0, x.capacity_gap_agents).sum()),
            "11_hourly_surplus_agent_hours_(gross)": float(np.maximum(0, -x.capacity_gap_agents).sum()),
            "data_label": DATA_LABEL,
        })
    return pd.DataFrame(rows)


def workload_variance(hf: pd.DataFrame) -> pd.DataFrame:
    """Actual - forecast workload hours = volume effect (at planned AHT) + AHT effect (on actual volume). Exact identity."""
    x = hf.copy()
    x["fc_wl"] = x.forecast_contacts * x.planned_aht_sec / 3600
    x["act_wl"] = x.actual_contacts * x.actual_aht_sec / 3600
    x["vol_eff"] = (x.actual_contacts - x.forecast_contacts) * x.planned_aht_sec / 3600
    x["aht_eff"] = x.actual_contacts * (x.actual_aht_sec - x.planned_aht_sec) / 3600
    out = x.groupby(["date", "day_label", "phase", "skill_group"], sort=False)[["fc_wl", "act_wl", "vol_eff", "aht_eff"]].sum().round(2).reset_index()
    out = out.rename(columns={"fc_wl": "forecast_workload_hours", "act_wl": "actual_workload_hours",
                              "vol_eff": "volume_effect_hours", "aht_eff": "aht_effect_hours"})
    out["variance_hours"] = (out.actual_workload_hours - out.forecast_workload_hours).round(2)
    out["identity_check_hours"] = (out.variance_hours - out.volume_effect_hours - out.aht_effect_hours).round(2)
    out["data_label"] = DATA_LABEL
    return out


# ------------------------------------------------------------------ C. service ----------
def service_daily(hf: pd.DataFrame, p: Params) -> pd.DataFrame:
    def f(x):
        return pd.Series({
            "contacts": x.contacts_arrived.sum(),
            "sla_attainment_pct": round(_wavg(x.sla_attainment, x.contacts_arrived) * 100, 1),
            "mean_response_sec": round(_wavg(x.response_time_sec, x.contacts_arrived), 1),
            "avg_handling_time_sec": round(float((x.contacts_arrived * x.actual_aht_sec).sum() / max(x.contacts_arrived.sum(), 1)), 1),
            "peak_backlog_contacts": round(x.backlog_end_contacts.max(), 1),
            "end_of_day_backlog_contacts": round(x.sort_values("hour").backlog_end_contacts.iloc[-1], 1),
            "hours_below_sla_target": int(((x.sla_attainment < p.sla_target) & (x.contacts_arrived > 0)).sum()),
            "understaffed_hours": int((x.capacity_gap_agents > 0).sum()),
        })
    out = hf.groupby(["date", "day_label", "phase", "skill_group"], sort=False).apply(f, include_groups=False).reset_index()
    out["sla_target_pct"] = p.sla_target * 100
    out["data_label"] = DATA_LABEL
    return out


def service_daily_total(hf: pd.DataFrame, p: Params) -> pd.DataFrame:
    def f(x):
        return pd.Series({
            "contacts": x.contacts_arrived.sum(),
            "sla_attainment_pct": round(_wavg(x.sla_attainment, x.contacts_arrived) * 100, 1),
            "mean_response_sec": round(_wavg(x.response_time_sec, x.contacts_arrived), 1),
            "end_of_day_backlog_contacts": round(x[x.hour == x.hour.max()].backlog_end_contacts.sum(), 1),
            "understaffed_group_hours": int((x.capacity_gap_agents > 0).sum()),
        })
    out = hf.groupby(["date", "day_label", "phase"], sort=False).apply(f, include_groups=False).reset_index()
    out["data_label"] = DATA_LABEL
    return out


def gap_vs_sla(hf: pd.DataFrame, p: Params):
    """Relationship between staffing shortfall and service level (event week, hours with demand)."""
    ev = hf[(hf.phase == "event") & (hf.contacts_arrived > 0)].copy()
    ev["gap_bin"] = pd.cut(ev.capacity_gap_agents, [-1e9, 0, 2, 5, 1e9], labels=["no shortfall", "1-2 agents short", "3-5 agents short", "6+ agents short"])
    ev["load_tercile"] = pd.qcut(ev.contacts_arrived * ev.actual_aht_sec, 3, labels=["low load", "mid load", "high load"])
    tab = ev.groupby("gap_bin", observed=True).apply(lambda x: pd.Series({
        "group_hours": len(x), "mean_sla_pct": round(_wavg(x.sla_attainment, x.contacts_arrived) * 100, 1),
        "share_hours_below_target_pct": round(float((x.sla_attainment < p.sla_target).mean() * 100), 1),
        "mean_response_sec": round(_wavg(x.response_time_sec, x.contacts_arrived), 1),
        "mean_end_backlog": round(x.backlog_end_contacts.mean(), 1)}), include_groups=False).reset_index()
    tab.insert(0, "analysis", "overall")
    strat = ev.assign(short=np.where(ev.capacity_gap_agents > 0, "short", "not short")).groupby(["load_tercile", "short"], observed=True).apply(
        lambda x: pd.Series({"group_hours": len(x), "mean_sla_pct": round(_wavg(x.sla_attainment, x.contacts_arrived) * 100, 1),
                             "share_hours_below_target_pct": round(float((x.sla_attainment < p.sla_target).mean() * 100), 1)}), include_groups=False).reset_index()
    strat.insert(0, "analysis", "stratified by workload tercile")
    strat = strat.rename(columns={"load_tercile": "gap_bin", "short": "shortfall_flag"})
    strat["gap_bin"] = strat["gap_bin"].astype(str) + " / " + strat["shortfall_flag"]
    strat = strat.drop(columns="shortfall_flag")
    table = pd.concat([tab, strat], ignore_index=True)
    table["data_label"] = DATA_LABEL

    # correlations (Spearman, rank-based)
    ev = ev.sort_values(["skill_group", "date", "hour"]).copy()
    ev["next_hour_sla"] = ev.groupby(["skill_group", "date"])["sla_attainment"].shift(-1)
    ev["load_ratio"] = ev.contacts_arrived * ev.actual_aht_sec / 3600 / np.maximum(ev.available * (1 - p.shrinkage), 0.5)
    def sp(a, b):
        m = a.notna() & b.notna()
        r, pv = stats.spearmanr(a[m], b[m])
        return round(float(r), 3), float(pv), int(m.sum())
    rows = []
    for name, a, b, note in [
        ("shortfall (agents) vs SLA, same hour", ev.capacity_gap_agents, ev.sla_attainment, "expected negative"),
        ("shortfall (agents) vs SLA, next hour", ev.capacity_gap_agents, ev.next_hour_sla, "backlog carry-over effect"),
        ("shortfall (agents) vs backlog at end of hour", ev.capacity_gap_agents, ev.backlog_end_contacts, "expected positive"),
        ("workload hours vs SLA, same hour", ev.contacts_arrived * ev.actual_aht_sec / 3600, ev.sla_attainment, "demand alone also moves with SLA: confounder"),
        ("load ratio (workload / productive agents) vs SLA", ev.load_ratio, ev.sla_attainment, "closest to the model's mechanism"),
    ]:
        r, pv, n = sp(a, b)
        rows.append({"relationship": name, "spearman_rho": r, "p_value": pv, "n": n, "note": note})
    corr = pd.DataFrame(rows)
    corr["caveat"] = ("Association in simulated data. SLA is generated by a queue model from staffing and load, so the link is "
                      "built in by construction and does not prove causation in a real operation.")
    corr["data_label"] = DATA_LABEL
    return table, corr


def sla_episodes(hf: pd.DataFrame, p: Params) -> pd.DataFrame:
    """Contiguous runs of below-target hours per queue-day with the shortfall overlap."""
    rows = []
    ev = hf[hf.phase == "event"].sort_values(["skill_group", "date", "hour"])
    for (g, d), x in ev.groupby(["skill_group", "date"]):
        below = ((x.sla_attainment < p.sla_target) & (x.contacts_arrived > 0)).to_numpy()
        short = (x.capacity_gap_agents > 0).to_numpy()
        hrs = x.hour.to_numpy()
        i = 0
        while i < len(below):
            if below[i]:
                j = i
                while j + 1 < len(below) and below[j + 1]:
                    j += 1
                seg = slice(i, j + 1)
                rows.append({"skill_group": g, "date": d, "day_label": x.day_label.iloc[0], "start_hour": int(hrs[i]),
                             "end_hour": int(hrs[j]), "duration_hours": j - i + 1,
                             "hours_with_shortfall": int(short[seg].sum()),
                             "shortfall_at_start_hour": bool(short[i]),
                             "shortfall_within_prior_2_hours_or_start": bool(short[max(0, i - 2):i + 1].any()),
                             "min_sla_pct": round(float(x.sla_attainment.to_numpy()[seg].min() * 100), 1),
                             "peak_backlog": round(float(x.backlog_end_contacts.to_numpy()[seg].max()), 1)})
                i = j + 1
            else:
                i += 1
    out = pd.DataFrame(rows)
    out["data_label"] = DATA_LABEL
    return out


# ------------------------------------------------------------------ D. variance ---------
def planned_vs_actual(orders: pd.DataFrame, daily_demand: pd.DataFrame, hf: pd.DataFrame, svc_total: pd.DataFrame,
                      p: Params, base_rates: dict) -> pd.DataFrame:
    """Long table of planned vs actual by event day and metric (planned = forecast/plan/target)."""
    rows = []
    ev_orders = orders[orders.phase == "event"].set_index("date")
    ev_dd = daily_demand[daily_demand.phase == "event"].set_index("date")
    ev = hf[hf.phase == "event"]
    st = svc_total[svc_total.phase == "event"].set_index("date")

    def add(date, label, metric, planned, actual, unit, kind="volume"):
        var = actual - planned
        rows.append({"date": date, "day_label": label, "metric": metric, "unit": unit, "planned": round(float(planned), 2),
                     "actual": round(float(actual), 2), "variance": round(float(var), 2),
                     "variance_pct": round(float(var / planned * 100), 2) if planned else np.nan, "kind": kind})

    for date, o in ev_orders.iterrows():
        lab = o.day_label
        x = ev[ev.date == date]
        add(date, lab, "Orders", o.forecast_orders, o.actual_orders, "orders")
        add(date, lab, "Fulfilment exceptions", base_rates["exception_rate"] * o.forecast_orders, o.fulfilment_exceptions, "count (planned = baseline rate x forecast orders)")
        add(date, lab, "Cancellations", base_rates["cancel_rate"] * o.forecast_orders, o.cancellations, "count (planned = baseline rate x forecast orders)")
        add(date, lab, "Customer contacts", ev_dd.loc[date, "forecast_contacts"], ev_dd.loc[date, "actual_contacts"], "contacts")
        pw = (x.forecast_contacts * x.planned_aht_sec / 3600).sum()
        aw = (x.actual_contacts * x.actual_aht_sec / 3600).sum()
        add(date, lab, "Workload hours", pw, aw, "agent-hours of handling work")
        add(date, lab, "Average handling time", pw * 3600 / x.forecast_contacts.sum(), aw * 3600 / x.actual_contacts.sum(), "seconds", "rate")
        add(date, lab, "Required staffing (scheduled basis)", x.required_planned.sum(), x.required_actual_scheduled_basis.sum(), "agent-hours (planned incl. 10% buffer)")
        add(date, lab, "Staff on shift vs plan", x.scheduled.sum(), x.available.sum(), "agent-hours (scheduled vs available after absence)", "supply")
        add(date, lab, "SLA attainment", p.sla_target * 100, st.loc[date, "sla_attainment_pct"], "% within threshold (planned = target)", "service")
        add(date, lab, "End-of-day backlog", 0.0, st.loc[date, "end_of_day_backlog_contacts"], "contacts (planned = 0)", "service")
    out = pd.DataFrame(rows)
    out["data_label"] = DATA_LABEL
    return out


def largest_variances(pva: pd.DataFrame, top: int = 15) -> pd.DataFrame:
    x = pva.dropna(subset=["variance_pct"]).copy()
    x["abs_variance_pct"] = x.variance_pct.abs()
    x = x[x.metric != "End-of-day backlog"]
    out = x.sort_values("abs_variance_pct", ascending=False).head(top).reset_index(drop=True)
    out.insert(0, "rank", np.arange(1, len(out) + 1))
    return out.drop(columns=["abs_variance_pct"])


def baseline_rates(orders: pd.DataFrame) -> dict:
    b = orders[orders.phase == "baseline"]
    return {"exception_rate": b.fulfilment_exceptions.sum() / b.actual_orders.sum(),
            "cancel_rate": b.cancellations.sum() / b.actual_orders.sum(),
            "return_rate": b.returns_initiated.sum() / b.actual_orders.sum()}
