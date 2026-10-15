"""Matplotlib charts (PNG) for the SIMULATED case study. Palette: validated default (blue, orange, aqua)."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e3e2de"
BLUE, ORANGE, AQUA, GREY = "#2a78d6", "#eb6834", "#1baf7a", "#8a8984"
SEQ_BLUE = ["#fcfcfb", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
SEQ_ORANGE = ["#fcfcfb", "#fbe0d2", "#f6bc9f", "#f19868", "#eb6834", "#c8501f", "#9c3b13"]
WATERMARK = "SIMULATED DATA - hypothetical retailer 'NorthBay Mart'"


def _style(ax, title, ylabel=None, xlabel=None):
    ax.set_facecolor(SURFACE)
    ax.set_title(title, loc="left", fontsize=11, color=INK, fontweight="bold", pad=10)
    ax.tick_params(colors=INK2, labelsize=8.5, length=0)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.grid(axis="y", color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)
    if ylabel:
        ax.set_ylabel(ylabel, color=INK2, fontsize=9)
    if xlabel:
        ax.set_xlabel(xlabel, color=INK2, fontsize=9)


def _save(fig, path: Path, note: str = ""):
    fig.patch.set_facecolor(SURFACE)
    fig.text(0.01, 0.005, WATERMARK + (f" | {note}" if note else ""), fontsize=7, color=INK2, ha="left", va="bottom")
    fig.tight_layout(rect=(0, 0.025, 1, 1))
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)


def _cmap(colors):
    from matplotlib.colors import LinearSegmentedColormap
    return LinearSegmentedColormap.from_list("seq", colors)


def chart_orders(orders: pd.DataFrame, out: Path):
    fig, ax = plt.subplots(figsize=(9, 4.2))
    x = np.arange(len(orders))
    ax.bar(x, orders.actual_orders, color=BLUE, width=0.62, label="Actual orders")
    ax.plot(x, orders.forecast_orders, color=ORANGE, marker="o", markersize=5, linewidth=2, label="Forecast orders")
    ax.axvline(6.5, color=GREY, linewidth=1, linestyle=":")
    ax.text(6.6, ax.get_ylim()[1] * 0.97, "event starts", color=INK2, fontsize=8, va="top")
    ax.set_xticks(x, orders.day_label)
    _style(ax, "Orders: forecast vs actual (baseline week B1-B7, event week E1-E7)", "orders per day")
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v/1000:.0f}k"))
    ax.legend(frameon=False, fontsize=8.5, loc="upper left", labelcolor=INK2)
    _save(fig, out / "01_orders_forecast_vs_actual.png")


def chart_contact_heatmap(contacts: pd.DataFrame, out: Path):
    h = contacts[contacts.phase == "event"].groupby(["day_label", "hour"])["actual_contacts"].sum().unstack()
    fig, ax = plt.subplots(figsize=(9, 3.8))
    im = ax.imshow(h.values, aspect="auto", cmap=_cmap(SEQ_BLUE))
    ax.set_xticks(range(h.shape[1]), [f"{c:02d}" for c in h.columns])
    ax.set_yticks(range(h.shape[0]), h.index)
    for i in range(h.shape[0]):
        for j in range(h.shape[1]):
            v = h.values[i, j]
            ax.text(j, i, int(v), ha="center", va="center", fontsize=6.5, color="white" if v > h.values.max() * 0.55 else INK2)
    ax.set_title("Actual customer contacts by hour, event week (darker = more contacts)", loc="left", fontsize=11, color=INK, fontweight="bold", pad=10)
    ax.set_xlabel("hour of day (start of hour)", color=INK2, fontsize=9)
    ax.tick_params(colors=INK2, labelsize=8.5, length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    _save(fig, out / "02_contacts_hourly_heatmap_event.png")


def chart_contact_mix(mix: pd.DataFrame, out: Path):
    m = mix.sort_values("event_total")
    fig, ax = plt.subplots(figsize=(9, 3.8))
    y = np.arange(len(m))
    ax.barh(y - 0.2, m.baseline_avg_daily, height=0.36, color=GREY, label="Baseline week (avg/day)")
    ax.barh(y + 0.2, m.event_avg_daily, height=0.36, color=BLUE, label="Event week (avg/day)")
    for yi, (v, s) in enumerate(zip(m.event_avg_daily, m.event_share_pct)):
        ax.text(v + 15, yi + 0.2, f"{v:,.0f}  ({s:.0f}% of event contacts)", va="center", fontsize=8, color=INK2)
    ax.set_yticks(y, m.label)
    _style(ax, "Contacts by issue category: baseline vs event (avg per day)", None, "contacts per day")
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=GRID, linewidth=0.7)
    ax.set_xlim(0, m.event_avg_daily.max() * 1.45)
    ax.legend(frameon=False, fontsize=8.5, loc="lower right", labelcolor=INK2)
    _save(fig, out / "03_contact_mix_by_category.png")


def chart_forecast_error(dd: pd.DataFrame, out: Path):
    ev = dd[dd.phase == "event"]
    fig, ax = plt.subplots(figsize=(9, 3.8))
    x = np.arange(len(ev))
    ax.bar(x - 0.2, ev.order_error_pct, width=0.36, color=BLUE, label="Orders")
    ax.bar(x + 0.2, ev.contact_error_pct, width=0.36, color=ORANGE, label="Customer contacts")
    ax.axhline(0, color=INK2, linewidth=0.8)
    for xi, v in zip(x + 0.2, ev.contact_error_pct):
        ax.text(xi, v + (1.5 if v >= 0 else -1.5), f"{v:+.0f}%", ha="center", va="bottom" if v >= 0 else "top", fontsize=7.5, color=INK2)
    ax.set_xticks(x, ev.day_label)
    _style(ax, "Event week forecast error (actual vs forecast; + = under-forecast)", "% error")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left", labelcolor=INK2)
    _save(fig, out / "04_forecast_error_event.png")


def chart_capacity_heatmap(hf: pd.DataFrame, out: Path):
    ev = hf[hf.phase == "event"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8), sharey=True)
    vmax = max(1, ev.capacity_gap_agents.clip(lower=0).max())
    for ax, g, title in zip(axes, ("OD", "RP"), ("Order & Delivery queue", "Returns, Payments & Product queue")):
        t = ev[ev.skill_group == g].pivot(index="day_label", columns="hour", values="capacity_gap_agents").clip(lower=0)
        t = t.loc[[f"E{i}" for i in range(1, 8)]]
        ax.imshow(t.values, aspect="auto", cmap=_cmap(SEQ_ORANGE), vmin=0, vmax=vmax)
        ax.set_xticks(range(t.shape[1]), [f"{c:02d}" for c in t.columns], fontsize=7)
        ax.set_yticks(range(t.shape[0]), t.index)
        for i in range(t.shape[0]):
            for j in range(t.shape[1]):
                v = int(t.values[i, j])
                if v > 0:
                    ax.text(j, i, v, ha="center", va="center", fontsize=7, color="white" if v > vmax * 0.6 else INK)
        ax.set_title(title, loc="left", fontsize=10, color=INK, fontweight="bold")
        ax.tick_params(colors=INK2, length=0)
        for s in ax.spines.values():
            s.set_visible(False)
    fig.suptitle("Staffing shortfall (agents short of requirement vs available), event week. Blank = no shortfall", x=0.01, ha="left", fontsize=11, fontweight="bold", color=INK)
    _save(fig, out / "05_capacity_shortfall_heatmap.png")


def chart_required_vs_available(hf: pd.DataFrame, out: Path, days=("E2", "E5", "E7"), group="OD"):
    ev = hf[(hf.skill_group == group) & (hf.day_label.isin(days))]
    fig, axes = plt.subplots(1, len(days), figsize=(11, 3.6), sharey=True)
    for ax, d in zip(np.atleast_1d(axes), days):
        x = ev[ev.day_label == d]
        ax.plot(x.hour, x.required_actual, color=BLUE, linewidth=2, label="Required (actual workload)")
        ax.step(x.hour, x.scheduled, where="mid", color=ORANGE, linewidth=2, label="Scheduled")
        ax.step(x.hour, x.available, where="mid", color=AQUA, linewidth=2, linestyle="--", label="Available (after absence)")
        _style(ax, f"{d}", "agents" if d == days[0] else None, "hour of day")
    np.atleast_1d(axes)[0].legend(frameon=False, fontsize=7.5, loc="upper left", labelcolor=INK2)
    fig.suptitle(f"Required vs scheduled vs available agents - Order & Delivery queue", x=0.01, ha="left", fontsize=11, fontweight="bold", color=INK)
    _save(fig, out / "06_required_vs_scheduled_vs_available_OD.png")


def chart_sla_backlog(svc: pd.DataFrame, p, out: Path):
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 5.8), sharex=True, gridspec_kw={"height_ratios": [3, 2]})
    labels = list(svc.day_label.unique())
    x = np.arange(len(labels))
    for g, c, name in (("OD", BLUE, "Order & Delivery"), ("RP", ORANGE, "Returns, Payments & Product")):
        s = svc[svc.skill_group == g]
        a1.plot(x, s.sla_attainment_pct, color=c, marker="o", markersize=5, linewidth=2, label=name)
        a2.plot(x, s.end_of_day_backlog_contacts, color=c, marker="o", markersize=5, linewidth=2, label=name)
    a1.axhline(p.sla_target * 100, color=GREY, linestyle="--", linewidth=1.2)
    a1.text(0, p.sla_target * 100 + 1.5, f"SLA target {p.sla_target*100:.0f}% within {p.sla_threshold_sec}s", fontsize=8, color=INK2)
    a1.axvline(6.5, color=GREY, linestyle=":", linewidth=1)
    a2.axvline(6.5, color=GREY, linestyle=":", linewidth=1)
    a1.set_ylim(0, 105)
    _style(a1, "Daily SLA attainment by queue (arrival-weighted)", "% within threshold")
    _style(a2, "End-of-day backlog (contacts carried to next morning)", "contacts")
    a1.legend(frameon=False, fontsize=8.5, loc="lower left", labelcolor=INK2)
    a2.set_xticks(x, labels)
    _save(fig, out / "07_sla_and_backlog_daily.png")


def chart_gap_vs_sla(table: pd.DataFrame, out: Path):
    t = table[table.analysis == "overall"]
    fig, ax = plt.subplots(figsize=(8, 3.8))
    ax.bar(t.gap_bin.astype(str), t.mean_sla_pct, color=BLUE, width=0.55)
    for i, (v, n) in enumerate(zip(t.mean_sla_pct, t.group_hours)):
        ax.text(i, v + 1.5, f"{v:.0f}%  (n={n})", ha="center", fontsize=8.5, color=INK2)
    _style(ax, "Mean SLA by staffing shortfall size (event week; association, not proof of causation)", "mean SLA %")
    ax.set_ylim(0, 110)
    _save(fig, out / "08_sla_by_shortfall_bin.png")


def chart_scenarios(mc_sum: pd.DataFrame, p, out: Path):
    m = mc_sum.sort_values("scenario", ascending=False).reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(9, 4.4))
    y = np.arange(len(m))
    ax.hlines(y, m.sla_overall_p10 * 100, m.sla_overall_p90 * 100, color=BLUE, linewidth=3, alpha=0.5)
    ax.plot(m.sla_overall_mean * 100, y, "o", color=BLUE, markersize=8, markeredgecolor=SURFACE, markeredgewidth=2)
    ax.axvline(p.sla_target * 100, color=GREY, linestyle="--", linewidth=1.2)
    ax.text(p.sla_target * 100 + 0.6, -0.62, f"SLA target {p.sla_target*100:.0f}%", fontsize=8, color=INK2, va="center")
    ax.set_ylim(-0.9, len(m) - 0.4)
    for yi, (mean, s, extra) in enumerate(zip(m.sla_overall_mean, m.scenario, m.extra_paid_agent_hours)):
        ax.text(m.sla_overall_p90.iloc[yi] * 100 + 1, yi, f"{mean*100:.0f}%  (+{extra:.0f} paid agent-h)", va="center", fontsize=8, color=INK2)
    ax.set_yticks(y, [f"{s}  {d}" for s, d in zip(m.scenario, m.description)], fontsize=8)
    _style(ax, "", None, "event-week SLA % (modelled estimate)")
    fig.suptitle("Modelled event-week SLA by scenario (dot = mean, bar = p10-p90 across replications)", x=0.01, ha="left", fontsize=11, fontweight="bold", color=INK)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=GRID, linewidth=0.7)
    ax.set_xlim(35, 118)
    _save(fig, out / "09_scenario_comparison.png", "MODELLED ESTIMATES, not predictions")


def chart_workload_variance(wv: pd.DataFrame, out: Path):
    ev = wv[wv.phase == "event"].groupby("day_label", sort=False)[["volume_effect_hours", "aht_effect_hours"]].sum()
    fig, ax = plt.subplots(figsize=(9, 3.8))
    x = np.arange(len(ev))
    ax.bar(x - 0.2, ev.volume_effect_hours, width=0.36, color=BLUE, label="Volume effect (contacts vs forecast, at planned AHT)")
    ax.bar(x + 0.2, ev.aht_effect_hours, width=0.36, color=ORANGE, label="AHT effect (actual vs planned AHT)")
    ax.axhline(0, color=INK2, linewidth=0.8)
    ax.set_xticks(x, ev.index)
    _style(ax, "Event week workload variance vs plan, split into volume and AHT (agent-hours)", "agent-hours of work")
    ax.legend(frameon=False, fontsize=8, loc="upper left", labelcolor=INK2)
    _save(fig, out / "10_workload_variance_decomposition.png")


def make_all(res: dict, p, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    chart_orders(res["orders"], out)
    chart_contact_heatmap(res["contacts"], out)
    chart_contact_mix(res["mix"], out)
    chart_forecast_error(res["demand_daily"], out)
    chart_capacity_heatmap(res["hf"], out)
    chart_required_vs_available(res["hf"], out)
    chart_sla_backlog(res["service_daily"], p, out)
    chart_gap_vs_sla(res["gap_sla"], out)
    chart_scenarios(res["mc_summary"], p, out)
    chart_workload_variance(res["workload_variance"], out)
