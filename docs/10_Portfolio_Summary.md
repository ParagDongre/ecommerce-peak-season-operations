# 10 - Portfolio Summary

> **SIMULATED DATA / HYPOTHETICAL BUSINESS.** This is an independent portfolio case study about a fictional retailer ("NorthBay Mart"). It uses no Amazon data, metrics or processes, and makes no claim about any real operation. Scenario results are *modelled estimates*, not measured improvements.

## Project description (short)

An independent case study that simulates how a hypothetical online retailer prepares customer support for a seven-day sale. Using fully synthetic data, it forecasts demand, translates it into required, scheduled and available staffing by queue and hour, tracks SLA, backlog and handling time, and compares seven mitigation scenarios with Monte Carlo modelling. It is documented as a program: charter, KPI dictionary, risk and dependency registers, RACI, status report, executive readout and a simulated Six Sigma DMAIC. Built with Python (Pandas, NumPy, SciPy, Matplotlib), Streamlit and pytest; every figure is reproducible from a fixed seed.

## CV bullets (truthful, ATS-friendly)

- Built an independent, simulation-based e-commerce peak-season capacity-planning case study (Python, Pandas, NumPy, SciPy, Matplotlib, Streamlit) on a fully synthetic dataset for a hypothetical retailer, analysing demand forecast accuracy (WAPE, bias), required vs scheduled vs available staffing, and SLA, backlog and handling-time trends to identify staffing gaps by queue and hour.
- Authored program-management artifacts (project charter, KPI dictionary, prioritised risk and dependency registers, RACI, status report, executive readout) and applied a simulated Six Sigma DMAIC analysis comparing seven mitigation scenarios through Monte Carlo modelling, with documented assumptions, limitations and automated tests; all outcomes labelled as modelled estimates.

*Shorter variant (if space is tight):* Built a synthetic-data e-commerce peak-season workforce capacity-planning case study (Python, Pandas, Streamlit): forecast accuracy, staffing-gap and SLA analysis, scenario modelling, risk register and Six Sigma DMAIC; independent project, no real company data.

## Honest framing for interviews

- **Say:** "This is an independent simulation I built to learn WFM and peak-season planning. The data is synthetic, so the findings illustrate method, not real results."
- **Strongest transferable points:** separating forecast error by category and hour instead of trusting the total; noticing that a balanced weekly total hid hourly and cross-queue gaps; testing a lever (reallocation) that did *not* help and reporting that; showing ranges instead of single numbers; being explicit about what the model cannot say.
- **Do not say:** that it improved SLA, saved cost or raised productivity; that it reflects Amazon (or any real company's) operations; that you have professional WFM or e-commerce operations experience; that the Six Sigma work was a real engagement.
- **If asked "what would you do next with real data?":** validate the forecast by category on historical peaks, measure real shrinkage/occupancy/AHT by queue, test cross-skilling feasibility, and add cost and lead-time to scenarios.

## ATS term alignment (only where the work supports it)

| ATS term | What the project actually does | Evidence | Status |
|---|---|---|---|
| E-commerce Operations | Simulated order, exception, cancellation, return and contact workflows | `data/orders_daily.csv`, `operational_events_log.csv` | Supported (simulated, not professional experience) |
| Program Management | Charter, milestones, status report, decisions log, RACI | `docs/01`, `05`, `06`, `08` | Supported as documents; no real programme delivered |
| Workforce Management / WFM | Requirement, rostering, absence, scheduled vs available | `staffing_hourly.csv`, `src/calc.py` | Supported (simulated) |
| Demand Forecasting | Rate-based forecast built and evaluated against actuals | `A2_forecast_accuracy.csv` | Supported at a basic level (no time-series modelling) |
| Capacity Planning | Workload to agents, gaps by queue-hour, scenarios | `B*` and `E*` tables | Supported |
| Staffing Gaps | Shortfall and surplus agent-hours by queue and hour | `B1`, `B2`, `B3` tables | Supported |
| SLA Management | SLA, response time and backlog monitoring, thresholds, escalation | `C*` tables, `07` Control | Supported (modelled SLA) |
| KPI Reporting / Operational Reporting | KPI dictionary, daily tables, dashboard, status report | `docs/02`, `05`, dashboard | Supported |
| Forecast Accuracy | WAPE and bias with rationale | `A2` | Supported |
| Variance Analysis | Planned vs actual, ranked, volume vs AHT decomposition | `D1`, `D2`, `B5` | Supported |
| Resource Utilization | Occupancy, shrinkage, load ratio | `02` KPI dictionary | Supported (assumption-based) |
| Risk Management / Dependency Tracking | Prioritised register with owners, triggers; dependency tracker | `04`, `04b` | Supported |
| Root Cause Analysis | Causes tied to modelled evidence | `07` Analyze | Supported (simulated) |
| Process Improvement / Six Sigma DMAIC | Simulated DMAIC with DPMO and control plan | `07` | Supported (simulated; complements Yellow Belt badge) |
| Stakeholder Coordination | Hypothetical RACI and communication plan only | `06`, `05` | **Do not claim from this project.** Your real coordination experience is the SimplyPhi internship |

## Key facts (generated from the outputs)

- Event week: 238,980 orders; SLA 67.4% vs 80% target; baseline week 92.5%.
- Best modelled option (S6): mean event SLA 85.7% (p10-p90 78-92%) vs 63.5% as planned. *Modelled estimate on synthetic data; do not quote on a CV as an achieved improvement.*
