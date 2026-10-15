"""Reproducible SIMULATED data generator for the hypothetical retailer "NorthBay Mart".

`generate_world(p, seed)` is a pure function of (params, seed): same inputs -> identical data.
Nothing here uses real company data. All outputs carry data_label = SIMULATED.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import calc
from .config import (
    BASE_TEMPLATES, CATEGORIES, CATEGORY_GROUP, DATA_LABEL, MAX_AGENTS_PER_SHIFT_DRAW,
    N_HOURS, OPERATING_HOURS, SHIFT_TEMPLATES, SKILL_GROUPS, TEMPLATE_NAMES, Params,
)
from .simulate import simulate

CAT_GROUP_IDX = np.array([SKILL_GROUPS.index(CATEGORY_GROUP[c]) for c in CATEGORIES])
HOURS = np.array(OPERATING_HOURS)


def shift_mask(template: str) -> np.ndarray:
    s, e = SHIFT_TEMPLATES[template]
    return ((HOURS >= s) & (HOURS < e)).astype(float)


MASKS = {t: shift_mask(t) for t in TEMPLATE_NAMES}


@dataclass
class World:
    p: Params
    seed: int
    dates: pd.DatetimeIndex
    is_event: np.ndarray                 # (D,) bool
    orders: pd.DataFrame
    exp_contacts_dc: np.ndarray          # (D, C) expected daily contacts by category
    contacts: np.ndarray                 # (D, H, C) actual contacts
    aht: np.ndarray                      # (D, H, C) actual AHT (s)
    fc_contacts: np.ndarray              # (D, H, C) forecast contacts
    planned_aht: np.ndarray              # (C,) planned AHT (s)
    arrivals: np.ndarray = field(default=None)       # (D, H, G) actual contacts by skill group
    workload_h: np.ndarray = field(default=None)     # (D, H, G) actual workload hours
    fc_arrivals: np.ndarray = field(default=None)    # (D, H, G)
    fc_workload_h: np.ndarray = field(default=None)  # (D, H, G)
    req_planned: np.ndarray = field(default=None)    # (D, H, G) planned required agents (with buffer)
    req_actual: np.ndarray = field(default=None)     # (D, H, G) agents needed PRESENT for actual workload
    req_actual_sched: np.ndarray = field(default=None)  # (D, H, G) same, on a scheduled basis (incl. absence allowance)
    absence_u: np.ndarray = field(default=None)      # (D, G, T, M) uniform lottery shared by scenarios
    roster: np.ndarray = field(default=None)         # (D, G, T) baseline roster counts


def day_labels(p: Params):
    return [f"B{i+1}" for i in range(p.n_baseline_days)] + [f"E{i+1}" for i in range(p.n_event_days)]


def absence_rate_by_day(p: Params) -> np.ndarray:
    return np.r_[np.full(p.n_baseline_days, p.baseline_absence_rate), np.array(p.event_absence_rate)]


def group_arrays(p: Params, contacts, aht):
    """Aggregate (D,H,C) category arrays to (D,H,G): contacts and workload hours."""
    D = contacts.shape[0]
    G = len(SKILL_GROUPS)
    arr = np.zeros((D, N_HOURS, G))
    wl = np.zeros((D, N_HOURS, G))
    for c in range(len(CATEGORIES)):
        g = CAT_GROUP_IDX[c]
        arr[:, :, g] += contacts[:, :, c]
        wl[:, :, g] += calc.workload_hours(contacts[:, :, c], aht[:, :, c])
    return arr, wl


def required_by_group(p: Params, wl, buffer: float = 0.0, scheduled_basis: bool = True):
    """Required agents per group-hour from workload hours (see calc.required_agents).

    scheduled_basis=True : agents to SCHEDULE (shrinkage includes the planned absence allowance)
    scheduled_basis=False: agents needed PRESENT/available (non-absence shrinkage only)
    calc.required_agents takes contacts and AHT; workload hours are passed as contacts with AHT 3600 s.
    """
    shr = p.planned_shrinkage if scheduled_basis else p.shrinkage
    return calc.required_agents(np.asarray(wl) * (1.0 + buffer), 3600.0, shr, p.target_occupancy)


# ------------------------------------------------------------------------------------------
def build_orders(p: Params, rng: np.random.Generator):
    D = p.n_days
    nb = p.n_baseline_days
    dates = pd.date_range(p.baseline_start, periods=D)
    is_event = np.arange(D) >= nb
    dowf = np.array(p.baseline_dow_factor)[dates.dayofweek.to_numpy()]
    mult_actual = np.r_[np.ones(nb), np.array(p.actual_event_multiplier)]
    mult_plan = np.r_[np.ones(nb), np.array(p.plan_event_multiplier)]
    noise = rng.normal(0.0, p.order_noise_sd, D)
    orders = np.rint(p.baseline_orders_per_day * dowf * mult_actual * (1.0 + noise)).astype(int)
    fc_orders = np.rint(p.baseline_orders_per_day * dowf * mult_plan).astype(int)

    ev_idx = np.where(is_event)[0]
    exc_day_in_event = lambda days: np.isin(np.arange(D) - nb, days) & is_event

    # fulfilment exceptions
    excess = np.maximum(0, orders - p.fulfilment_capacity_orders_per_day)
    late_exp = p.base_late_shipment_rate * orders + p.late_share_of_excess_orders * excess
    late_exp = late_exp + p.carrier_disruption_extra_late_rate * orders * exc_day_in_event(p.carrier_disruption_event_days)
    late = rng.poisson(late_exp)
    failed = rng.poisson(p.failed_delivery_rate * orders)
    damaged = rng.poisson(p.damaged_missing_rate * orders)
    # cancellations
    so_rate = p.base_stockout_cancel_rate + p.stockout_extra_cancel_rate * exc_day_in_event(p.stockout_event_days)
    stockout_cancels = rng.poisson(so_rate * orders)
    other_cancels = rng.poisson((p.base_cancel_rate - p.base_stockout_cancel_rate) * orders)
    cancels = stockout_cancels + other_cancels
    # returns with lag (steady-state history assumed before day 0)
    rate = np.where(is_event, p.event_return_rate, p.base_return_rate)
    returns_exp = np.zeros(D)
    for t in range(D):
        for k, w in zip(p.return_lag_days, p.return_lag_weights):
            s = t - k
            if s >= 0:
                returns_exp[t] += w * rate[s] * orders[s]
            else:
                returns_exp[t] += w * p.base_return_rate * p.baseline_orders_per_day
    returns = rng.poisson(returns_exp)

    labels = day_labels(p)
    df = pd.DataFrame(
        {
            "date": dates.strftime("%Y-%m-%d"),
            "day_index": np.arange(D),
            "day_label": labels,
            "phase": np.where(is_event, "event", "baseline"),
            "weekday": dates.day_name(),
            "forecast_orders": fc_orders,
            "actual_orders": orders,
            "late_shipments": late,
            "failed_deliveries": failed,
            "damaged_or_missing": damaged,
            "fulfilment_exceptions": late + failed + damaged,
            "cancellations": cancels,
            "stockout_cancellations": stockout_cancels,
            "returns_initiated": returns,
        }
    )
    df["order_growth_dod_pct"] = (df["actual_orders"].pct_change() * 100).round(2)
    base_avg = df.loc[df.phase == "baseline", "actual_orders"].mean()
    df["orders_vs_baseline_avg"] = (df["actual_orders"] / base_avg).round(3)
    df["cancellation_rate_pct"] = (df["cancellations"] / df["actual_orders"] * 100).round(2)
    df["return_rate_pct"] = (df["returns_initiated"] / df["actual_orders"] * 100).round(2)
    df["exception_rate_pct"] = (df["fulfilment_exceptions"] / df["actual_orders"] * 100).round(2)
    df["data_label"] = DATA_LABEL
    return dates, is_event, df


def expected_daily_contacts(p: Params, orders_df: pd.DataFrame, is_event: np.ndarray) -> np.ndarray:
    o = orders_df["actual_orders"].to_numpy(float)
    exc = orders_df["fulfilment_exceptions"].to_numpy(float)
    so = orders_df["stockout_cancellations"].to_numpy(float)
    ret = orders_df["returns_initiated"].to_numpy(float)
    D = len(o)
    prev = lambda a, k: np.array([a[max(t - k, 0)] for t in range(D)])
    out = np.zeros((D, len(CATEGORIES)))
    w0, w1 = p.wismo_lag_weights
    out[:, 0] = p.wismo_per_order * (w0 * o + w1 * prev(o, 1))
    d0, d1 = p.delay_lag_weights
    out[:, 1] = p.delay_contacts_per_exception * (d0 * prev(exc, 1) + d1 * prev(exc, 2))
    out[:, 2] = p.cancel_modify_per_order * o + p.contacts_per_stockout_cancel * so
    out[:, 3] = p.contacts_per_return * ret
    out[:, 4] = p.payment_promo_per_order * o * np.where(is_event, p.payment_promo_event_factor, 1.0)
    out[:, 5] = p.product_enquiry_per_order * o * np.where(is_event, p.product_enquiry_event_factor, 1.0)
    return out


def hourly_profile_matrix(p: Params) -> np.ndarray:
    """(D, H, C) share of each day's category contacts landing in each hour (with deal-drop uplift)."""
    D = p.n_days
    base = np.array(p.hourly_profile)
    prof = np.tile(base, (D, len(CATEGORIES), 1))  # (D, C, H)
    for e in p.deal_drop_event_days:
        d = p.n_baseline_days + e
        for c, cat in enumerate(CATEGORIES):
            if cat in ("delivery_delay", "returns_refunds"):
                continue  # driven by past events, not by an evening deal
            w = base.copy()
            for hh in p.deal_drop_hours:
                w[list(OPERATING_HOURS).index(hh)] *= p.deal_drop_uplift
            prof[d, c, :] = w / w.sum()
    return np.transpose(prof, (0, 2, 1))


