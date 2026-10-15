"""Mitigation scenarios (MODELLED ESTIMATES on SIMULATED data).

Scenarios (event days only; baseline-week rosters are unchanged):
  S0  As-planned baseline (forecast-built roster executed against actual demand)
  S1  Reallocate existing headcount: same agents per group-day, re-rostered to a rolling-corrected forecast
  S2  Cross-training: `flex_share` of agents can serve the other queue (with an AHT penalty)
  S3  Approved additional capacity, spread evenly: a 17:00-22:00 peak-cover shift, N agents per queue per event day
  S4  Same total extra agents (same paid hours as S3) all assigned to the bottleneck queue
  S5  Combined (S1 + S2 + S4)
  S6  Ablation of S5 without S1 (S2 + S4) to isolate the marginal value of reallocation

Information rule: the correction for event day d uses only actuals up to day d-1 (no look-ahead).
Not modelled: training time/cost, hiring lead time, overtime premiums, agent preferences, attrition.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import calc
from .config import BASE_TEMPLATES, SHIFT_TEMPLATES, SKILL_GROUPS, TEMPLATE_NAMES, Params
from .generate_data import (
    MASKS, World, available_from_roster, generate_world, required_by_group,
)
from .simulate import simulate

SCENARIOS = {
    "S0": "As-planned baseline",
    "S1": "Reallocate existing staff to rolling-corrected forecast",
    "S2": "Cross-train 20% of agents across both queues",
    "S3": "Extra peak-cover capacity (17:00-22:00), spread evenly over queues",
    "S4": "Same extra capacity, targeted at the bottleneck queue (OD)",
    "S5": "Combined: S1 + S2 + S4",
    "S6": "Ablation: S2 + S4 (no reallocation)",
}
SCENARIO_FLEX = {"S0": False, "S1": False, "S2": True, "S3": False, "S4": False, "S5": True, "S6": True}
_REALLOC = ("S1", "S5")
_EXTRA_EVEN = ("S3",)
_EXTRA_TARGETED = ("S4", "S5", "S6")


def corrected_requirement_curve(p: Params, w: World, d: int, g: int) -> np.ndarray:
    """Required scheduled agents by hour for day d, group g from a rolling-corrected forecast.

    ratio  = actual workload / forecast workload over the previous `lookback` days (clipped)
    shape  = blend of the observed intraday workload shape (previous days) and the baseline forecast shape
    """
    lo = max(0, d - p.forecast_correction_lookback_days)
    prev = range(lo, d)
    fc_tot = w.fc_workload_h[d, :, g].sum()
    if len(prev) == 0 or fc_tot <= 0:
        return w.req_planned[d, :, g].astype(float)
    act_prev = w.workload_h[lo:d, :, g].sum(axis=0)
    fc_prev = w.fc_workload_h[lo:d, :, g].sum()
    ratio = float(np.clip(act_prev.sum() / fc_prev, *p.forecast_correction_bounds))
    obs_shape = act_prev / act_prev.sum()
    base_shape = w.fc_workload_h[d, :, g] / fc_tot
    shape = p.profile_blend_weight * obs_shape + (1 - p.profile_blend_weight) * base_shape
    wl_curve = fc_tot * ratio * shape
    return np.ceil(wl_curve * (1 + p.planning_buffer) / ((1 - p.planned_shrinkage) * p.target_occupancy) - 1e-9)


def build_roster(p: Params, w: World, scenario: str) -> np.ndarray:
    """Roster counts (D, G, T) for a scenario."""
    roster = w.roster.copy()
    nb = p.n_baseline_days
    D, G, _ = roster.shape
    t_idx = {t: i for i, t in enumerate(TEMPLATE_NAMES)}
    if scenario in _REALLOC:
        masks = {t: MASKS[t] for t in BASE_TEMPLATES}
        for d in range(nb, D):
            for g in range(G):
                total = int(w.roster[d, g, [t_idx[t] for t in BASE_TEMPLATES]].sum())
                curve = corrected_requirement_curve(p, w, d, g)
                res = calc.greedy_roster(curve, masks, p.roster_over_weight, fixed_total=total)
                for t in BASE_TEMPLATES:
                    roster[d, g, t_idx[t]] = res[t]
    if scenario in _EXTRA_EVEN:
        roster[nb:, :, t_idx["D"]] += p.extra_peak_agents_per_group_day
    if scenario in _EXTRA_TARGETED:
        gi = SKILL_GROUPS.index(p.extra_peak_targeted_group)
        roster[nb:, gi, t_idx["D"]] += p.extra_peak_agents_per_group_day * len(SKILL_GROUPS)
    return roster


def paid_agent_hours(roster: np.ndarray, event_only_from: int = 0) -> float:
    hrs = np.array([SHIFT_TEMPLATES[t][1] - SHIFT_TEMPLATES[t][0] for t in TEMPLATE_NAMES], float)
    return float((roster[event_only_from:] * hrs[None, None, :]).sum())


def run_scenario(p: Params, w: World, scenario: str) -> dict:
    roster = build_roster(p, w, scenario)
    sched, avail, absent = available_from_roster(p, roster, w.absence_u)
    sim = simulate(p, w.arrivals, w.workload_h, avail, flex=SCENARIO_FLEX[scenario])
    return {"scenario": scenario, "roster": roster, "scheduled": sched, "available": avail, "absent": absent, "sim": sim}


def kpis(p: Params, w: World, res: dict) -> dict:
    """Event-week KPIs for one scenario run (arrival-weighted SLA etc.)."""
    nb = p.n_baseline_days
    sim, avail = res["sim"], res["available"]
    arr = w.arrivals[nb:]
    sla = sim["sla"][nb:]
    resp = sim["resp_sec"][nb:]
    bl = sim["backlog_end"][nb:]
    out = {
        "sla_overall": float((sla * arr).sum() / arr.sum()),
        "mean_response_sec": float((resp * arr).sum() / arr.sum()),
        "group_hours_below_target": int(((sla < p.sla_target) & (arr > 0)).sum()),
        "peak_backlog_contacts": float(bl.sum(axis=2).max()),
        "end_of_event_backlog_contacts": float(bl[-1, -1, :].sum()),
        "understaffed_group_hours": int((w.req_actual[nb:] > avail[nb:]).sum()),
        "shortfall_agent_hours": float(np.maximum(0, w.req_actual[nb:] - avail[nb:]).sum()),
        "paid_agent_hours": paid_agent_hours(res["roster"], nb),
    }
    for gi, g in enumerate(SKILL_GROUPS):
        out[f"sla_{g}"] = float((sla[:, :, gi] * arr[:, :, gi]).sum() / arr[:, :, gi].sum())
    # worst single-day SLA
    day_sla = (sla * arr).sum(axis=(1, 2)) / arr.sum(axis=(1, 2))
    out["worst_day_sla"] = float(day_sla.min())
    out["days_meeting_sla_target"] = int((day_sla >= p.sla_target).sum())
    return out


def compare_scenarios(p: Params, w: World) -> pd.DataFrame:
    rows, base_paid = [], None
    for s, name in SCENARIOS.items():
        res = run_scenario(p, w, s)
        k = kpis(p, w, res)
        if s == "S0":
            base_paid = k["paid_agent_hours"]
        k["extra_paid_agent_hours_vs_S0"] = k["paid_agent_hours"] - base_paid
        rows.append({"scenario": s, "description": name, **k})
    df = pd.DataFrame(rows)
    df["label"] = "MODELLED ESTIMATE (simulated data; single seed)"
    return df


def monte_carlo(p: Params, n: int | None = None) -> pd.DataFrame:
    """Re-draw the whole simulated world (orders, contacts, AHT, absences) n times; compare all scenarios.

    Each replication uses a different seed but all scenarios within a replication share the same demand
    and the same absence lottery (common random numbers), so differences are paired.
    """
    n = p.mc_replications if n is None else n
    rows = []
    for r in range(n):
        w = generate_world(p, seed=p.seed + 1000 + r)
        for s in SCENARIOS:
            k = kpis(p, w, run_scenario(p, w, s))
            rows.append({"replication": r, "scenario": s, **k})
    df = pd.DataFrame(rows)
    base = df[df.scenario == "S0"].set_index("replication")
    for col in ("sla_overall", "end_of_event_backlog_contacts", "shortfall_agent_hours", "mean_response_sec"):
        df[f"delta_{col}"] = df[col] - df["replication"].map(base[col])
    df["label"] = "MODELLED ESTIMATE (simulated data)"
    return df


def summarise_mc(mc: pd.DataFrame, p: Params) -> pd.DataFrame:
    rows = []
    for s, g in mc.groupby("scenario", sort=True):
        rows.append(
            {
                "scenario": s, "description": SCENARIOS[s], "replications": len(g),
                "sla_overall_mean": g.sla_overall.mean(), "sla_overall_p10": g.sla_overall.quantile(0.10),
                "sla_overall_p90": g.sla_overall.quantile(0.90),
                "sla_OD_mean": g.sla_OD.mean(), "sla_RP_mean": g.sla_RP.mean(),
                "mean_response_sec_mean": g.mean_response_sec.mean(),
                "end_backlog_mean": g.end_of_event_backlog_contacts.mean(),
                "share_reps_ending_with_backlog_gt_50": float((g.end_of_event_backlog_contacts > 50).mean()),
                "shortfall_agent_hours_mean": g.shortfall_agent_hours.mean(),
                "days_meeting_target_mean": g.days_meeting_sla_target.mean(),
                "extra_paid_agent_hours": g.paid_agent_hours.mean() - mc[mc.scenario == "S0"].paid_agent_hours.mean(),
                "paired_delta_sla_mean": g.delta_sla_overall.mean(),
                "paired_delta_sla_p10": g.delta_sla_overall.quantile(0.10),
                "paired_delta_sla_p90": g.delta_sla_overall.quantile(0.90),
                "share_reps_better_than_S0": float((g.delta_sla_overall > 0.005).mean()) if s != "S0" else np.nan,
                "share_reps_worse_than_S0": float((g.delta_sla_overall < -0.005).mean()) if s != "S0" else np.nan,
                "label": "MODELLED ESTIMATE (simulated data; ranges = p10-p90 across replications)",
            }
        )
    return pd.DataFrame(rows)
