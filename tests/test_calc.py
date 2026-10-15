"""Unit tests for the pure calculation helpers (src/calc.py)."""
import math

import numpy as np
import pytest

from src import calc


def test_workload_hours():
    assert calc.workload_hours(100, 360) == pytest.approx(10.0)


def test_required_agents_matches_hand_calculation():
    # 100 contacts x 360 s = 10 workload hours; (1-0.2)*0.8 = 0.64 -> 15.625 -> 16 scheduled agents
    assert calc.required_agents(100, 360, 0.2, 0.8, ceil=False) == pytest.approx(15.625)
    assert calc.required_agents(100, 360, 0.2, 0.8) == 16


def test_required_agents_zero_demand_is_zero():
    assert calc.required_agents(0, 300, 0.12, 0.85) == 0


def test_required_agents_increases_with_shrinkage_and_lower_occupancy():
    base = calc.required_agents(500, 300, 0.12, 0.85, ceil=False)
    assert calc.required_agents(500, 300, 0.25, 0.85, ceil=False) > base
    assert calc.required_agents(500, 300, 0.12, 0.70, ceil=False) > base


def test_erlang_known_values():
    assert calc.erlang_b(1, 1.0) == pytest.approx(0.5)
    assert calc.erlang_c(1, 0.5) == pytest.approx(0.5)
    assert calc.erlang_c(2, 1.0) == pytest.approx(1 / 3)
    assert calc.erlang_c(3, 3.0) == 1.0  # unstable queue: everyone waits


def test_service_level_monotone_in_agents():
    a, aht, t = 18.0, 300.0, 300
    sls = [calc.service_level_integer(n, a, aht, t)[0] for n in range(19, 30)]
    assert all(x <= y + 1e-12 for x, y in zip(sls, sls[1:]))
    assert sls[-1] > 0.99


def test_service_level_unstable_and_idle():
    assert calc.service_level_integer(5, 6.0, 300, 300)[0] == 0.0
    assert calc.service_level_integer(5, 0.0, 300, 300) == (1.0, 0.0)


def test_service_level_fractional_agents_interpolates():
    lo = calc.service_level_erlang(20.0, 17.0, 300, 300)[0]
    hi = calc.service_level_erlang(21.0, 17.0, 300, 300)[0]
    mid = calc.service_level_erlang(20.5, 17.0, 300, 300)[0]
    assert lo <= mid <= hi


def test_fluid_queue_extremes():
    assert calc.fluid_queue(0, 0, 100, 300) == (1.0, 0.0)
    sl, wait = calc.fluid_queue(0, 50, 100, 300)  # spare capacity, no queue
    assert sl == 1.0 and wait == 0.0
    sl, wait = calc.fluid_queue(5000, 100, 100, 300)  # huge standing backlog
    assert sl == 0.0 and wait > 300


@pytest.mark.parametrize("backlog,arrivals,agents", [(0, 120, 8), (30, 120, 8), (0, 40, 8), (200, 10, 3), (0, 0, 5)])
def test_hourly_service_conserves_contacts(backlog, arrivals, agents):
    r = calc.hourly_service(backlog, arrivals, agents, 300, 0.95, 300)
    assert r["handled"] + r["backlog_end"] == pytest.approx(backlog + arrivals)
    assert r["handled"] <= r["capacity"] + 1e-9
    assert 0.0 <= r["sla"] <= 1.0


def test_hourly_service_no_agents_builds_backlog():
    r = calc.hourly_service(0, 50, 0, 300, 0.95, 300)
    assert r["handled"] == 0 and r["backlog_end"] == 50 and r["sla"] == 0.0


def test_wape_bias_hand_calculation():
    a, f = [100, 200], [110, 180]
    assert calc.wape(a, f) == pytest.approx(30 / 300)
    assert calc.bias(a, f) == pytest.approx(-10 / 300)
    assert calc.bias([100], [120]) > 0  # over-forecast is positive


def test_wape_robust_where_mape_explodes():
    a, f = [1000, 2], [1000, 20]
    assert calc.wape(a, f) < 0.05  # volume-weighted: the tiny point barely matters
    assert calc.mape(a, f, min_actual=1) > 4  # per-point percentage explodes


def test_greedy_roster_fixed_total_and_coverage():
    h = np.arange(16)
    masks = {"A": ((h >= 0) & (h < 8)).astype(float), "B": ((h >= 8) & (h < 16)).astype(float)}
    req = np.array([4] * 8 + [10] * 8, float)
    res = calc.greedy_roster(req, masks, 0.15, fixed_total=14)
    assert sum(res.values()) == 14 and res == {"A": 4, "B": 10}


def test_greedy_roster_stops_when_no_improvement():
    h = np.arange(16)
    masks = {"A": ((h < 8)).astype(float)}
    res = calc.greedy_roster(np.array([3] * 8 + [0] * 8, float), masks, 0.15)
    assert res["A"] == 3


def test_flex_moves_only_into_deficit_and_conserves_capacity():
    kw = dict(shrinkage=0.12, max_occ=0.95, penalty=0.10, donor_occ=0.85)
    avail, aht = np.array([10.0, 10.0]), np.array([300.0, 300.0])
    # no deficit -> unchanged
    eff = calc.flex_effective_agents(avail, 0.2 * avail, aht, np.array([50.0, 50.0]), **kw)
    assert eff == pytest.approx(avail * 0.88)
    # queue 0 overloaded, queue 1 idle -> queue 0 gains effective agents, queue 1 loses, net not above total
    eff = calc.flex_effective_agents(avail, 0.2 * avail, aht, np.array([400.0, 10.0]), **kw)
    assert eff[0] > 10 * 0.88 and eff[1] < 10 * 0.88
    assert eff.sum() <= 20 * 0.88 + 1e-9  # penalty means moved agents are less productive, never more
    # never moves more than the flex pool
    assert eff[1] >= 10 * 0.88 - 0.2 * 10 * 0.88 - 1e-9


def test_flex_penalty_applied_exactly():
    """Capacity gained by the overloaded queue = capacity lost by the donor / (1 + penalty)."""
    avail, aht = np.array([10.0, 10.0]), np.array([300.0, 300.0])
    for pen in (0.0, 0.10, 0.50):
        kw = dict(shrinkage=0.12, max_occ=0.95, penalty=pen, donor_occ=0.85)
        eff = calc.flex_effective_agents(avail, 0.2 * avail, aht, np.array([400.0, 10.0]), **kw)
        gained, lost = eff[0] - 8.8, 8.8 - eff[1]
        assert lost > 0
        assert gained == pytest.approx(lost / (1 + pen))


def test_flex_donor_keeps_target_occupancy_reserve():
    kw = dict(shrinkage=0.12, max_occ=0.95, penalty=0.10, donor_occ=0.85)
    avail, aht = np.array([10.0, 10.0]), np.array([300.0, 300.0])
    # queue 1 demand needs ~ at 85% occupancy: 10 agents * 0.88 * 0.85 * 12 contacts/h = ~89.8 contacts
    eff = calc.flex_effective_agents(avail, avail, aht, np.array([400.0, 89.0]), **kw)
    assert eff[1] == pytest.approx(10 * 0.88, rel=0.02)  # donor queue barely loses agents


def test_erlang_stability_for_large_n():
    c = calc.erlang_c(300, 280.0)
    assert 0.0 <= c <= 1.0 and not math.isnan(c)
