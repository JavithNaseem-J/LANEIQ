# LANEIQ — System Architecture

## Overview

LANEIQ is a production-grade AI freight routing system that combines OR-Tools VRP
optimisation with a LangGraph multi-agent pipeline to convert free-text shipment briefs
into cost-optimised, exception-aware routing plans.

---

## Agent Graph Flow

```
                        ┌─────────────────────────────────────────┐
                        │              AgentState                 │
                        │  shipment_brief  │  decomposed_tasks    │
                        │  route_options   │  selected_route      │
                        │  exceptions      │  final_report        │
                        │  error           │                      │
                        └─────────────────────────────────────────┘

  [START]
    │
    ▼
┌──────────┐   Groq llama-3.3-70b-versatile        decomposed_tasks
│ PLANNER  │ ─── tool-calling (extract_shipment) ──► [{origin, destination,
│  Agent   │                                           cargo_type, weight_kg,
└──────────┘                                           deadline, mode}]
    │
    ▼
┌──────────┐   OR-Tools VRP + Greedy Baseline       route_options / selected_route
│  ROUTE   │ ─── runs both solvers, picks lowest ──► {strategy, total_cost,
│  Agent   │     cost, logs to MLflow                 routes, cost_reduction_pct}
└──────────┘
    │
    ▼
┌──────────┐   MarineTraffic API / Synthetic ETAs   exceptions
│EXCEPTION │ ─── checks vessel ETA vs deadline   ──► [{shipment_id, delay_hours,
│  Agent   │     re-routes delayed shipments           original_mode, new_mode}]
└──────────┘
    │
    ▼
┌──────────┐   Groq llama-3.3-70b-versatile        final_report (JSON)
│  REPORT  │ ─── generates prose summary         ──► OptimisationResult schema
│  Agent   │     serialised to Pydantic model
└──────────┘
    │
    ▼
  [END]
```

---

## DVC Pipeline (Batch Mode)

```
  data/raw/manifests.json  (5,000 shipments)
           │
           ▼
     [featurize]  src/features/transform.py
           │       Haversine distances, time windows, per-mode costs
           ▼
  data/features/routing_inputs.json
           │
           ▼
       [solve]    src/solver/solve_stage.py
           │       OR-Tools VRP in batches of 500
           ▼
  data/processed/routes.json   (150 vehicles, ~$3.8M total cost)
           │
           ▼
      [evaluate]  src/tasks/eval_stage.py
           │       20 representative briefs through the full agent graph
           ▼
  data/processed/eval_results.json
```

---

## Component Map

```
f:/DSML/LANEIQ/
├── src/
│   ├── agents/
│   │   ├── state.py          AgentState TypedDict
│   │   ├── graph.py          LangGraph StateGraph — wires all 4 nodes
│   │   ├── planner.py        Planner Agent — Groq tool-calling
│   │   ├── route.py          Route Agent   — OR-Tools + baseline
│   │   ├── exception.py      Exception Agent — vessel ETA + re-routing
│   │   └── report.py         Report Agent  — Groq prose + Pydantic schema
│   ├── solver/
│   │   ├── vrp.py            OR-Tools CVRPTW solver (config-driven)
│   │   ├── baseline.py       Greedy per-kg baseline solver
│   │   └── solve_stage.py    DVC solve stage entry-point
│   ├── features/
│   │   └── transform.py      Manifest → routing_inputs featurizer
│   ├── data/
│   │   ├── generator.py      Synthetic manifest generator (5,000 shipments)
│   │   └── vessel_api.py     MarineTraffic wrapper + synthetic delay fallback
│   └── tasks/
│       ├── celery_app.py     Async Celery task wrapping pipeline.invoke()
│       └── eval_stage.py     DVC evaluate stage (20 briefs)
├── api/
│   └── schemas/
│       └── result.py         OptimisationResult Pydantic output schema
├── config/
│   ├── agents.py             System prompts + tool schemas (Planner)
│   └── settings.py           Pydantic Settings (env vars)
├── models/
│   └── solver_configs/
│       └── best_config.json  Optimal solver config (PATH_CHEAPEST_ARC, 30s)
├── pipelines/
│   ├── dvc.yaml              3-stage DVC pipeline
│   └── params.yaml           Cost coefficients + solver params
└── tests/
    ├── unit/                 14+ pure unit tests (no API calls)
    └── integration/          24+ integration tests (Groq API)
```

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **LangGraph** for orchestration | Explicit state machine — easy to add conditional edges (re-routing, error recovery) |
| **Groq** (llama-3.3-70b) | Fast inference, native tool-calling, free tier sufficient for dev |
| **OR-Tools CVRPTW** | Industry-standard VRP solver; 64% cost reduction over greedy on 5,000 shipments |
| **Config-driven solver** | `best_config.json` decouples hyperparameters from code; A/B-testable without deploys |
| **Synthetic delay fallback** | 20% deterministic delays (hash-seeded per shipment_id) ensure Exception Agent is always testable |
| **Celery + Redis** | Async task queue enables non-blocking API responses; eager mode for dev/test |
| **DVC** | Full pipeline reproducibility — `dvc repro` rebuilds from raw manifests to eval report |
| **MLflow** | Experiment tracking for solver strategy sweeps; best config auto-registered as `FreightSolver-v1` |

---

## Cost Performance

| Mode | 5,000 Manifests | vs Greedy Baseline |
|---|---|---|
| Greedy Baseline | ~$5.6M | — |
| OR-Tools VRP (PATH_CHEAPEST_ARC, 30s) | ~$2.0M | **~64% reduction** |

*Measured on Day 6 strategy sweep logged to MLflow.*