def draw_contacts_and_aht(p: Params, exp_dc: np.ndarray, is_event: np.ndarray, rng: np.random.Generator):
    D, C = exp_dc.shape
    prof = hourly_profile_matrix(p)  # (D, H, C)
    day_eff = np.exp(rng.normal(-0.5 * p.contact_day_effect_sd**2, p.contact_day_effect_sd, (D, 1, C)))
    mean_hourly = exp_dc[:, None, :] * prof * day_eff
    contacts = rng.poisson(mean_hourly)
    aht_base = np.array(p.aht_sec, float)[None, None, :] * np.where(is_event, p.event_aht_complexity_factor, 1.0)[:, None, None]
    aht = np.maximum(60.0, aht_base * (1.0 + rng.normal(0.0, p.aht_noise_sd, (D, N_HOURS, C))))
    return contacts, aht


def build_forecast(p: Params, orders_df: pd.DataFrame, contacts: np.ndarray, aht: np.ndarray):
    """Planner forecast: baseline-week contacts-per-order x forecast orders x baseline hourly profile.

    Rates/profile/AHT are learned from the baseline week only (so event effects are NOT anticipated).
    For baseline days the forecast is therefore in-sample (documented).
    """
    nb = p.n_baseline_days
    ao = orders_df["actual_orders"].to_numpy(float)
    fo = orders_df["forecast_orders"].to_numpy(float)
    base_orders = ao[:nb].sum()
    base_c = contacts[:nb].sum(axis=(0, 1))                 # (C,)
    rate = base_c / base_orders                              # contacts per order
    prof = contacts[:nb].sum(axis=0) / np.maximum(base_c[None, :], 1e-9)  # (H, C) hour shares
    fc = fo[:, None, None] * rate[None, None, :] * prof[None, :, :]
    wl = (contacts[:nb] * aht[:nb]).sum(axis=(0, 1))
    planned_aht = wl / np.maximum(base_c, 1e-9)
    return fc, planned_aht


