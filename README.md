# E-commerce Peak-Season Operations & Workforce Capacity Planning: Case Study

> **SIMULATED DATA / HYPOTHETICAL BUSINESS.** This is an independent portfolio case study about a fictional retailer ("NorthBay Mart"). It uses no Amazon data, metrics or processes, and makes no claim about any real operation. Scenario results are *modelled estimates*, not measured improvements.

An end-to-end, reproducible simulation of how an online retailer's support operation prepares for a 7-day sale: demand forecasting, workforce capacity, SLA monitoring, risk and dependency management, mitigation scenarios and a simulated Six Sigma DMAIC. Built as an independent portfolio project to demonstrate e-commerce operations and workforce-management analysis. **The author has no professional e-commerce operations or WFM experience; this project does not claim any.**

## Business context (hypothetical)

NorthBay Mart runs a "Winter Mega Sale" (2026-11-16 to 2026-11-22) after a baseline week. Customer contacts split into two skill queues: **Order & Delivery** (order status, delivery delay, cancel/modify) and **Returns, Payments & Product**. Support runs 07:00-23:00 on three 8-hour shift templates. Target: 80% of contacts answered within 300 seconds.

## Findings (all on SIMULATED data; properties of the stated assumptions)

1. **A reasonable total forecast hid a poor category mix.** Event contact forecast WAPE 11.5% (bias -7.0%) in total, but Order & Delivery workload was +24% vs forecast while the other queue ended with 544 surplus agent-hours. Order & Delivery had enough agent-hours over the week yet was short in 46 of 112 hours.
2. **Service failed a day *after* the trigger.** Launch day E1 met SLA; E2 collapsed (stock-outs and exceptions create contacts 1-2 days later), and the finale E7 closed with the largest backlog. Event-week SLA 67.4% vs 80% target; 3 of 7 days on target.
3. **Where capacity sits matters more than how much.** Modelled over 200 replications: reshaping rosters inside existing shifts changed SLA by -0.5 pp; cross-training +8.7 pp; the same extra hours spread evenly +14.0 pp vs targeted at the bottleneck queue +16.3 pp (*modelled estimates*; training cost unmodelled).

## Repository layout

```
data/        synthetic datasets (CSV) + assumptions.csv + operational_events_log.csv
src/         config, generator, calculations, queue simulation, analysis, scenarios, risk, charts, doc builders
analysis/    analysis tables (A-E), results.json, charts/*.png
docs/        01-10 deliverables (charter, KPI dictionary, analysis, risk register, status, RACI, DMAIC, readout, methodology, portfolio)
tests/       pytest unit and integration tests
dashboard/   Streamlit dashboard
```

## Run it

```bash
pip install -r requirements.txt
python -m src.run_pipeline      # generates data, analysis, scenarios (Monte Carlo), charts, risk register (~30 s)
python -m src.build_docs        # regenerates docs/*.md and this README from the outputs
python -m pytest -q             # run tests
streamlit run dashboard/app.py  # optional dashboard
```

Everything is deterministic for the seed in `src/config.py` (seed 42). Changing any assumption and re-running regenerates data, tables, charts and documents consistently.

## Methodology in brief

Orders and exceptions drive contacts (with lags); contacts x handling time give workload; required agents = workload / ((1 - shrinkage) x occupancy); rosters are built from the forecast; absences are drawn from a shared lottery; an hourly queue model (Erlang C when stable, fluid queue when overloaded, backlog carried over) produces SLA, response time and backlog. Forecast accuracy uses WAPE and bias. Scenarios are compared with paired Monte Carlo replications. Full detail, a calibration log and limitations: `docs/09_Methodology_and_Limitations.md`.

## Key assumptions

All 60 parameters, with unit, basis and rationale, are in `data/assumptions.csv`. Headline ones: shrinkage 12% (+ absence), target occupancy 85%, planning buffer 10%, baseline absence 6%, SLA 80/300s, fulfilment capacity 36,000 orders/day.

## Limitations (summary)

Synthetic by construction; planted effects mean findings illustrate method rather than reveal reality; simplified staffing and queue maths; correlation between shortfall and SLA is built in; no training/hiring cost or lead time; single 14-day event; some parameters were calibrated after a first run (documented). See `docs/09_Methodology_and_Limitations.md`.

## Documents

| File | Purpose |
|---|---|
| `docs/01_Project_Charter.md` | Objectives, scope, stakeholders, milestones, success criteria |
| `docs/02_KPI_Dictionary.md` | Metric definitions and formulas |
| `docs/03_Operational_Analysis.md` | Demand, capacity, SLA, variance and scenario findings |
| `docs/04_Risk_and_Mitigation_Register.csv` (+ `04b_Dependency_Tracker.csv`) | Prioritised risks, owners, dependencies, triggers |
| `docs/05_Program_Status_Report.md` | Weekly status |
| `docs/06_RACI_Matrix.csv` | Hypothetical responsibilities |
| `docs/07_Six_Sigma_DMAIC.md` | Simulated DMAIC |
| `docs/08_Executive_Readout.md` | Leadership summary and decisions |
| `docs/09_Methodology_and_Limitations.md` | Assumptions, limits, reproducibility |
| `docs/10_Portfolio_Summary.md` | Project description and CV bullets |
