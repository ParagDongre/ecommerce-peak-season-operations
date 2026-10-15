# 09 - Methodology and Limitations

> **SIMULATED DATA / HYPOTHETICAL BUSINESS.** This is an independent portfolio case study about a fictional retailer ("NorthBay Mart"). It uses no Amazon data, metrics or processes, and makes no claim about any real operation. Scenario results are *modelled estimates*, not measured improvements.

## 1. What this is

A transparent simulation of customer-support demand, staffing and service for a hypothetical retailer, built to practise and demonstrate peak-season operations and workforce-planning analysis. Nothing is calibrated to any real business. Findings follow from the assumptions in `data/assumptions.csv` (60 parameters, each with unit, basis and rationale).

## 2. Data generation (`src/generate_data.py`)

1. **Orders.** Baseline 15,000/day with a weekday pattern and noise; event days at planner-forecast vs actual multiples of baseline (the forecast curve is deliberately smoother and slightly low on launch and finale).
2. **Fulfilment, cancellations, returns.** Orders above 36,000/day ship late; a carrier disruption (E4-E5) and stock-outs (E1-E2) add exceptions and cancellations; returns are initiated 3-9 days after the order (so returns contacts lag).
3. **Contacts.** Expected daily contacts per category are driven by orders, exceptions (1-2 day lag), stock-out cancellations and returns; they are spread over 16 operating hours with an evening-weighted profile (plus unforecast evening deal drops on E1, E4, E7) and drawn from a Poisson distribution with day-level over-dispersion.
4. **Handling time.** Category AHT of 240-540 s, +5% in the event, with hour-level noise.
5. **Forecast.** Baseline-week contacts-per-order x forecast orders x baseline hourly profile; planned AHT from the baseline week. It cannot anticipate lags, promo complexity, mix shifts or deal drops. Baseline-week forecast is in-sample.
6. **Roster and absence.** Greedy roster (3 eight-hour templates) against the forecast requirement. Absence is drawn per agent from a uniform lottery shared by all scenarios, so scenario differences are not noise.
7. **Reproducibility.** `numpy.random.SeedSequence(seed)` spawns independent streams for orders, contacts and absences. Same seed and parameters give identical CSVs (tested against the committed `data/`).

## 3. Core calculations (`src/calc.py`)

- Workload hours = contacts x AHT / 3600.
- Required agents = ceil( workload x (1 + buffer) / ((1 - shrinkage) x occupancy) ). Planned (scheduled basis) uses planned shrinkage 0.1728 = 1 - (1 - 0.12) x (1 - 0.06) and a 10% buffer; actual (present basis) uses 12% shrinkage and no buffer.
- **Queue model, hour by hour per queue.** Capacity = effective agents x 0.95 x 3600 / AHT. If offered load is below capacity, SLA = min(Erlang C, fluid-queue) and response = max(Erlang ASA, fluid wait); otherwise a fluid FIFO queue accumulates backlog. Backlog carries across hours and overnight. Fractional agent counts interpolate between integer Erlang results.
- **Forecast accuracy.** WAPE and bias; MAPE shown only for contrast.
- **Cross-training (S2).** 20% of available agents may move to the other queue in an hour if their own queue stays at or below target occupancy and the other cannot clear its demand; they are 10% slower there.
- **Scenarios** (`src/scenarios.py`): S1 re-rosters existing headcount with a rolling-corrected forecast using only prior days' actuals (tested for no look-ahead); S3/S4 add a 17:00-22:00 shift; S5 = S1+S2+S4; S6 = S2+S4. **Monte Carlo:** 200 replications re-draw the whole world; scenarios within a replication share demand and absences.

## 4. Validation performed

- **Automated tests** (`pytest`): hand-calculated staffing; Erlang B/C known values; monotonicity; contact conservation through the queue; WAPE/bias hand calculation; roster rules; flex-penalty exactness; absence-lottery monotonicity; no look-ahead; accounting identities; the workload-variance identity; determinism; reproduction of committed data; RACI has one accountable owner per activity.
- **Mutation check:** the core formulas (shrinkage, WAPE, capacity, Erlang C, flex penalty, S1 look-ahead, absence lottery) were deliberately broken one at a time in a scratch copy; the tests failed for each. Two initial survivors led to a stronger flex test and a corrected mutation.
- **Not validated:** the simulation against any real data. That is impossible here by design.

## 5. Calibration log (what I changed after seeing results)

This matters for honesty: some parameters were adjusted *after* a first run, so the case study's story is partly a function of calibration.

| # | First run | Problem seen | Change | Alternatives rejected |
|---|---|---|---|---|
| 1 | Single 18% shrinkage; planner ignored expected absence | Baseline week SLA only 49-87%, so event-week degradation could not be attributed to the event | Split shrinkage into 12% non-absence + planned absence allowance (planned shrinkage 0.173) | - |
| 2 | 5% planning buffer; roster over-cover weight 0.35 | Baseline still short in places; Order & Delivery queue collapsed from E2 onward and never recovered (degenerate: no scenario could be compared) | Buffer 10%, over-cover weight 0.15 (planner-policy parameters) | Variants that softened the *demand-side* drivers (stock-out contacts, delay contacts) were tested and **rejected** as they tune the outcome rather than planner behaviour |
| 3 | Scenarios S0-S4 | S1 showed no effect and the queue imbalance was visible | Added S4 (targeted capacity, same hours as S3) and S6 (ablation) **post hoc** to separate effects | - |
| 4 | Planned-vs-actual table included returns initiated | Same-day plan vs lagged returns was a timing artifact, not a variance | Removed that row | - |

Even after calibration, the event-week outcome varies a lot by seed (event SLA p10-p90 for the as-planned case: 50-75%), which is why scenarios are reported as Monte Carlo ranges.

## 6. Limitations

1. **Synthetic by construction.** Planted features (forecast bias, lags, stock-outs, absence spike, deal drops) make the results *properties of the assumptions*, not discoveries about e-commerce operations.
2. **Simplified staffing maths.** Steady-state hour; single shrinkage and occupancy constants; per-hour integer rounding; no intra-hour burstiness, abandonment, callbacks, breaks scheduling, skills routing or multichannel differences.
3. **Queue approximations.** Erlang C assumes Poisson arrivals, exponential service and infinite patience; fractional agents are interpolated; the fluid model approximates overload. Backlog is never abandoned and carries overnight.
4. **Causation.** SLA is generated from staffing and load, so correlation analyses demonstrate method, not causal proof.
5. **Scenario scope.** No training or hiring cost and lead time, overtime premiums, attrition or morale effects; paid agent-hours are the only cost proxy. Cross-training shows an upper-bound-style benefit for that reason. S3 vs S4 differences are small relative to run-to-run spread.
6. **Single event, 14 days, two queues.** Returns after E7 are outside the window. Sensitivity analysis on key parameters (absence, bias, AHT) is not yet done.
7. **Planner behaviour is assumed.** Rosters are built by a rule, not by real planners with judgement and constraints.

## 7. Reproduce

```bash
pip install -r requirements.txt
python -m src.run_pipeline      # data, analysis, scenarios, charts, risk register (about 30 s)
python -m src.build_docs        # regenerates the docs from the outputs
python -m pytest -q             # tests
streamlit run dashboard/app.py  # optional dashboard
```
