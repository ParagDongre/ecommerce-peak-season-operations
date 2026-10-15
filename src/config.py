"""Central assumptions for the SIMULATED peak-season case study.

Every number in this file is a *simulation assumption chosen by the project author*.
Nothing here is sourced from, or claims to represent, any real company (including Amazon).
The hypothetical retailer is called "NorthBay Mart".

Change a value here and re-run `python -m src.run_pipeline`: every dataset, chart,
number in the docs and dashboard is regenerated from this single source of truth.
"""
from __future__ import annotations

from dataclasses import dataclass, fields

import pandas as pd

DATA_LABEL = "SIMULATED"

# Support operates 07:00-22:59 (hour-of-day = start of the hour).
OPERATING_HOURS = tuple(range(7, 23))
N_HOURS = len(OPERATING_HOURS)

CATEGORIES = (
    "order_status",
    "delivery_delay",
    "cancel_modify",
    "returns_refunds",
    "payment_promo",
    "product_enquiry",
)
CATEGORY_LABELS = {
    "order_status": "Order status (where is my order)",
    "delivery_delay": "Delivery delay / exception",
    "cancel_modify": "Cancellation / modification",
    "returns_refunds": "Returns & refunds",
    "payment_promo": "Payment & promo-code issues",
    "product_enquiry": "Product & promo enquiries",
}

# Two skill queues. Agents are specialised by default (cross-training is a scenario).
SKILL_GROUPS = ("OD", "RP")
GROUP_LABELS = {"OD": "Order & Delivery", "RP": "Returns, Payments & Product"}
CATEGORY_GROUP = {
    "order_status": "OD",
    "delivery_delay": "OD",
    "cancel_modify": "OD",
    "returns_refunds": "RP",
    "payment_promo": "RP",
    "product_enquiry": "RP",
}

# Shift templates as [start_hour, end_hour) of the hour-of-day. 8-hour shifts A-C are the
# standard roster; D is a 5-hour "peak cover" shift used only in the extra-capacity scenario.
SHIFT_TEMPLATES = {"A": (7, 15), "B": (11, 19), "C": (15, 23), "D": (17, 22)}
BASE_TEMPLATES = ("A", "B", "C")
TEMPLATE_NAMES = tuple(SHIFT_TEMPLATES)
MAX_AGENTS_PER_SHIFT_DRAW = 400  # size of the pre-drawn absence lottery per shift-group-day