def draw_absence_lottery(p: Params, rng: np.random.Generator):
    return rng.random((p.n_days, len(SKILL_GROUPS), len(TEMPLATE_NAMES), MAX_AGENTS_PER_SHIFT_DRAW))


def available_from_roster(p: Params, roster: np.ndarray, u: np.ndarray):
    """roster (D,G,T) ints + shared lottery u -> scheduled, absent, available arrays (D,H,G) and absent (D,G,T)."""
    D, G, T = roster.shape
    rates = absence_rate_by_day(p)
    absent = np.zeros((D, G, T), dtype=int)
    for d in range(D):
        for g in range(G):
            for t in range(T):
                n = int(roster[d, g, t])
                if n:
                    absent[d, g, t] = int((u[d, g, t, :n] < rates[d]).sum())
    masks = np.stack([MASKS[t] for t in TEMPLATE_NAMES])  # (T, H)
    scheduled = np.einsum("dgt,th->dhg", roster, masks)
    available = np.einsum("dgt,th->dhg", roster - absent, masks)
    return scheduled, available, absent


def build_baseline_roster(p: Params, req_planned: np.ndarray) -> np.ndarray:
    D, H, G = req_planned.shape
    roster = np.zeros((D, G, len(TEMPLATE_NAMES)), dtype=int)
    masks = {t: MASKS[t] for t in BASE_TEMPLATES}
    for d in range(D):
        for g in range(G):
            res = calc.greedy_roster(req_planned[d, :, g], masks, p.roster_over_weight)
            for t, n in res.items():
                roster[d, g, TEMPLATE_NAMES.index(t)] = n
    return roster


