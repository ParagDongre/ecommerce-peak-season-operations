"""Hour-by-hour queue simulation over (day, hour, skill-group) arrays. SIMULATED model."""
from __future__ import annotations

import numpy as np

from . import calc
from .config import Params


def group_mean_aht(arrivals: np.ndarray, workload_h: np.ndarray) -> np.ndarray:
    """Volume-weighted AHT (seconds) per group, used as a fallback for hours with zero arrivals."""
    c = arrivals.sum(axis=(0, 1))
    w = workload_h.sum(axis=(0, 1))
    return np.where(c > 0, w * 3600.0 / np.maximum(c, 1e-9), 300.0)


def simulate(p: Params, arrivals, workload_h, available, flex: bool = False) -> dict:
    """Run the queue model.

    arrivals, workload_h, available: arrays shaped (D, H, G).
      * workload_h = contacts x AHT / 3600 per group-hour (so AHT is implied)
      * available  = agents present (scheduled minus absent); shrinkage is applied here
    flex: if True, `p.flex_share` of the available agents are cross-trained and may be moved to the
    other queue each hour (see calc.flex_effective_agents).
    Backlog carries from hour to hour and overnight (documented simplification).
    """
    D, H, G = arrivals.shape
    fallback = group_mean_aht(arrivals, workload_h)
    aht = np.where(arrivals > 0, workload_h * 3600.0 / np.maximum(arrivals, 1e-9), fallback[None, None, :])
    out = {k: np.zeros((D, H, G)) for k in ("sla", "resp_sec", "handled", "backlog_end", "capacity", "eff_agents")}
    backlog = np.zeros(G)
    for d in range(D):
        for h in range(H):
            eff = available[d, h, :] * (1.0 - p.shrinkage)
            if flex and G == 2:
                eff = calc.flex_effective_agents(
                    avail=available[d, h, :],
                    flex=p.flex_share * available[d, h, :],
                    aht=aht[d, h, :],
                    demand=backlog + arrivals[d, h, :],
                    shrinkage=p.shrinkage,
                    max_occ=p.max_throughput_occupancy,
                    penalty=p.flex_aht_penalty,
                    donor_occ=p.target_occupancy,
                )
            for g in range(G):
                r = calc.hourly_service(
                    backlog[g], arrivals[d, h, g], eff[g], aht[d, h, g],
                    p.max_throughput_occupancy, p.sla_threshold_sec,
                )
                backlog[g] = r["backlog_end"]
                out["sla"][d, h, g] = r["sla"]
                out["resp_sec"][d, h, g] = r["resp_sec"]
                out["handled"][d, h, g] = r["handled"]
                out["backlog_end"][d, h, g] = r["backlog_end"]
                out["capacity"][d, h, g] = r["capacity"]
                out["eff_agents"][d, h, g] = eff[g]
    return out
