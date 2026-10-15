"""End-to-end pipeline: generate SIMULATED data -> analyse -> scenarios -> charts -> docs inputs.

Run from the project root:   python -m src.run_pipeline
All outputs are deterministic given the seed in src/config.py.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

from . import analysis as an
from . import charts, risk
from .config import CATEGORIES, DATA_LABEL, GROUP_LABELS, Params, assumptions_table
from .generate_data import build_all
from .scenarios import SCENARIOS, compare_scenarios, monte_carlo, summarise_mc

ROOT = Path(__file__).resolve().parents[1]
DATA, ANALYSIS, DOCS = ROOT / "data", ROOT / "analysis", ROOT / "docs"


def _csv(df: pd.DataFrame, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")  # BOM so Excel opens UTF-8 correctly


def _py(v):
    """Convert numpy scalars for JSON."""
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    raise TypeError(type(v))


def main(p: Params | None = None, quiet: bool = False, mc_n: int | None = None) -> dict:
    t0 = time.time()
    p = p or Params()
    log = (lambda *a: None) if quiet else print
    for d in (DATA, ANALYSIS, ANALYSIS / "charts", DOCS):
        d.mkdir(parents=True, exist_ok=True)

    # ---- 1. data ------------------------------------------------------------------
    r = build_all(p)
    w = r["world"]
    for name in ("orders_daily", "contacts_hourly", "staffing_hourly", "service_hourly", "absences_daily", "roster_plan", "operational_events_log"):
        _csv(r[name], DATA / f"{name}.csv")
    _csv(assumptions_table(p), DATA / "assumptions.csv")
    log(f"[1/6] datasets written ({time.time()-t0:.1f}s)")

    orders, contacts, staffing, service = r["orders_daily"], r["contacts_hourly"], r["staffing_hourly"], r["service_hourly"]
    hf = an.hourly_frame(staffing, service)

    # ---- 2. analysis ---------------------------------------------------------------
    dd = an.demand_daily(orders, contacts)
    fa = an.forecast_accuracy(orders, contacts, staffing)
    mix = an.contact_mix(contacts)
    cap_d = an.capacity_daily(hf, p)
    cap_h = an.capacity_by_hour_event(hf)
    under = an.understaffed_ranked(hf)
    bridge = an.capacity_bridge(hf, p)
    wv = an.workload_variance(hf)
    svc = an.service_daily(hf, p)
    svc_t = an.service_daily_total(hf, p)
    gap_tab, gap_corr = an.gap_vs_sla(hf, p)
    epis = an.sla_episodes(hf, p)
    pva = an.planned_vs_actual(orders, dd, hf, svc_t, p, an.baseline_rates(orders))
    big = an.largest_variances(pva)
    out = {
        "A1_demand_daily_summary": dd, "A2_forecast_accuracy": fa, "A3_contact_mix_by_category": mix,
        "A4_contacts_by_category_daily": an.contacts_by_category_daily(contacts), "A5_hourly_profile_event": an.hourly_profile_event(contacts),
        "A6_peak_hours_top10": an.peak_hours(contacts),
        "B1_capacity_daily_by_group": cap_d, "B2_capacity_by_hour_event": cap_h, "B3_understaffed_hours_ranked": under,
        "B4_capacity_bridge_event_week": bridge, "B5_workload_variance_decomposition": wv,
        "C1_service_daily_by_group": svc, "C2_service_daily_total": svc_t, "C3_sla_by_shortfall_size": gap_tab,
        "C4_shortfall_sla_correlations": gap_corr, "C5_sla_breach_episodes": epis,
        "D1_planned_vs_actual_event_days": pva, "D2_largest_variances": big,
    }
    for k, v in out.items():
        _csv(v, ANALYSIS / f"{k}.csv")
    log(f"[2/6] analysis tables written ({time.time()-t0:.1f}s)")

    # ---- 3. scenarios ----------------------------------------------------------------
    sc = compare_scenarios(p, w)
    mc = monte_carlo(p, mc_n)
    mcs = summarise_mc(mc, p)
    _csv(sc, ANALYSIS / "E1_scenario_comparison_single_seed.csv")
    _csv(mcs, ANALYSIS / "E2_scenario_monte_carlo_summary.csv")
    _csv(mc, ANALYSIS / "E3_scenario_monte_carlo_replications.csv")
    log(f"[3/6] scenarios + Monte Carlo ({len(mc)//len(SCENARIOS)} reps) ({time.time()-t0:.1f}s)")

    # ---- 4. evidence dict, risk register, dependency tracker, RACI ------------------------
    ev_o = orders[orders.phase == "event"]
    ev_hf = hf[hf.phase == "event"]
    ev_wv = wv[wv.phase == "event"].groupby("skill_group")[["forecast_workload_hours", "actual_workload_hours"]].sum()
    cap_ev = cap_d[cap_d.phase == "event"].groupby("skill_group")[["understaffed_hours", "surplus_agent_hours", "shortfall_agent_hours"]].sum()
    ex_peak = ev_o.loc[ev_o.fulfilment_exceptions.idxmax()]
    base_delay = contacts[(contacts.phase == "baseline") & (contacts.issue_category == "delivery_delay")].actual_contacts.sum() / p.n_baseline_days
    ev_delay = contacts[(contacts.phase == "event") & (contacts.issue_category == "delivery_delay")].actual_contacts.sum() / p.n_event_days
    hp = out["A5_hourly_profile_event"]
    eve = hp[hp.hour.isin(p.deal_drop_hours)]
    acc = fa.set_index(["level", "scope"])
    shortage_od = ev_hf[(ev_hf.skill_group == "OD") & (ev_hf.capacity_gap_agents > 0)].groupby("hour").capacity_gap_agents.sum().sort_values(ascending=False)
    mcs_i = mcs.set_index("scenario")
    abs_ev = r["absences_daily"][r["absences_daily"].phase == "event"]
    over_days = ev_o[ev_o.actual_orders > p.fulfilment_capacity_orders_per_day].day_label.tolist()
    first_event = pd.Timestamp(p.baseline_start) + pd.Timedelta(days=p.n_baseline_days)
    evid = {
        "od_workload_var_pct": float((ev_wv.loc["OD", "actual_workload_hours"] / ev_wv.loc["OD", "forecast_workload_hours"] - 1) * 100),
        "rp_workload_var_pct": float((ev_wv.loc["RP", "actual_workload_hours"] / ev_wv.loc["RP", "forecast_workload_hours"] - 1) * 100),
        "od_understaffed_hours": int(cap_ev.loc["OD", "understaffed_hours"]),
        "rp_understaffed_hours": int(cap_ev.loc["RP", "understaffed_hours"]),
        "rp_surplus_hours": float(cap_ev.loc["RP", "surplus_agent_hours"]),
        "od_surplus_hours": float(cap_ev.loc["OD", "surplus_agent_hours"]),
        "od_shortfall_hours": float(cap_ev.loc["OD", "shortfall_agent_hours"]),
        "rp_shortfall_hours": float(cap_ev.loc["RP", "shortfall_agent_hours"]),
        "peak_exceptions": int(ex_peak.fulfilment_exceptions), "peak_exceptions_day": str(ex_peak.day_label),
        "delay_uplift_pct": float((ev_delay / base_delay - 1) * 100),
        "eve_hour_error_pct": float((eve.event_avg_contacts.sum() / eve.event_forecast_avg_contacts.sum() - 1) * 100),
        "deal_days": [f"E{e+1}" for e in p.deal_drop_event_days],
        "event_absence_pct": float(abs_ev.absent_shifts.sum() / abs_ev.scheduled_shifts.sum() * 100),
        "top_short_hours": ", ".join(f"{h:02d}:00" for h in shortage_od.index[:3]),
        "s1_delta_pp": float(mcs_i.loc["S1", "paired_delta_sla_mean"] * 100),
        "s2_delta_pp": float(mcs_i.loc["S2", "paired_delta_sla_mean"] * 100),
        "peak_backlog": float(sc.set_index("scenario").loc["S0", "peak_backlog_contacts"]),
        "aht_var_pct": float(pva[pva.metric == "Average handling time"].pipe(lambda x: (x.actual.mean() / x.planned.mean() - 1) * 100)),
        "over_capacity_days": ", ".join(over_days) if over_days else "no day",
        "contact_wape_event": float(acc.loc[("contacts (daily total)", "event week"), "wape_pct"]),
        "contact_bias_event": float(acc.loc[("contacts (daily total)", "event week"), "bias_pct"]),
        "extra_hours": float(mcs_i.loc["S3", "extra_paid_agent_hours"]),
    }
    key_dates = {"event_start": first_event.strftime("%Y-%m-%d")}
    mc_s0 = mc[mc.scenario == "S0"]
    reg = risk.build_register(p, evid, mc_s0, key_dates)
    _csv(reg, DOCS / "04_Risk_and_Mitigation_Register.csv")
    _csv(risk.dependency_tracker(key_dates), DOCS / "04b_Dependency_Tracker.csv")
    _csv(risk.raci(), DOCS / "06_RACI_Matrix.csv")
    log(f"[4/6] risk register, dependencies, RACI ({time.time()-t0:.1f}s)")

    # ---- 5. charts ---------------------------------------------------------------------
    charts.make_all({"orders": orders, "contacts": contacts, "mix": mix, "demand_daily": dd, "hf": hf, "service_daily": svc,
                     "gap_sla": gap_tab, "mc_summary": mcs, "workload_variance": wv}, p, ANALYSIS / "charts")
    log(f"[5/6] charts written ({time.time()-t0:.1f}s)")

    # ---- 6. machine-readable results (docs are built from this) -------------------------------
    ev_svc = svc_t[svc_t.phase == "event"]
    base_svc = svc_t[svc_t.phase == "baseline"]
    bsw = lambda d: float((d.sla_attainment_pct * d.contacts).sum() / d.contacts.sum())
    results = {
        "data_label": DATA_LABEL, "seed": p.seed, "mc_replications": int(len(mc) // len(SCENARIOS)),
        "params": {k: (list(v) if isinstance(v, tuple) else v) for k, v in asdict(p).items()},
        "planned_shrinkage": p.planned_shrinkage, "event_start": key_dates["event_start"],
        "evidence": evid,
        "headline": {
            "baseline_week_sla_pct": bsw(base_svc), "event_week_sla_pct": bsw(ev_svc),
            "event_orders_total": int(ev_o.actual_orders.sum()), "baseline_orders_avg": float(orders[orders.phase == "baseline"].actual_orders.mean()),
            "peak_orders_day": str(ev_o.loc[ev_o.actual_orders.idxmax(), "day_label"]), "peak_orders": int(ev_o.actual_orders.max()),
            "peak_orders_vs_baseline_x": float(ev_o.actual_orders.max() / orders[orders.phase == "baseline"].actual_orders.mean()),
            "event_contacts_total": int(dd[dd.phase == "event"].actual_contacts.sum()),
            "event_contacts_forecast": float(dd[dd.phase == "event"].forecast_contacts.sum()),
            "worst_sla_day": str(ev_svc.loc[ev_svc.sla_attainment_pct.idxmin(), "day_label"]),
            "worst_sla_pct": float(ev_svc.sla_attainment_pct.min()),
            "days_meeting_target": int((ev_svc.sla_attainment_pct >= p.sla_target * 100).sum()),
            "end_backlog_E7": float(ev_svc[ev_svc.day_label == "E7"].end_of_day_backlog_contacts.iloc[0]),
            "understaffed_group_hours_event": int(ev_hf.understaffed.sum()), "group_hours_event": int(len(ev_hf)),
        },
        "forecast_accuracy": fa.replace({np.nan: None}).to_dict(orient="records"),
        "contact_mix": mix.to_dict(orient="records"),
        "scenarios_single_seed": sc.to_dict(orient="records"),
        "scenarios_mc": mcs.replace({np.nan: None}).to_dict(orient="records"),
        "gap_vs_sla": gap_tab.to_dict(orient="records"),
        "correlations": gap_corr.to_dict(orient="records"),
        "largest_variances": big.replace({np.nan: None}).to_dict(orient="records"),
        "capacity_bridge": bridge.to_dict(orient="records"),
        "risk_top": reg.head(6)[["risk_id", "risk", "score", "rating", "owner_role"]].to_dict(orient="records"),
        "episodes_n": int(len(epis)),
        "episodes_with_shortfall_pct": float(epis.shortfall_within_prior_2_hours_or_start.mean() * 100) if len(epis) else None,
    }
    (ANALYSIS / "results.json").write_text(json.dumps(results, indent=2, default=_py), encoding="utf-8")
    log(f"[6/6] results.json written ({time.time()-t0:.1f}s total)")
    return results


if __name__ == "__main__":
    main()
    from .build_docs import main as build_docs  # regenerate docs/*.md and README from the fresh outputs

    for f in build_docs():
        print("wrote", f)