@dataclass(frozen=True)
class Params:
    # ---- run control -------------------------------------------------------------
    seed: int = 42
    mc_replications: int = 200
    # ---- calendar ----------------------------------------------------------------
    baseline_start: str = "2026-11-09"  # a Monday; hypothetical calendar
    n_baseline_days: int = 7
    n_event_days: int = 7
    # ---- orders ------------------------------------------------------------------
    baseline_orders_per_day: int = 15000
    baseline_dow_factor: tuple = (0.97, 0.97, 0.98, 1.00, 1.03, 1.05, 1.00)
    order_noise_sd: float = 0.03
    actual_event_multiplier: tuple = (2.6, 2.1, 1.9, 1.8, 2.0, 2.4, 3.0)
    plan_event_multiplier: tuple = (2.4, 2.0, 1.9, 1.9, 2.0, 2.3, 2.8)
    # ---- fulfilment / exceptions --------------------------------------------------
    fulfilment_capacity_orders_per_day: int = 36000
    late_share_of_excess_orders: float = 0.60
    base_late_shipment_rate: float = 0.015
    failed_delivery_rate: float = 0.006
    damaged_missing_rate: float = 0.003
    carrier_disruption_event_days: tuple = (3, 4)  # 0-indexed: E4, E5
    carrier_disruption_extra_late_rate: float = 0.03
    base_cancel_rate: float = 0.025
    base_stockout_cancel_rate: float = 0.004
    stockout_event_days: tuple = (0, 1)  # E1, E2
    stockout_extra_cancel_rate: float = 0.012
    base_return_rate: float = 0.06
    event_return_rate: float = 0.08
    return_lag_days: tuple = (3, 4, 5, 6, 7, 8, 9)
    return_lag_weights: tuple = (0.10, 0.18, 0.20, 0.18, 0.14, 0.12, 0.08)
    # ---- customer-contact generation ----------------------------------------------
    wismo_per_order: float = 0.032
    wismo_lag_weights: tuple = (0.4, 0.6)  # same day, previous day
    delay_contacts_per_exception: float = 0.55
    delay_lag_weights: tuple = (0.6, 0.4)  # 1 day and 2 days after the exception
    cancel_modify_per_order: float = 0.010
    contacts_per_stockout_cancel: float = 0.80
    contacts_per_return: float = 0.40
    payment_promo_per_order: float = 0.007
    payment_promo_event_factor: float = 1.5
    product_enquiry_per_order: float = 0.015
    product_enquiry_event_factor: float = 1.3
    contact_day_effect_sd: float = 0.04
    hourly_profile: tuple = (
        0.020, 0.030, 0.042, 0.052, 0.060, 0.062, 0.058, 0.056,
        0.058, 0.066, 0.080, 0.092, 0.098, 0.090, 0.070, 0.066,
    )
    deal_drop_event_days: tuple = (0, 3, 6)  # E1, E4, E7: evening lightning deals
    deal_drop_hours: tuple = (20, 21)
    deal_drop_uplift: float = 1.30
    # ---- handling time -------------------------------------------------------------
    aht_sec: tuple = (240, 420, 300, 480, 540, 270)  # CATEGORIES order
    event_aht_complexity_factor: float = 1.05
    aht_noise_sd: float = 0.03
    # ---- workforce planning ---------------------------------------------------------
    shrinkage: float = 0.12  # non-absence shrinkage of PRESENT agents
    target_occupancy: float = 0.85
    max_throughput_occupancy: float = 0.95
    planning_buffer: float = 0.10
    roster_over_weight: float = 0.15
    baseline_absence_rate: float = 0.06
    event_absence_rate: tuple = (0.06, 0.06, 0.12, 0.06, 0.06, 0.08, 0.08)
    # ---- service level ---------------------------------------------------------------
    sla_target: float = 0.80
    sla_threshold_sec: int = 300
    # ---- mitigation scenarios --------------------------------------------------------
    forecast_correction_lookback_days: int = 2
    forecast_correction_bounds: tuple = (0.85, 1.35)
    profile_blend_weight: float = 0.50
    flex_share: float = 0.20
    flex_aht_penalty: float = 0.10
    extra_peak_agents_per_group_day: int = 6
    extra_peak_targeted_group: str = "OD"

    @property
    def n_days(self) -> int:
        return self.n_baseline_days + self.n_event_days

    @property
    def planned_shrinkage(self) -> float:
        """Shrinkage used for *scheduling*: non-absence shrinkage combined with the planned absence allowance."""
        return 1.0 - (1.0 - self.shrinkage) * (1.0 - self.baseline_absence_rate)

    def validate(self) -> None:
        assert len(self.actual_event_multiplier) == self.n_event_days
        assert len(self.plan_event_multiplier) == self.n_event_days
        assert len(self.event_absence_rate) == self.n_event_days
        assert len(self.hourly_profile) == N_HOURS
        assert abs(sum(self.hourly_profile) - 1.0) < 1e-6, "hourly profile must sum to 1"
        assert abs(sum(self.return_lag_weights) - 1.0) < 1e-6
        assert len(self.return_lag_days) == len(self.return_lag_weights)
        assert abs(sum(self.wismo_lag_weights) - 1.0) < 1e-6
        assert abs(sum(self.delay_lag_weights) - 1.0) < 1e-6
        assert len(self.aht_sec) == len(CATEGORIES)
        assert 0 < self.target_occupancy <= self.max_throughput_occupancy < 1
        assert 0 <= self.shrinkage < 1
        assert len(self.baseline_dow_factor) == 7


