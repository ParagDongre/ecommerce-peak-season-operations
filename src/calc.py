"""Pure calculation helpers: staffing maths, Erlang C, fluid queue, rostering, accuracy metrics.

These functions contain no randomness and no I/O so they can be unit-tested directly.
All of them are *simplified models*; see docs/09_Methodology_and_Limitations.md.
"""
from __future__ import annotations

import math

import numpy as np

MAX_WAIT_SEC = 86_400.0  # cap on modelled waiting time (24 h) for pathological cases
ASA_CAP_SEC = 3_600.0  # cap used when interpolating Erlang results across an unstable integer


# --------------------------------------------------------------------------------------
# Workload and required staffing
# --------------------------------------------------------------------------------------
def workload_hours(contacts, aht_sec):
    """Agent-hours of handling work = contacts x AHT / 3600."""
    return np.asarray(contacts, dtype=float) * np.asarray(aht_sec, dtype=float) / 3600.0


def required_agents(contacts, aht_sec, shrinkage, occupancy, ceil=True):
    """Agents that must be *scheduled* in an hour to carry the workload.

    required = workload_hours / ((1 - shrinkage) * occupancy)

    * shrinkage: share of paid time not available for handling (breaks, meetings, ...)
    * occupancy: target share of available time spent handling contacts
    """
    r = workload_hours(contacts, aht_sec) / ((1.0 - shrinkage) * occupancy)
    return np.ceil(r - 1e-9) if ceil else r


# --------------------------------------------------------------------------------------
# Erlang C (stable queue) and fluid queue (overload / backlog)
# --------------------------------------------------------------------------------------
def erlang_b(n: int, a: float) -> float:
    """Erlang B blocking probability via the stable recursion."""
    b = 1.0
    for k in range(1, n + 1):
        b = a * b / (k + a * b)
    return b


def erlang_c(n: int, a: float) -> float:
    """Probability an arriving contact has to wait (Erlang C). Requires a < n."""
    if n <= 0 or a >= n:
        return 1.0
    b = erlang_b(n, a)
    return n * b / (n - a * (1.0 - b))


def service_level_integer(n: int, a: float, aht_sec: float, t_sec: float):
    """(share answered within t_sec, average speed of answer in seconds) for integer agents."""
    if a <= 0:
        return 1.0, 0.0
    if n <= a:
        return 0.0, ASA_CAP_SEC
    c = erlang_c(n, a)
    sl = 1.0 - c * math.exp(-(n - a) * t_sec / aht_sec)
    asa = min(c * aht_sec / (n - a), ASA_CAP_SEC)
    return max(0.0, min(1.0, sl)), asa


def service_level_erlang(n_eff: float, a: float, aht_sec: float, t_sec: float):
    """Erlang C service level for a fractional number of effective agents.

    Linearly interpolates between floor(n) and ceil(n); documented simplification.
    """
    if n_eff <= 0:
        return (1.0, 0.0) if a <= 0 else (0.0, ASA_CAP_SEC)
    lo = math.floor(n_eff)
    frac = n_eff - lo
    sl_lo, asa_lo = service_level_integer(lo, a, aht_sec, t_sec)
    if frac < 1e-9:
        return sl_lo, asa_lo
    sl_hi, asa_hi = service_level_integer(lo + 1, a, aht_sec, t_sec)
    return sl_lo + frac * (sl_hi - sl_lo), asa_lo + frac * (asa_hi - asa_lo)


def fluid_queue(backlog_start: float, arrivals: float, capacity: float, t_sec: float, grid: int = 60):
    """FIFO fluid approximation inside one hour.

    A contact arriving at fraction s of the hour sees queue q(s) = max(0, backlog + (arrivals - capacity)*s)
    and waits 3600*q(s)/capacity seconds. Returns (share waiting <= t_sec, mean wait in seconds).
    """
    if arrivals <= 0 and backlog_start <= 0:
        return 1.0, 0.0
    s = (np.arange(grid) + 0.5) / grid
    q = np.maximum(0.0, backlog_start + (arrivals - capacity) * s)
    if capacity <= 1e-9:
        wait = np.where(q > 0, MAX_WAIT_SEC, 0.0)
    else:
        wait = np.minimum(3600.0 * q / capacity, MAX_WAIT_SEC)
    return float(np.mean(wait <= t_sec)), float(np.mean(wait))


