"""Integration tests: determinism, accounting identities, scenario logic, committed-data reproducibility.

These tests never write to data/, analysis/ or docs/.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src import analysis as an
from src import risk
from src.config import CATEGORIES, Params, assumptions_table
from src.generate_data import available_from_roster, build_all, generate_world
from src.scenarios import SCENARIOS, build_roster, kpis, paid_agent_hours, run_scenario
from src.simulate import simulate

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def P():
    return Params()


@pytest.fixture(scope="module")
def built(P):
    return build_all(P)


def test_params_validate(P):
    P.validate()
    assert abs(sum(P.hourly_profile) - 1) < 1e-9
    assert P.planned_shrinkage == pytest.approx(1 - (1 - P.shrinkage) * (1 - P.baseline_absence_rate))


def test_generation_is_deterministic(P):
    a, b = generate_world(P, 7), generate_world(P, 7)
    assert np.array_equal(a.contacts, b.contacts) and np.array_equal(a.roster, b.roster)
    assert np.array_equal(a.absence_u, b.absence_u)
    c = generate_world(P, 8)
    assert not np.array_equal(a.contacts, c.contacts)


def test_orders_accounting(built):
    o = built["orders_daily"]
    assert (o.fulfilment_exceptions == o.late_shipments + o.failed_deliveries + o.damaged_or_missing).all()
    assert (o.stockout_cancellations <= o.cancellations).all()
    assert len(o) == 14 and set(o.phase) == {"baseline", "event"}
    assert (o.data_label == "SIMULATED").all()


def test_all_tables_labelled_simulated(built):
    for k in ("orders_daily", "contacts_hourly", "staffing_hourly", "service_hourly", "absences_daily", "roster_plan", "operational_events_log"):
        assert (built[k].data_label == "SIMULATED").all(), k


def test_contact_table_shape_and_group_consistency(built, P):
    c = built["contacts_hourly"]
    assert len(c) == 14 * 16 * len(CATEGORIES)
    assert (c.actual_contacts >= 0).all()
    # group-level arrivals in staffing table equal category sums
    g = c.groupby(["date", "hour", "skill_group"], as_index=False).actual_contacts.sum()
    s = built["staffing_hourly"].merge(g, on=["date", "hour", "skill_group"], suffixes=("", "_c"))
    assert (s.actual_contacts == s.actual_contacts_c).all()


def test_staffing_definitions(built):
    s = built["staffing_hourly"]
    assert (s.available <= s.scheduled).all() and (s.absent == s.scheduled - s.available).all()
    assert (s.capacity_gap_agents == s.required_actual - s.available).all()
    assert (s.understaffed == (s.capacity_gap_agents > 0).astype(int)).all()
    # scheduled-basis requirement is never below the present-basis requirement for the same workload
    assert (s.required_actual_scheduled_basis >= s.required_actual).all()


def test_required_agents_in_table_matches_formula(built, P):
    s = built["staffing_hourly"]
    wl = s.actual_contacts * s.actual_aht_sec / 3600
    approx = np.ceil(wl / ((1 - P.shrinkage) * P.target_occupancy) - 1e-9)
    # AHT is rounded to 0.1 s in the CSV table, so allow a 1-agent tolerance at rounding boundaries
    assert (np.abs(approx - s.required_actual) <= 1).all()
    assert (approx == s.required_actual).mean() > 0.97


def test_queue_conserves_contacts_over_whole_run(built):
    w, sim = built["world"], built["sim"]
    assert sim["handled"].sum() + sim["backlog_end"][-1, -1, :].sum() == pytest.approx(w.arrivals.sum())
    assert ((sim["sla"] >= 0) & (sim["sla"] <= 1)).all()


def test_more_staff_never_worsens_service(built, P):
    w = built["world"]
    base = simulate(P, w.arrivals, w.workload_h, built["available"])
    plus = simulate(P, w.arrivals, w.workload_h, built["available"] + 2)
    assert plus["backlog_end"].sum() <= base["backlog_end"].sum() + 1e-6
    a = (base["sla"] * w.arrivals).sum() / w.arrivals.sum()
    b = (plus["sla"] * w.arrivals).sum() / w.arrivals.sum()
    assert b >= a - 1e-9


def test_absence_lottery_is_monotone_in_roster(P):
    w = generate_world(P, 5)
    r2 = w.roster.copy()
    r2[:, :, 0] += 3
    _, _, ab1 = available_from_roster(P, w.roster, w.absence_u)
    _, _, ab2 = available_from_roster(P, r2, w.absence_u)
    assert (ab2 >= ab1).all()  # same lottery: bigger roster can only have >= absentees
    assert (ab1 <= w.roster).all()


def test_workload_variance_identity(built):
    hf = an.hourly_frame(built["staffing_hourly"], built["service_hourly"])
    wv = an.workload_variance(hf)
    # actual - forecast = volume effect + AHT effect (rounding to 2 dp per row)
    assert wv.identity_check_hours.abs().max() < 0.05


def test_scenario_roster_rules(built, P):
    w = built["world"]
    nb = P.n_baseline_days
    s0, s1, s3, s4 = (build_roster(P, w, s) for s in ("S0", "S1", "S3", "S4"))
    assert np.array_equal(s0, w.roster)
    # S1 keeps headcount per group-day (fixed total) and leaves baseline-week rosters untouched
    assert np.array_equal(s1[:nb], w.roster[:nb])
    assert np.array_equal(s1[nb:, :, :3].sum(axis=2), w.roster[nb:, :, :3].sum(axis=2))
    # S3 / S4 add identical total paid hours (same extra agents, different queue split)
    assert paid_agent_hours(s3, nb) == paid_agent_hours(s4, nb)
    extra_h = 6 * 2 * P.n_event_days * 5  # agents x groups x days x 5h template D
    assert paid_agent_hours(s3, nb) - paid_agent_hours(s0, nb) == extra_h
    assert (s4[nb:, 1, 3] == 0).all() and (s4[nb:, 0, 3] == 12).all()


def test_scenario_s1_has_no_lookahead(P):
    """Corrected requirement for day d must not change if actuals on day d and later change."""
    from src.scenarios import corrected_requirement_curve
    w = generate_world(P, 11)
    d = P.n_baseline_days + 2
    before = corrected_requirement_curve(P, w, d, 0).copy()
    w.workload_h[d:, :, :] *= 3.0
    assert np.array_equal(before, corrected_requirement_curve(P, w, d, 0))


def test_scenario_kpis_and_ordering(P):
    w = generate_world(P, 42)
    res = {s: kpis(P, w, run_scenario(P, w, s)) for s in SCENARIOS}
    for k in res.values():
        assert 0 <= k["sla_overall"] <= 1 and k["end_of_event_backlog_contacts"] >= 0
    assert res["S2"]["paid_agent_hours"] == res["S0"]["paid_agent_hours"]  # cross-training adds no paid hours
    assert res["S4"]["sla_overall"] >= res["S0"]["sla_overall"]  # added capacity targeted at the bottleneck cannot hurt


def test_forecast_metrics_on_generated_data(built):
    o, c, s = built["orders_daily"], built["contacts_hourly"], built["staffing_hourly"]
    fa = an.forecast_accuracy(o, c, s)
    row = fa[(fa.level == "orders (daily)") & (fa.scope == "event week")].iloc[0]
    manual = (o[o.phase == "event"].actual_orders - o[o.phase == "event"].forecast_orders).abs().sum() / o[o.phase == "event"].actual_orders.sum() * 100
    assert row.wape_pct == pytest.approx(round(manual, 2))


def test_contact_mix_shares_sum_to_100(built):
    mix = an.contact_mix(built["contacts_hourly"])
    assert mix.event_share_pct.sum() == pytest.approx(100, abs=0.1)
    assert mix.cumulative_event_share_pct.iloc[-1] == pytest.approx(100, abs=0.1)
    assert mix.event_total.is_monotonic_decreasing


def test_risk_scoring_rules():
    assert [risk.prob_score(x) for x in (0.05, 0.2, 0.4, 0.6, 0.9)] == [1, 2, 3, 4, 5]
    assert risk.rating(25) == "Critical" and risk.rating(12) == "High" and risk.rating(6) == "Medium" and risk.rating(2) == "Low"


def test_raci_has_exactly_one_accountable_per_activity():
    r = risk.raci()
    roles = [c for c in r.columns if c not in ("activity", "data_label")]
    assert ((r[roles] == "A").sum(axis=1) == 1).all()
    assert ((r[roles] == "R").sum(axis=1) >= 0).all()


def test_assumptions_table_documents_every_parameter(P):
    from dataclasses import fields
    t = assumptions_table(P)
    assert set(f.name for f in fields(P)) <= set(t.parameter)
    assert (t.rationale.str.len() > 10).all() and (t.data_label == "SIMULATED").all()


@pytest.mark.skipif(not (ROOT / "data" / "orders_daily.csv").exists(), reason="data not generated yet")
def test_committed_data_reproduces_from_seed(built):
    """The CSVs in data/ must equal a fresh regeneration (reproducibility)."""
    for name in ("orders_daily", "contacts_hourly", "staffing_hourly", "service_hourly"):
        disk = pd.read_csv(ROOT / "data" / f"{name}.csv", encoding="utf-8-sig")
        fresh = built[name].copy()
        pd.testing.assert_frame_equal(disk.reset_index(drop=True), fresh.reset_index(drop=True), check_dtype=False, check_exact=False, rtol=1e-9, atol=1e-9)


def test_narrative_claims_in_docs_hold_for_default_seed(built, P):
    """The generated docs state a few qualitative claims; fail loudly if the data stops supporting them."""
    from src.analysis import hourly_frame, service_daily_total
    hf = hourly_frame(built["staffing_hourly"], built["service_hourly"])
    svc = service_daily_total(hf, P).set_index("day_label")
    o = built["orders_daily"].set_index("day_label")
    # E1 launch day holds SLA; E2 does not (the 'trouble arrives a day late' story)
    assert svc.loc["E1", "sla_attainment_pct"] >= P.sla_target * 100
    assert svc.loc["E2", "sla_attainment_pct"] < 60
    # E7 closes with the largest backlog; the lowest-SLA day is reported separately, not assumed to be E7
    ev = svc[svc.phase == "event"]
    assert ev.end_of_day_backlog_contacts.idxmax() == "E7"
    # orders: E1 and E7 are the two largest order days; E4 is the smallest event day
    eo = o[o.phase == "event"].actual_orders
    assert set(eo.nlargest(2).index) == {"E1", "E7"} or eo.idxmax() == "E7"
    assert eo.idxmin() == "E4"
    # baseline week is healthy (so event-week degradation is attributable to the event)
    assert svc[svc.phase == "baseline"].sla_attainment_pct.mean() >= P.sla_target * 100
    # OD is the bottleneck queue, RP carries surplus
    ev_hf = hf[hf.phase == "event"]
    gap = ev_hf.groupby("skill_group").capacity_gap_agents.apply(lambda s: (s > 0).sum())
    assert gap["OD"] > gap["RP"]