# (category, unit, basis, rationale) per parameter. Rendered into data/assumptions.csv.
DESIGN = "Design choice (scenario parameter)"
CONVENTION = "Illustrative planning convention (typical range; not sourced from any company)"
SIMPLIFY = "Modelling simplification"
PARAM_DOCS: dict[str, tuple[str, str, str, str]] = {
    "seed": ("Run control", "integer", DESIGN, "Fixed seed so every dataset is reproducible."),
    "mc_replications": ("Run control", "count", DESIGN, "Monte Carlo replications (each re-draws orders, contacts, AHT and absences) used to show stochastic ranges for scenarios."),
    "baseline_start": ("Calendar", "date", DESIGN, "Hypothetical calendar; the baseline week precedes the event week."),
    "n_baseline_days": ("Calendar", "days", DESIGN, "Baseline week used to learn contact rates and hourly profile."),
    "n_event_days": ("Calendar", "days", DESIGN, "Seven-day promotional event, per the project brief."),
    "baseline_orders_per_day": ("Orders", "orders/day", DESIGN, "Scale chosen so the support team is tens of agents per hour at peak."),
    "baseline_dow_factor": ("Orders", "multiplier Mon-Sun", DESIGN, "Mild weekend lift; averages to 1.0."),
    "order_noise_sd": ("Orders", "fraction", DESIGN, "Day-level random variation in actual orders."),
    "actual_event_multiplier": ("Orders", "x baseline", DESIGN, "Actual event-day demand: launch (E1) and finale (E7) are the peaks."),
    "plan_event_multiplier": ("Orders", "x baseline", DESIGN, "Planning team's forecast curve: smoother than reality and slightly under-calls launch and finale. This is the planted forecast bias."),
    "fulfilment_capacity_orders_per_day": ("Fulfilment", "orders/day", DESIGN, "Orders above this ship late; links demand to delivery-delay contacts."),
    "late_share_of_excess_orders": ("Fulfilment", "fraction", DESIGN, "Share of over-capacity orders that dispatch late."),
    "base_late_shipment_rate": ("Fulfilment", "fraction of orders", DESIGN, "Background late-dispatch rate."),
    "failed_delivery_rate": ("Fulfilment", "fraction of orders", DESIGN, "Address/delivery-failure exceptions."),
    "damaged_missing_rate": ("Fulfilment", "fraction of orders", DESIGN, "Damaged or missing item exceptions."),
    "carrier_disruption_event_days": ("Fulfilment", "event-day index (0 = E1)", DESIGN, "Hypothetical carrier network disruption on E4-E5."),
    "carrier_disruption_extra_late_rate": ("Fulfilment", "fraction of orders", DESIGN, "Extra late-shipment rate on disruption days."),
    "base_cancel_rate": ("Cancellations", "fraction of orders", DESIGN, "Background cancellation rate (all causes)."),
    "base_stockout_cancel_rate": ("Cancellations", "fraction of orders", DESIGN, "Part of cancellations caused by stock-outs."),
    "stockout_event_days": ("Cancellations", "event-day index (0 = E1)", DESIGN, "Promo items sell out on launch days E1-E2."),
    "stockout_extra_cancel_rate": ("Cancellations", "fraction of orders", DESIGN, "Extra stock-out cancellations on those days."),
    "base_return_rate": ("Returns", "fraction of orders", DESIGN, "Share of normal orders later returned."),
    "event_return_rate": ("Returns", "fraction of orders", DESIGN, "Higher return propensity for promotional/impulse purchases."),
    "return_lag_days": ("Returns", "days after order", DESIGN, "Returns are initiated 3-9 days after the order."),
    "return_lag_weights": ("Returns", "fraction", DESIGN, "Distribution of return timing; sums to 1. Returns contacts therefore arrive after the event peak."),
    "wismo_per_order": ("Contact rates", "contacts/order", DESIGN, "'Where is my order' contacts per order placed."),
    "wismo_lag_weights": ("Contact rates", "fraction (same day, prior day)", DESIGN, "Timing of order-status contacts."),
    "delay_contacts_per_exception": ("Contact rates", "contacts/exception", DESIGN, "Delivery-exception contact propensity."),
    "delay_lag_weights": ("Contact rates", "fraction (1 day, 2 days later)", DESIGN, "Delay contacts follow the exception by 1-2 days."),
    "cancel_modify_per_order": ("Contact rates", "contacts/order", DESIGN, "Customer-initiated cancel/modify contacts."),
    "contacts_per_stockout_cancel": ("Contact rates", "contacts/cancellation", DESIGN, "Customers contacting about stock-out cancellations."),
    "contacts_per_return": ("Contact rates", "contacts/return", DESIGN, "Share of returns that generate a contact (rest self-serve)."),
    "payment_promo_per_order": ("Contact rates", "contacts/order", DESIGN, "Payment and promo-code issue contacts."),
    "payment_promo_event_factor": ("Contact rates", "x baseline rate", DESIGN, "Promo codes drive more payment/promo contacts during the event."),
    "product_enquiry_per_order": ("Contact rates", "contacts/order", DESIGN, "Product and promotion enquiries."),
    "product_enquiry_event_factor": ("Contact rates", "x baseline rate", DESIGN, "More enquiries during the event."),
    "contact_day_effect_sd": ("Contact rates", "fraction", DESIGN, "Day-level over-dispersion on top of hourly Poisson noise."),
    "hourly_profile": ("Intraday", "share of daily contacts, 07:00-22:00", DESIGN, "Evening-weighted profile typical of consumer e-commerce; sums to 1."),
    "deal_drop_event_days": ("Intraday", "event-day index (0 = E1)", DESIGN, "Evening lightning deals on E1, E4, E7 that the forecast profile does not anticipate."),
    "deal_drop_hours": ("Intraday", "hour of day", DESIGN, "Hours affected by the deal-drop uplift."),
    "deal_drop_uplift": ("Intraday", "x profile weight", DESIGN, "Uplift applied to those hours, then the profile is renormalised."),
    "aht_sec": ("Handling time", "seconds per contact", DESIGN, "Per-category average handling time (order of CATEGORIES). Returns and payment contacts take longer."),
    "event_aht_complexity_factor": ("Handling time", "x baseline AHT", DESIGN, "Promo rules and exceptions make contacts ~5% longer in the event; not in the plan."),
    "aht_noise_sd": ("Handling time", "fraction", DESIGN, "Hour-level random variation in AHT."),
    "shrinkage": ("Workforce", "fraction of present time", CONVENTION, "Breaks, coaching, meetings, system downtime for agents who are present. Absence is a separate parameter; planners schedule against planned_shrinkage = 1-(1-shrinkage)*(1-baseline_absence_rate)."),
    "target_occupancy": ("Workforce", "fraction", CONVENTION, "Planning occupancy used to compute required staffing."),
    "max_throughput_occupancy": ("Workforce", "fraction", SIMPLIFY, "Physical ceiling on occupancy in the queue model (agents cannot be 100% busy)."),
    "planning_buffer": ("Workforce", "fraction", CONVENTION, "Peak-season contingency planners add on top of forecast-based requirements (calibrated: 5% gave an unhealthy baseline week, see methodology calibration log)."),
    "roster_over_weight": ("Workforce", "weight", SIMPLIFY, "Greedy roster optimiser penalises over-cover at 15% of the weight of shortfall (calibrated from 35%, see methodology calibration log)."),
    "baseline_absence_rate": ("Workforce", "fraction of scheduled agents", DESIGN, "Background unplanned absence."),
    "event_absence_rate": ("Workforce", "fraction per event day", DESIGN, "E3 spike (hypothetical regional disruption/illness) and mild late-event fatigue on E6-E7."),
    "sla_target": ("Service level", "fraction", DESIGN, "Target share of contacts answered within the threshold."),
    "sla_threshold_sec": ("Service level", "seconds", DESIGN, "Response threshold for the SLA (blended chat/phone-style queue)."),
    "forecast_correction_lookback_days": ("Scenarios", "days", DESIGN, "Rolling forecast correction uses the trailing N event days."),
    "forecast_correction_bounds": ("Scenarios", "ratio (low, high)", DESIGN, "Caps on the correction ratio to avoid over-reacting."),
    "profile_blend_weight": ("Scenarios", "weight on observed profile", DESIGN, "Blend of observed intraday shape and the baseline profile."),
    "flex_share": ("Scenarios", "fraction of agents", DESIGN, "Share of agents cross-trained to serve both queues."),
    "flex_aht_penalty": ("Scenarios", "fraction", DESIGN, "Cross-trained agents are 10% slower on the non-primary queue."),
    "extra_peak_agents_per_group_day": ("Scenarios", "agents per group per event day", DESIGN, "Approved additional capacity on the 17:00-22:00 peak-cover shift (S3: spread evenly over both queues)."),
    "extra_peak_targeted_group": ("Scenarios", "skill group", DESIGN, "S4/S5/S6: the same total extra agents (2 x per-group number) all assigned to this queue, i.e. same paid hours as S3 but targeted at the bottleneck queue."),
}


def assumptions_table(p: Params) -> pd.DataFrame:
    """Flat assumptions table (one row per parameter) for data/assumptions.csv."""
    rows = []
    for i, f in enumerate(fields(p), start=1):
        cat, unit, basis, why = PARAM_DOCS[f.name]
        rows.append(
            {
                "id": f"A{i:02d}",
                "category": cat,
                "parameter": f.name,
                "value": str(getattr(p, f.name)),
                "unit": unit,
                "basis": basis,
                "rationale": why,
                "data_label": DATA_LABEL,
            }
        )
    rows.append(
        {
            "id": f"A{len(rows)+1:02d}", "category": "Workforce", "parameter": "planned_shrinkage (derived)",
            "value": f"{p.planned_shrinkage:.4f}", "unit": "fraction", "basis": SIMPLIFY,
            "rationale": "Derived: scheduling shrinkage = non-absence shrinkage combined with the planned (baseline) absence allowance.",
            "data_label": DATA_LABEL,
        }
    )
    return pd.DataFrame(rows)