def generate_world(p: Params, seed: int | None = None) -> World:
    p.validate()
    seed = p.seed if seed is None else seed
    ss = np.random.SeedSequence(seed)
    r_orders, r_contacts, r_abs = (np.random.default_rng(s) for s in ss.spawn(3))
    dates, is_event, orders_df = build_orders(p, r_orders)
    exp_dc = expected_daily_contacts(p, orders_df, is_event)
    contacts, aht = draw_contacts_and_aht(p, exp_dc, is_event, r_contacts)
    fc, planned_aht = build_forecast(p, orders_df, contacts, aht)
    w = World(p, seed, dates, is_event, orders_df, exp_dc, contacts, aht, fc, planned_aht)
    w.arrivals, w.workload_h = group_arrays(p, contacts, aht)
    w.fc_arrivals, w.fc_workload_h = group_arrays(p, fc, np.broadcast_to(planned_aht, fc.shape))
    w.req_planned = required_by_group(p, w.fc_workload_h, p.planning_buffer)
    w.req_actual = required_by_group(p, w.workload_h, 0.0, scheduled_basis=False)
    w.req_actual_sched = required_by_group(p, w.workload_h, 0.0, scheduled_basis=True)
    w.absence_u = draw_absence_lottery(p, r_abs)
    w.roster = build_baseline_roster(p, w.req_planned)
    return w


# ------------------------------------------------------------------------------------------
# Tables
# ------------------------------------------------------------------------------------------
def _grid(w: World):
    p = w.p
    D, H, G = w.arrivals.shape
    labels = day_labels(p)
    idx = pd.MultiIndex.from_product([range(D), range(H), range(G)], names=["d", "h", "g"])
    base = idx.to_frame(index=False)
    base["date"] = w.dates.strftime("%Y-%m-%d")[base["d"]]
    base["day_index"] = base["d"]
    base["day_label"] = np.array(labels)[base["d"]]
    base["phase"] = np.where(w.is_event[base["d"]], "event", "baseline")
    base["hour"] = HOURS[base["h"]]
    base["skill_group"] = np.array(SKILL_GROUPS)[base["g"]]
    return base


