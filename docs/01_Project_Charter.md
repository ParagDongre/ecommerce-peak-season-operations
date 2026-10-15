# 01 - Project Charter: E-commerce Peak-Season Operations & Workforce Capacity Planning

> **SIMULATED DATA / HYPOTHETICAL BUSINESS.** This is an independent portfolio case study about a fictional retailer ("NorthBay Mart"). It uses no Amazon data, metrics or processes, and makes no claim about any real operation. Scenario results are *modelled estimates*, not measured improvements.

| | |
|---|---|
| **Business (hypothetical)** | NorthBay Mart, an online retailer running a 7-day "Winter Mega Sale" (2026-11-16 to 2026-11-22) |
| **Sponsor / PM (hypothetical roles)** | Finance / Leadership Sponsor; Program Manager (WFM) |
| **Status** | Simulated exercise, fully reproducible from seed 42 |

## 1. The charter at a glance: eight questions

| Question | Answer (all figures SIMULATED) |
|---|---|
| **What is the operational problem?** | The support plan, built from an order-based forecast, does not hold service levels in the event week. Event-week SLA is 67.4% against an 80% target (baseline week 92.5%); only 3 of 7 event days meet target. |
| **What evidence supports it?** | Contact forecast WAPE 11.5% (bias -7.0%) at daily-total level hides category errors of up to 51%. Order & Delivery (OD) workload ran +24% above forecast; the Returns/Payments/Product (RP) queue ended with 544 surplus agent-hours. See `03_Operational_Analysis.md`. |
| **What is the impact on service and capacity?** | 56 of 224 event group-hours were understaffed (available agents below requirement). Worst day E2 at 37.6% SLA; backlog at close of E7: 400 contacts. |
| **What decisions are needed?** | (1) Approve targeted extra peak-cover capacity (+420 paid agent-hours). (2) Approve cross-training of 20% of agents. (3) Adopt a by-queue, lag-aware forecast and a daily re-forecast rule. See `08_Executive_Readout.md`. |
| **Who owns each mitigation?** | See `04_Risk_and_Mitigation_Register.csv` (owner per action) and `06_RACI_Matrix.csv`. |
| **Dependencies and deadlines?** | See `04b_Dependency_Tracker.csv`; capacity approval and cross-training certification are needed by 2026-11-02 (T-14 days). |
| **What could prevent success?** | Approval lead time (R10), cross-training not certified in time (R08), late exception/promo data hand-offs (R02, R03), and the model itself: assumptions, not observations (see `09_Methodology_and_Limitations.md`). |
| **How is success measured and verified?** | Section 5 below: KPI targets, owners, data source and verification step. |

## 2. Objectives

1. Forecast event demand (orders and customer contacts) and quantify forecast accuracy.
2. Translate demand into required staffing, compare it with scheduled and available staffing, and quantify capacity gaps.
3. Monitor SLA, backlog, response time and handling time; identify when and why service deteriorates.
4. Compare at least three mitigation options with transparent, labelled-as-modelled estimates.
5. Package the work as program-management artifacts: risk register, dependency tracker, RACI, status report, executive readout, DMAIC.

## 3. Scope

**In scope:** daily orders and exceptions; hourly contacts by six issue categories in two skill queues; hourly required/scheduled/available staffing; hourly SLA, response time, backlog; absences; mitigation scenarios; documentation.

**Out of scope:** real company data; cost/financial modelling (only paid agent-hours are tracked); hiring lead times and training cost; omnichannel routing, abandonment and callbacks; individual agent attributes; post-event returns tail beyond E7.

## 4. Stakeholders (hypothetical roles)

| Role | Interest | Engagement |
|---|---|---|
| Finance / Leadership Sponsor | Approves capacity; wants SLA risk and trade-offs | Executive readout, decision log |
| Program Manager (WFM) | Owns plan, risks, status and escalation | Daily stand-up during event |
| Workforce Planning Lead / Analyst | Forecast, requirement, rosters | Daily re-forecast |
| Customer Support Ops Manager / Training Manager | Execution, absence, cross-training | Daily SLA/backlog review |
| Fulfilment Ops Manager | Exceptions and stock-outs that drive contacts | Daily data feed |
| Marketing Ops Liaison | Promo calendar and deal drops | 72-hour notice |
| HR / Scheduling | Shift agreements, absence process | Weekly sync |

## 5. Success criteria and verification (targets for the *simulated* operation)

| Criterion | Target | Verified by | Owner | Modelled as-planned result |
|---|---|---|---|---|
| Event-week SLA attainment | >= 80% | `C2_service_daily_total.csv`; dashboard | Customer Support Ops Manager | 67.4% (single seed); 63.5% mean across 200 replications |
| Event days meeting SLA target | >= 6 of 7 | same | Customer Support Ops Manager | 3 of 7 (single seed) |
| End-of-day backlog | <= 100 contacts any day | `C1_service_daily_by_group.csv` | Customer Support Ops Manager | 400 at close of E7 |
| Contact forecast accuracy by queue | WAPE <= 10% at queue-hour | `A2_forecast_accuracy.csv` | Workforce Planning Lead | OD 16.2%, RP 13.8% |
| Understaffed group-hours | trending down vs plan | `B1_capacity_daily_by_group.csv` | Workforce Planning Lead | 56 of 224 |
| Risks with owner and due date | 100% of High/Critical | `04_Risk_and_Mitigation_Register.csv` | Program Manager (WFM) | All 12 risks assigned |

## 6. Milestones (hypothetical calendar; E1 = 2026-11-16)

| When | Milestone | Owner |
|---|---|---|
| T-21 | Baseline week analysed; contact rates and profile learned | Workforce Planning Analyst |
| T-14 | Capacity request and cross-training plan submitted with scenario evidence | Program Manager (WFM) |
| T-10 | Promo calendar (incl. deal drops) signed off | Marketing Ops Liaison |
| T-7 | Rosters published; cross-trained agents certified | Workforce Planning Lead / Training Manager |
| T-1 | Go/no-go: dependencies D01-D09 confirmed | Program Manager (WFM) |
| E1-E7 | Daily forecast-vs-actual, SLA and backlog review; escalation per triggers | Customer Support Ops Manager |
| T+7 | Post-event review; control plan handover | Program Manager (WFM) |

## 7. Top risks (full register in `04_Risk_and_Mitigation_Register.csv`)

| ID | Risk | Score | Rating | Owner (role) | Due |
|---|---|---|---|---|---|
| R01 | Contact-mix forecast error: Order & Delivery workload under-forecast while Returns/Payments is over-planned | 25 | Critical | Workforce Planning Lead | 2026-11-09 |
| R08 | Siloed skill queues prevent moving spare capacity to the bottleneck | 20 | Critical | Customer Support Training Manager | 2026-11-02 |
| R02 | Delivery-delay contacts lag fulfilment exceptions by 1-2 days and are not in the order-based forecast | 16 | High | Operations Program Manager | 2026-11-11 |
| R06 | Backlog carry-over snowball: overnight backlog is not cleared before next day's peak | 16 | High | Customer Support Operations Manager | 2026-11-11 |
| R10 | Approval lead time for additional capacity | 12 | High | Program Manager (WFM) | 2026-11-02 |

Scoring: probability x impact, each 1-5. Where probability is computed from the Monte Carlo runs the register says so; otherwise it is labelled judgement.

## 8. Assumptions and constraints

All modelling assumptions are in `data/assumptions.csv` (60 parameters, each with unit, basis and rationale). The planted features of the scenario (forecast bias, lagged contact drivers, stock-outs, absence spike) are design choices; they make the case study analytically interesting and are **not** findings about any real business.