def hourly_service(backlog_start, arrivals, agents_eff, aht_sec, max_occ, t_sec):
    """One hour of one queue.

    agents_eff: productive agents (available agents x (1 - shrinkage), already penalty-adjusted).
    Returns dict(capacity, handled, backlog_end, sla, resp_sec).

    Regime logic (documented in the methodology doc):
      * stable  (offered load < max_occ * agents):  min(Erlang C, fluid) service level,
        max(Erlang ASA, fluid wait) response time
      * overload: fluid queue only (backlog grows)
    """
    cap = agents_eff * max_occ * 3600.0 / aht_sec if aht_sec > 0 else 0.0
    demand = backlog_start + arrivals
    handled = min(demand, cap)
    backlog_end = demand - handled
    if arrivals <= 0 and backlog_start <= 0:
        return dict(capacity=cap, handled=0.0, backlog_end=0.0, sla=1.0, resp_sec=0.0)
    sl_f, w_f = fluid_queue(backlog_start, arrivals, cap, t_sec)
    a_erl = arrivals * aht_sec / 3600.0
    if agents_eff > 0 and a_erl < max_occ * agents_eff:
        sl_e, asa_e = service_level_erlang(agents_eff, a_erl, aht_sec, t_sec)
        sl, resp = min(sl_e, sl_f), max(asa_e, w_f)
    else:
        sl, resp = sl_f, w_f
    return dict(capacity=cap, handled=handled, backlog_end=backlog_end, sla=sl, resp_sec=resp)


# --------------------------------------------------------------------------------------
# Cross-training (flex) allocation between two queues
# --------------------------------------------------------------------------------------
def flex_effective_agents(avail, flex, aht, demand, shrinkage, max_occ, penalty, donor_occ=None):
    """Effective productive agents per queue after moving cross-trained agents.

    avail, flex, aht, demand: length-2 arrays (one entry per queue).
    A cross-trained agent moves to the other queue only when (a) their own queue would still run at
    or below `donor_occ` (default: max_occ) after they leave, and (b) the other queue cannot clear its
    demand at `max_occ`. On the other queue they are `penalty` slower (AHT x (1 + penalty)).
    """
    donor_occ = max_occ if donor_occ is None else donor_occ
    avail = np.asarray(avail, float)
    flex = np.asarray(flex, float)
    aht = np.asarray(aht, float)
    demand = np.asarray(demand, float)
    per_agent = (1.0 - shrinkage) * max_occ * 3600.0 / aht  # contacts per scheduled agent-hour
    per_agent_donor = (1.0 - shrinkage) * donor_occ * 3600.0 / aht
    need = demand / per_agent_donor
    surplus = np.minimum(flex, np.maximum(0.0, avail - need))
    deficit = np.maximum(0.0, demand - avail * per_agent)
    eff = avail * (1.0 - shrinkage)
    for g in (0, 1):
        h = 1 - g
        if deficit[g] > 0 and surplus[h] > 0:
            cap_per_moved_agent = per_agent[g] / (1.0 + penalty)
            moved = min(surplus[h], deficit[g] / cap_per_moved_agent)
            eff[h] -= moved * (1.0 - shrinkage)
            eff[g] += moved * (1.0 - shrinkage) / (1.0 + penalty)
    return eff


# --------------------------------------------------------------------------------------
# Rostering
# --------------------------------------------------------------------------------------
def greedy_roster(req, masks: dict, over_weight: float, fixed_total: int | None = None, max_total: int = 400):
    """Choose how many agents start each shift template to cover a requirement curve.

    Minimises sum(shortfall^2) + over_weight * sum(overcover^2) by adding one agent at a time to the
    best template. Without `fixed_total` it stops when another agent no longer improves the objective;
    with `fixed_total` it keeps adding until exactly that many agents are rostered (used to *reallocate*
    a fixed headcount). Deterministic; ties broken by template order.
    """
    req = np.asarray(req, float)
    names = list(masks)
    counts = np.zeros(len(names), dtype=int)
    cover = np.zeros_like(req)

    def objective(cov):
        short = np.maximum(0.0, req - cov)
        over = np.maximum(0.0, cov - req)
        return float((short**2).sum() + over_weight * (over**2).sum())

    cur = objective(cover)
    limit = max_total if fixed_total is None else fixed_total
    while counts.sum() < limit:
        best_obj, best_i = None, None
        for i, nm in enumerate(names):
            o = objective(cover + masks[nm])
            if best_obj is None or o < best_obj - 1e-12:
                best_obj, best_i = o, i
        if fixed_total is None and best_obj >= cur - 1e-9:
            break
        counts[best_i] += 1
        cover = cover + masks[names[best_i]]
        cur = best_obj
    return dict(zip(names, counts.tolist()))


# --------------------------------------------------------------------------------------
# Forecast accuracy
# --------------------------------------------------------------------------------------
def wape(actual, forecast) -> float:
    """Weighted absolute percentage error = sum|A-F| / sum A."""
    a = np.asarray(actual, float)
    f = np.asarray(forecast, float)
    return float(np.abs(a - f).sum() / a.sum())


def bias(actual, forecast) -> float:
    """Signed forecast bias = (sum F - sum A) / sum A. Negative = under-forecast."""
    a = np.asarray(actual, float)
    f = np.asarray(forecast, float)
    return float((f.sum() - a.sum()) / a.sum())


def mape(actual, forecast, min_actual: float = 1.0) -> float:
    """Mean absolute percentage error, skipping points with actual < min_actual (shown for contrast only)."""
    a = np.asarray(actual, float)
    f = np.asarray(forecast, float)
    m = a >= min_actual
    return float(np.mean(np.abs(a[m] - f[m]) / a[m]))