def contacts_table(w: World) -> pd.DataFrame:
    p = w.p
    D, H, C = w.contacts.shape
    labels = np.array(day_labels(p))
    idx = pd.MultiIndex.from_product([range(D), range(H), range(C)], names=["d", "h", "c"]).to_frame(index=False)
    df = pd.DataFrame(
        {
            "date": w.dates.strftime("%Y-%m-%d")[idx["d"]],
            "day_index": idx["d"],
            "day_label": labels[idx["d"]],
            "phase": np.where(w.is_event[idx["d"]], "event", "baseline"),
            "hour": HOURS[idx["h"]],
            "issue_category": np.array(CATEGORIES)[idx["c"]],
            "skill_group": np.array(SKILL_GROUPS)[CAT_GROUP_IDX[idx["c"]]],
            "forecast_contacts": np.round(w.fc_contacts[idx["d"], idx["h"], idx["c"]], 2),
            "actual_contacts": w.contacts[idx["d"], idx["h"], idx["c"]],
            "planned_aht_sec": np.round(w.planned_aht[idx["c"]], 1),
            "actual_aht_sec": np.round(w.aht[idx["d"], idx["h"], idx["c"]], 1),
        }
    )
    df["data_label"] = DATA_LABEL
    return df


def staffing_and_service_tables(w: World, sim: dict, scheduled, available, absent):
    p = w.p
    g = _grid(w)
    d, h, k = g["d"].to_numpy(), g["h"].to_numpy(), g["g"].to_numpy()
    st = g[["date", "day_index", "day_label", "phase", "hour", "skill_group"]].copy()
    st["forecast_contacts"] = np.round(w.fc_arrivals[d, h, k], 2)
    st["actual_contacts"] = w.arrivals[d, h, k].astype(int)
    st["planned_aht_sec"] = np.round(np.where(w.fc_arrivals[d, h, k] > 0, w.fc_workload_h[d, h, k] * 3600 / np.maximum(w.fc_arrivals[d, h, k], 1e-9), 0), 1)
    st["actual_aht_sec"] = np.round(np.where(w.arrivals[d, h, k] > 0, w.workload_h[d, h, k] * 3600 / np.maximum(w.arrivals[d, h, k], 1), 0), 1)
    st["required_planned"] = w.req_planned[d, h, k].astype(int)
    st["required_actual_scheduled_basis"] = w.req_actual_sched[d, h, k].astype(int)
    st["required_actual"] = w.req_actual[d, h, k].astype(int)
    st["scheduled"] = scheduled[d, h, k].astype(int)
    st["available"] = available[d, h, k].astype(int)
    st["absent"] = st["scheduled"] - st["available"]
    st["plan_gap_agents"] = st["required_planned"] - st["scheduled"]
    st["capacity_gap_agents"] = st["required_actual"] - st["available"]
    st["understaffed"] = (st["capacity_gap_agents"] > 0).astype(int)
    st["data_label"] = DATA_LABEL

    sv = g[["date", "day_index", "day_label", "phase", "hour", "skill_group"]].copy()
    sv["contacts_arrived"] = w.arrivals[d, h, k].astype(int)
    sv["aht_sec"] = st["actual_aht_sec"].to_numpy()
    sv["effective_agents"] = np.round(sim["eff_agents"][d, h, k], 2)
    sv["capacity_contacts"] = np.round(sim["capacity"][d, h, k], 1)
    sv["contacts_handled"] = np.round(sim["handled"][d, h, k], 1)
    sv["backlog_end_contacts"] = np.round(sim["backlog_end"][d, h, k], 1)
    sv["response_time_sec"] = np.round(sim["resp_sec"][d, h, k], 1)
    sv["sla_attainment"] = np.round(sim["sla"][d, h, k], 4)
    sv["sla_target"] = p.sla_target
    sv["data_label"] = DATA_LABEL
    return st, sv


