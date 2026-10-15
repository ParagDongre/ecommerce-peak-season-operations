"""Shared loader/helpers for building the documentation from pipeline outputs.

Every figure in the generated docs is read from analysis/*.csv, data/*.csv or analysis/results.json,
so the docs cannot drift from the analysis (re-run `python -m src.build_docs` after the pipeline).
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
from scipy.stats import norm

from .config import Params

ROOT = Path(__file__).resolve().parents[1]
A, D, DOCS = ROOT / "analysis", ROOT / "data", ROOT / "docs"

BANNER = ("> **SIMULATED DATA / HYPOTHETICAL BUSINESS.** This is an independent portfolio case study about a fictional retailer "
          "(\"NorthBay Mart\"). It uses no Amazon data, metrics or processes, and makes no claim about any real operation. "
          "Scenario results are *modelled estimates*, not measured improvements.")


def rd(name: str, folder: Path = A) -> pd.DataFrame:
    return pd.read_csv(folder / f"{name}.csv", encoding="utf-8-sig")


def pct(x, d=1, sign=False):
    return f"{x:+.{d}f}%" if sign else f"{x:.{d}f}%"


def num(x, d=0):
    return f"{x:,.{d}f}"


def md_table(df: pd.DataFrame, cols=None, rename=None, fmts=None, align_right=True) -> str:
    """Render a DataFrame as a GitHub-markdown table. fmts: {col: callable or format string}."""
    cols = list(cols or df.columns)
    fmts = fmts or {}
    head = [(rename or {}).get(c, c) for c in cols]
    lines = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            f = fmts.get(c)
            if v is None or (isinstance(v, float) and np.isnan(v)):
                cells.append("")
            elif callable(f):
                cells.append(f(v))
            elif isinstance(f, str):
                cells.append(f.format(v))
            elif isinstance(v, float):
                cells.append(f"{v:,.1f}")
            else:
                cells.append(str(v).replace("|", "/"))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def sigma_from_defect_rate(rate: float) -> float:
    """Short-term sigma level with the conventional 1.5-sigma shift (illustrative convention)."""
    rate = min(max(rate, 1e-9), 1 - 1e-9)
    return float(norm.ppf(1 - rate) + 1.5)


def load() -> SimpleNamespace:
    p = Params()
    R = json.loads((A / "results.json").read_text(encoding="utf-8"))
    c = SimpleNamespace(p=p, R=R, H=R["headline"], E=R["evidence"])
    c.dd, c.fa, c.mix = rd("A1_demand_daily_summary"), rd("A2_forecast_accuracy"), rd("A3_contact_mix_by_category")
    c.hp, c.peaks = rd("A5_hourly_profile_event"), rd("A6_peak_hours_top10")
    c.cap_d, c.cap_h, c.bridge, c.wv = rd("B1_capacity_daily_by_group"), rd("B2_capacity_by_hour_event"), rd("B4_capacity_bridge_event_week"), rd("B5_workload_variance_decomposition")
    c.under = rd("B3_understaffed_hours_ranked")
    c.svc, c.svc_t, c.gap, c.corr, c.epis = rd("C1_service_daily_by_group"), rd("C2_service_daily_total"), rd("C3_sla_by_shortfall_size"), rd("C4_shortfall_sla_correlations"), rd("C5_sla_breach_episodes")
    c.pva, c.big = rd("D1_planned_vs_actual_event_days"), rd("D2_largest_variances")
    c.sc, c.mcs = rd("E1_scenario_comparison_single_seed"), rd("E2_scenario_monte_carlo_summary")
    c.reg = pd.read_csv(DOCS / "04_Risk_and_Mitigation_Register.csv", encoding="utf-8-sig")
    c.dep = pd.read_csv(DOCS / "04b_Dependency_Tracker.csv", encoding="utf-8-sig")
    c.orders = rd("orders_daily", D)
    c.events = rd("operational_events_log", D)
    c.service_h = rd("service_hourly", D)
    c.mcs_i = c.mcs.set_index("scenario")
    c.fa_i = c.fa.set_index(["level", "scope"])
    # --- DMAIC measures: a "defect" is a contact not answered within the SLA threshold ----------
    s = c.service_h
    s = s.assign(defects=s.contacts_arrived * (1 - s.sla_attainment))
    c.dmaic = {}
    for ph in ("baseline", "event"):
        x = s[s.phase == ph]
        rate = float(x.defects.sum() / x.contacts_arrived.sum())
        c.dmaic[ph] = {"contacts": int(x.contacts_arrived.sum()), "defects": float(x.defects.sum()), "rate": rate,
                       "dpmo": rate * 1e6, "sigma": sigma_from_defect_rate(rate)}
    ev = c.wv[c.wv.phase == "event"]
    c.vol_hours = float(ev.volume_effect_hours.sum())
    c.aht_hours = float(ev.aht_effect_hours.sum())
    c.var_hours = float(ev.variance_hours.sum())
    c.date_first = c.orders.date.iloc[0]
    c.event_start = R["event_start"]
    c.event_end = str(pd.Timestamp(R["event_start"]) + pd.Timedelta(days=p.n_event_days - 1))[:10]
    return c