def absences_roster_tables(w: World, absent):
    p = w.p
    rows, rrows = [], []
    labels = day_labels(p)
    rates = absence_rate_by_day(p)
    for d in range(p.n_days):
        for gi, gname in enumerate(SKILL_GROUPS):
            tot_s = int(w.roster[d, gi].sum())
            tot_a = int(absent[d, gi].sum())
            rows.append(
                {
                    "date": w.dates[d].strftime("%Y-%m-%d"), "day_label": labels[d],
                    "phase": "event" if w.is_event[d] else "baseline", "skill_group": gname,
                    "scheduled_shifts": tot_s, "absent_shifts": tot_a,
                    "absence_rate_realised": round(tot_a / tot_s, 4) if tot_s else 0.0,
                    "absence_rate_assumed": float(rates[d]), "data_label": DATA_LABEL,
                }
            )
            for ti, t in enumerate(TEMPLATE_NAMES):
                rrows.append(
                    {
                        "date": w.dates[d].strftime("%Y-%m-%d"), "day_label": labels[d], "skill_group": gname,
                        "shift_template": t, "shift_hours": f"{SHIFT_TEMPLATES[t][0]:02d}:00-{SHIFT_TEMPLATES[t][1]:02d}:00",
                        "agents_scheduled": int(w.roster[d, gi, ti]), "agents_absent": int(absent[d, gi, ti]),
                        "data_label": DATA_LABEL,
                    }
                )
    return pd.DataFrame(rows), pd.DataFrame(rrows)


def events_log(w: World) -> pd.DataFrame:
    p = w.p
    nb = p.n_baseline_days
    labels = day_labels(p)

    def row(i, d, typ, desc, owner, effect):
        return {"event_id": f"EV{i:02d}", "date": w.dates[d].strftime("%Y-%m-%d"), "day_label": labels[d],
                "event_type": typ, "description": desc, "owning_team": owner, "modelled_effect": effect,
                "data_label": DATA_LABEL}

    rows, i = [], 1
    for e in p.stockout_event_days:
        rows.append(row(i, nb + e, "Stock-out", "Promotional items sell out; orders for them are cancelled.", "Inventory / Operations",
                        f"+{p.stockout_extra_cancel_rate*100:.1f} pts cancellation rate; extra cancel/modify contacts")); i += 1
    rows.append(row(i, nb + 2, "Absence spike", "Hypothetical regional disruption raises unplanned absence.", "Workforce Planning",
                    f"Absence {p.event_absence_rate[2]*100:.0f}% vs {p.baseline_absence_rate*100:.0f}% baseline")); i += 1
    for e in p.carrier_disruption_event_days:
        rows.append(row(i, nb + e, "Carrier disruption", "Hypothetical carrier network disruption delays deliveries.", "Fulfilment / Transport",
                        f"+{p.carrier_disruption_extra_late_rate*100:.0f} pts late-shipment rate; delay contacts follow 1-2 days later")); i += 1
    for e in p.deal_drop_event_days:
        rows.append(row(i, nb + e, "Evening deal drop", "Unscheduled-in-forecast lightning deal at 20:00-21:59.", "Marketing / Merchandising",
                        f"x{p.deal_drop_uplift} intraday weight at {p.deal_drop_hours[0]}:00-{p.deal_drop_hours[-1]+1}:00")); i += 1
    over = np.where(w.orders["actual_orders"].to_numpy() > p.fulfilment_capacity_orders_per_day)[0]
    for d in over:
        rows.append(row(i, int(d), "Fulfilment capacity exceeded",
                        f"Orders above {p.fulfilment_capacity_orders_per_day:,}/day dispatch late.", "Fulfilment / Operations",
                        f"{p.late_share_of_excess_orders*100:.0f}% of excess orders late")); i += 1
    return pd.DataFrame(rows).sort_values(["date", "event_id"]).reset_index(drop=True)


def build_all(p: Params, seed: int | None = None):
    """Generate the world, baseline roster, baseline simulation, and all output tables."""
    w = generate_world(p, seed)
    scheduled, available, absent = available_from_roster(p, w.roster, w.absence_u)
    sim = simulate(p, w.arrivals, w.workload_h, available)
    st, sv = staffing_and_service_tables(w, sim, scheduled, available, absent)
    ab, ro = absences_roster_tables(w, absent)
    return {
        "world": w, "sim": sim, "scheduled": scheduled, "available": available, "absent": absent,
        "orders_daily": w.orders, "contacts_hourly": contacts_table(w), "staffing_hourly": st,
        "service_hourly": sv, "absences_daily": ab, "roster_plan": ro, "operational_events_log": events_log(w),
    }
