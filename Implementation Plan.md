# LaneIQ — Implementation Plan
### Multi-Agent Freight Optimization System

---

## PROJECT SNAPSHOT

| Field | Detail |
|---|---|
| **Project Name** | FreightMind — Multi-Agent Freight Optimization System |
| **Problem** | Freight brokers and 3PLs in the UAE coordinate shipments reactively via manual processes, with no automated exception handling when port delays or flight disruptions occur. |
| **Target Industry** | Logistics / Supply Chain (UAE-primary, India-secondary) |
| **Success Condition** | Route cost reduction of 12–18% vs baseline greedy algorithm on synthetic load manifests, with exception detection lead time measurably ahead of manual monitoring. |
| **Hiring Signal** | Multi-agent orchestration with real constraint-satisfaction (OR-Tools) integrated into LLM agent handoffs — demonstrates both classical optimization and modern AI agents, a combination almost no candidate portfolio shows. |

**Core Stack:** LangGraph · OpenAI function calling · OR-Tools · MarineTraffic free-tier API · Celery · FastAPI · Streamlit · Redis · AWS EC2 t3.medium · Docker

---

## TECH STACK DECISIONS

### Core ML / AI

| Technology | Rationale | Version | Install |
|---|---|---|---|
| **LangGraph** | Chosen over CrewAI because LangGraph gives explicit state graph control with typed state schemas, which is mandatory for a system where agent handoff failures must be debuggable; CrewAI abstracts too much. | v0.2.x | `pip install langgraph` |
| **OpenAI SDK** (function calling) | Structured tool calls with enforced JSON schema; prevents hallucinated tool arguments that break OR-Tools input. | v1.x | `pip install openai` |
| **OR-Tools** | Google's constraint programming solver; chosen over custom heuristics because it handles VRP variants with time windows out of the box, which greedy algorithms cannot. | v9.10 | `pip install ortools` |

### MLOps

| Technology | Rationale | Version | Install |
|---|---|---|---|
| **MLflow** | Experiment tracking for OR-Tools parameter sweeps and agent prompt versions; gives you a model registry to version routing configs. | v2.14 | `pip install mlflow` |
| **DVC** | Pipeline versioning for synthetic data generation → feature extraction → solver runs; makes results reproducible. | v3.x | `pip install dvc dvc-s3` |

### API / Backend

| Technology | Rationale | Version | Install |
|---|---|---|---|
| **FastAPI** | Async support handles concurrent agent task submissions; Pydantic v2 enforces shipment manifest schema at the boundary. | v0.111 | `pip install fastapi uvicorn pydantic` |
| **Celery** | Async agent task execution; each optimization request spawns a Celery task so the API returns immediately and the frontend polls for results. | v5.4 | `pip install celery` |

### Frontend / Dashboard

| Technology | Rationale | Version | Install |
|---|---|---|---|
| **Streamlit** | Multipage app; sufficient for demo and hiring manager walkthrough; no React overhead for a solo build. | v1.36 | `pip install streamlit` |
| **Plotly** | Route visualization on map, cost comparison charts, ETA confidence intervals. | v5.x | `pip install plotly` |

### Database / Storage

| Technology | Rationale | Version | Install |
|---|---|---|---|
| **Redis** | Celery broker + LangGraph agent state persistence between steps; chosen over RabbitMQ for simplicity and because it doubles as a result cache. | v7.x | `pip install redis` |

### Cloud / Deployment

- **AWS EC2 t3.medium** — enough compute for OR-Tools + LangGraph + Redis on one instance for demo purposes; ECS adds complexity not worth the tradeoff on a 4-week solo build.
- **AWS S3** — DVC remote storage for versioned artifacts.
- **Docker + Docker Compose** — containerize API, Streamlit, Redis, Celery worker as separate services.

### Monitoring

| Technology | Rationale | Version | Install |
|---|---|---|---|
| **Evidently AI** | Drift detection on shipment feature distributions (weight, lanes, carrier counts) over synthetic data batches. | v0.4.x | `pip install evidently` |
| **Loguru** | Structured logging across all agents; critical for debugging multi-agent state transitions. | v0.7 | `pip install loguru` |

---

## FOLDER STRUCTURE

```
freightmind/
│
├── .github/
│   └── workflows/
│       ├── ci.yml                  # lint + test + docker build
│       └── deploy.yml              # push to ECR on merge to main
│
├── api/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app entrypoint
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── optimize.py             # POST /optimize endpoint
│   │   ├── status.py               # GET /status/{task_id}
│   │   └── health.py               # GET /health
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── shipment.py             # Pydantic input models
│   │   └── result.py               # Pydantic output models
│   └── middleware/
│       ├── __init__.py
│       └── rate_limit.py           # SlowAPI rate limiter
│
├── src/
│   ├── __init__.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── graph.py                # LangGraph state graph definition
│   │   ├── planner.py              # Planner Agent node
│   │   ├── route.py                # Route Agent node (calls OR-Tools)
│   │   ├── exception.py            # Exception Agent node (polls vessel/flight APIs)
│   │   ├── report.py               # Report Agent node (generates summary)
│   │   └── state.py                # TypedDict state schema
│   ├── solver/
│   │   ├── __init__.py
│   │   ├── vrp.py                  # OR-Tools VRP solver wrapper
│   │   ├── constraints.py          # Time window, capacity constraints
│   │   └── baseline.py             # Greedy algorithm for benchmarking
│   ├── data/
│   │   ├── __init__.py
│   │   ├── generator.py            # Synthetic shipment manifest generator
│   │   ├── vessel_api.py           # MarineTraffic free-tier wrapper
│   │   └── validator.py            # Schema validation for raw data
│   ├── features/
│   │   ├── __init__.py
│   │   └── transform.py            # Feature engineering for routing inputs
│   ├── monitoring/
│   │   ├── __init__.py
│   │   └── drift.py                # Evidently report generation
│   └── tasks/
│       ├── __init__.py
│       └── celery_app.py           # Celery app + task definitions
│
├── dashboard/
│   ├── app.py                      # Streamlit multipage entrypoint
│   ├── pages/
│   │   ├── 01_submit_shipment.py   # Shipment brief input form
│   │   ├── 02_route_map.py         # Plotly map of recommended route
│   │   ├── 03_cost_comparison.py   # OR-Tools vs greedy cost chart
│   │   ├── 04_exception_monitor.py # Live exception feed
│   │   └── 05_drift_report.py      # Evidently drift visualization
│   └── utils/
│       ├── __init__.py
│       └── api_client.py           # HTTP client to call FastAPI
│
├── pipelines/
│   ├── dvc.yaml                    # DVC pipeline stages
│   └── params.yaml                 # Solver and agent hyperparameters
│
├── config/
│   ├── settings.py                 # Pydantic BaseSettings, loads .env
│   ├── logging.py                  # Loguru configuration
│   └── agents.py                   # System prompts, tool definitions
│
├── data/
│   ├── raw/                        # Synthetic manifests (DVC-tracked)
│   ├── processed/                  # Cleaned, validated data
│   └── features/                   # Transformed routing features
│
├── models/
│   ├── solver_configs/             # Best OR-Tools parameter sets
│   └── mlflow/                     # MLflow artifact store (local)
│
├── notebooks/
│   └── 01_eda.ipynb                # EDA only — never imported by src/
│
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   ├── test_vrp.py
│   │   ├── test_generator.py
│   │   ├── test_state.py
│   │   └── test_schemas.py
│   └── integration/
│       ├── test_api.py
│       └── test_agent_graph.py
│
├── docker/
│   ├── Dockerfile.api              # FastAPI + Celery worker image
│   ├── Dockerfile.dashboard        # Streamlit image
│   └── docker-compose.yml          # Full stack: api, dashboard, redis, worker
│
├── .env.example
├── .gitignore
├── .dvcignore
├── requirements.txt
├── requirements-dev.txt
├── Makefile
└── README.md
```

---

## 4-WEEK DAILY EXECUTION PLAN

> **28 days · 4 hours/day · ~112 hours total**

---

### WEEK 1 — FOUNDATION
**Goal:** Working synthetic data generator, baseline greedy solver, OR-Tools VRP running and benchmarked locally.

---

#### DAY 1 — Project Setup
**Focus:** Repo, environment, scaffolding
**Time budget:** 4 hours

| Task | Time |
|---|---|
| Create GitHub repo, clone locally, init virtual env with Python 3.11 | ~0.5 hrs |
| Install all dependencies, commit `requirements.txt` and `requirements-dev.txt` | ~0.5 hrs |
| Build full folder structure, add `__init__.py` to every Python package | ~0.5 hrs |
| Write `config/settings.py` with Pydantic BaseSettings (OPENAI_API_KEY, REDIS_URL, MARINETRAFFIC_KEY, MLFLOW_URI, S3_BUCKET) | ~0.5 hrs |
| Write `Makefile` targets: `make install`, `make test`, `make lint`, `make run-api`, `make run-dashboard` | ~0.5 hrs |
| Write `.env.example` with all required keys, add `.env` to `.gitignore` | ~0.25 hrs |
| Write stub `README.md` with project name, problem, stack | ~0.25 hrs |
| Init DVC: `dvc init`, commit `.dvc/` | ~0.25 hrs |
| Verify: `make install` runs clean, folder structure matches Stage 3 exactly | ~0.25 hrs |

**Done when:** `git log` shows clean initial commit, `make install` exits 0, all folders exist, `.env.example` has every key.

**Tomorrow's setup:** Leave `src/data/generator.py` open — that's the first file you write tomorrow.

---

#### DAY 2 — Synthetic Data Generator
**Focus:** Produce realistic freight manifests as the project's data backbone
**Time budget:** 4 hours

| Task | Time |
|---|---|
| Write `src/data/generator.py`: generates N shipment records with fields — shipment_id, origin_port, destination_port, cargo_weight_kg, cargo_type, ready_datetime, deadline_datetime, preferred_mode (air/sea/road), estimated_value_usd | ~2 hrs |
| Use real UAE/India port names: Jebel Ali, Abu Dhabi, NSICT Mumbai, Chennai, Delhi ICD — hardcode as constants | ~0.25 hrs |
| Add realistic distributions: weight log-normal, deadlines 3–21 days, mode split 60% sea / 25% air / 15% road | ~0.5 hrs |
| Write `src/data/validator.py`: Pydantic model for a single shipment manifest, validate generator output | ~0.5 hrs |
| Save 500 records to `data/raw/manifests.json`, track with DVC: `dvc add data/raw/manifests.json` | ~0.25 hrs |
| Write `tests/unit/test_generator.py`: assert schema validity on 100 generated records | ~0.5 hrs |

**Done when:** `pytest tests/unit/test_generator.py` passes, `data/raw/manifests.json` exists and is DVC-tracked, 500 valid records confirmed.

**Tomorrow's setup:** Load `data/raw/manifests.json` at the top of the EDA notebook — don't rerun the generator.

---

#### DAY 3 — EDA
**Focus:** Understand the synthetic data before building on it
**Time budget:** 4 hours

| Task | Time |
|---|---|
| Open `notebooks/01_eda.ipynb`, load manifests | ~0.25 hrs |
| Plot: weight distribution, mode split, origin-destination pair frequency, deadline spread | ~1 hr |
| Compute: average transit time by mode (sea 14d, air 3d, road 2d), cost-per-kg estimates by mode | ~0.5 hrs |
| Identify: which port pairs have the most volume — these become the solver's primary test cases | ~0.5 hrs |
| Document findings in notebook markdown cells: 5 key observations that will inform the solver constraints | ~0.5 hrs |
| Based on EDA, define `pipelines/params.yaml`: max_cargo_weight per vehicle, time_window_slack_hours, cost_coefficients by mode | ~0.5 hrs |
| Commit notebook and params file | ~0.25 hrs |

> ⚠️ Do NOT import anything from `src/` in this notebook. EDA only.

**Done when:** Notebook runs top-to-bottom without errors, `params.yaml` populated with grounded values from EDA.

**Tomorrow's setup:** Copy the cost coefficients and port coordinates from the notebook into `src/features/transform.py` — you'll need them as constants.

---

#### DAY 4 — Feature Engineering
**Focus:** Transform raw manifests into solver-ready input format
**Time budget:** 4 hours

| Task | Time |
|---|---|
| Write `src/features/transform.py`: add port coordinates (lat/lon) as a lookup dict | ~0.5 hrs |
| Compute haversine distance between origin/destination pairs | ~0.5 hrs |
| Compute time_window: (ready_datetime, deadline_datetime) as integer hours from now | ~0.5 hrs |
| Compute cost_estimate per mode using params.yaml coefficients | ~0.5 hrs |
| Output: list of dicts ready for OR-Tools VRP input schema | ~0.5 hrs |
| Write DVC pipeline stage in `pipelines/dvc.yaml`: stage `featurize`, input `data/raw/manifests.json`, output `data/features/routing_inputs.json` | ~0.5 hrs |
| Run stage: `dvc repro featurize` | ~0.25 hrs |
| Write `tests/unit/test_schemas.py`: validate routing_inputs.json matches expected schema | ~0.25 hrs |

**Done when:** `dvc repro featurize` exits clean, `data/features/routing_inputs.json` exists, `pytest tests/unit/test_schemas.py` passes.

**Tomorrow's setup:** Pull up OR-Tools VRP quickstart docs. Tomorrow you write `src/solver/vrp.py` from scratch.

---

#### DAY 5 — Baseline Greedy Solver + OR-Tools VRP
**Focus:** Get two solvers running and producing comparable output
**Time budget:** 4 hours

| Task | Time |
|---|---|
| Write `src/solver/baseline.py`: greedy algorithm — for each shipment, pick the mode with lowest cost_estimate that fits within the deadline; O(N) complexity | ~1 hr |
| Write `src/solver/vrp.py`: OR-Tools VRP wrapper — load routing_inputs.json | ~0.25 hrs |
| Define distance callback from haversine distances | ~0.25 hrs |
| Add time window constraints from (ready, deadline) tuples | ~0.5 hrs |
| Add capacity constraints from cargo_weight | ~0.25 hrs |
| Set solver time limit to 30 seconds | ~0.25 hrs |
| Return: list of routes with assigned shipments, total cost, computation time | ~0.25 hrs |
| Run both solvers on 50 manifests, print cost comparison | ~0.5 hrs |
| Log results to MLflow: `mlflow.log_metric("greedy_cost", ...), mlflow.log_metric("ortools_cost", ...)` | ~0.5 hrs |

**Done when:** Both solvers produce output on 50 manifests, MLflow UI shows at least one run with both cost metrics.

**Tomorrow's setup:** Leave MLflow UI open. Tomorrow's job is to make OR-Tools consistently beat greedy by ≥12%.

---

#### DAY 6 — Solver Optimization
**Focus:** Tune OR-Tools parameters until cost reduction target is hit
**Time budget:** 4 hours

| Task | Time |
|---|---|
| Write `src/solver/constraints.py`: experiment with search strategies — AUTOMATIC, PATH_CHEAPEST_ARC, SAVINGS, CHRISTOFIDES — wrap each as a named config | ~1 hr |
| Run each strategy on 100 manifests, log every run to MLflow with strategy name as a tag | ~1 hr |
| Add time limit sweep: 10s, 30s, 60s — log cost vs time tradeoff | ~0.5 hrs |
| Identify best config: strategy + time limit that hits ≥12% cost reduction vs greedy | ~0.5 hrs |
| Write best config to `models/solver_configs/best_config.json` | ~0.25 hrs |
| Register config in MLflow Model Registry as "FreightSolver-v1" | ~0.25 hrs |
| Run on full 500 manifests, confirm ≥12% reduction holds | ~0.5 hrs |

**Done when:** MLflow shows ≥5 runs, best config identified, `models/solver_configs/best_config.json` written, ≥12% reduction confirmed on 500 manifests.

**Tomorrow's setup:** Pull the best_config.json into a note — you'll refactor everything into clean modules on Day 7.

---

#### DAY 7 — Week 1 Review
**Focus:** Refactor, test, clean commit
**Time budget:** 4 hours

| Task | Time |
|---|---|
| Refactor `src/solver/vrp.py` to load config from `best_config.json` rather than hardcoded values | ~0.5 hrs |
| Write `tests/unit/test_vrp.py`: test VRP solver returns valid route structure, assert cost < greedy cost on 10 manifests | ~1 hr |
| Run `make lint` (flake8 + black) and fix all issues | ~0.5 hrs |
| Run `pytest tests/` and confirm all tests pass | ~0.25 hrs |
| Write `pipelines/dvc.yaml` stage `solve`: input features, output `data/processed/routes.json` | ~0.5 hrs |
| Run `dvc repro` end-to-end: featurize → solve | ~0.5 hrs |
| Commit clean state: tag `v0.1.0-week1` | ~0.25 hrs |

**Done when:** `dvc repro` runs featurize → solve without errors, all pytest tests pass, `v0.1.0-week1` tag pushed to GitHub.

**Tomorrow's setup:** Read LangGraph quickstart — specifically TypedDict state and `add_node` / `add_edge` API. You build the graph skeleton on Day 8.

---

### WEEK 2 — AGENT ARCHITECTURE
**Goal:** Full LangGraph multi-agent system running locally end-to-end on a shipment brief.

---

#### DAY 8 — LangGraph State + Graph Skeleton
**Focus:** Define agent state and wire the graph structure
**Time budget:** 4 hours

| Task | Time |
|---|---|
| Write `src/agents/state.py`: TypedDict with fields — shipment_brief, decomposed_tasks, route_options, selected_route, exceptions, final_report, error | ~1 hr |
| Write `src/agents/graph.py`: init StateGraph, add nodes for planner, route, exception, report — add edges in sequence, set entry point | ~1 hr |
| Stub each agent node as a function that logs its name and passes state through unchanged | ~0.5 hrs |
| Run the graph on a dummy state — confirm it traverses all four nodes without error | ~0.5 hrs |
| Write `tests/unit/test_state.py`: validate state TypedDict instantiation, assert all required keys present | ~0.5 hrs |
| Commit graph skeleton | ~0.5 hrs |

**Done when:** Graph runs stub nodes end-to-end without error, `test_state.py` passes.

**Tomorrow's setup:** Planner Agent is the first real node. Prepare the system prompt in `config/agents.py` — write it tonight if you have energy.

---

#### DAY 9 — Planner Agent
**Focus:** Implement the Planner Agent that decomposes a shipment brief into tasks
**Time budget:** 4 hours

| Task | Time |
|---|---|
| Write system prompt for Planner in `config/agents.py`: role is to extract origin, destination, cargo_type, weight, deadline, preferred_mode from free-text and output structured JSON | ~0.5 hrs |
| Write `src/agents/planner.py`: accept state with shipment_brief | ~0.25 hrs |
| Call OpenAI with function calling — define tool schema matching the manifest Pydantic model | ~1.5 hrs |
| Parse function call response into state.decomposed_tasks | ~0.5 hrs |
| Handle OpenAI API errors — set state.error if call fails | ~0.5 hrs |
| Integrate into graph, run on 5 test briefs manually | ~0.5 hrs |
| Write `tests/integration/test_agent_graph.py`: test Planner node with hardcoded brief, assert decomposed_tasks is non-empty | ~0.5 hrs |

**Done when:** Planner node correctly extracts structured fields from 5 different free-text briefs, integration test passes.

**Tomorrow's setup:** Route Agent calls OR-Tools. Make sure `src/solver/vrp.py` is importable from `src/agents/route.py` — check imports work.

---

#### DAY 10 — Route Agent
**Focus:** Route Agent calls OR-Tools and returns ranked route options
**Time budget:** 4 hours

| Task | Time |
|---|---|
| Write `src/agents/route.py`: accept state.decomposed_tasks | ~0.25 hrs |
| Call `src/features/transform.py` to produce routing inputs | ~0.5 hrs |
| Call `src/solver/vrp.py` with best_config | ~0.5 hrs |
| Also run `src/solver/baseline.py` for comparison | ~0.25 hrs |
| Build state.route_options: list of dicts with {strategy, total_cost, routes, cost_reduction_vs_baseline} | ~1 hr |
| Select best option, set state.selected_route | ~0.5 hrs |
| Log cost_reduction to MLflow from within the agent | ~0.25 hrs |
| Integrate into graph, run end-to-end: Planner → Route | ~0.5 hrs |
| Extend integration test to assert selected_route is populated and cost_reduction > 0 | ~0.25 hrs |

**Done when:** Planner → Route runs on a test brief, selected_route populated with cost reduction computed, MLflow logs the metric.

**Tomorrow's setup:** Exception Agent needs the MarineTraffic API key. Get it from marinetraffic.com free tier tonight — it takes 10 minutes.

---

#### DAY 11 — Exception Agent
**Focus:** Exception Agent monitors vessel/flight data and triggers re-routing on delay
**Time budget:** 4 hours

| Task | Time |
|---|---|
| Write `src/data/vessel_api.py`: wrapper for MarineTraffic free-tier `/expectedarrivals` endpoint; returns vessel ETA for a given port | ~1 hr |
| Add fallback: if API quota exceeded, generate synthetic delay events (random 20% of sea routes delayed 24–72 hours) | ~0.5 hrs |
| Write `src/agents/exception.py`: for each route in state.selected_route, check expected arrival vs deadline | ~0.5 hrs |
| If delay detected, call Route Agent logic again with tightened time windows | ~0.5 hrs |
| Append exception events to state.exceptions: {shipment_id, exception_type, detected_at, resolution} | ~0.5 hrs |
| Integrate into graph: Route → Exception | ~0.5 hrs |
| Run end-to-end with a synthetic delay injected, confirm re-routing occurs | ~0.5 hrs |

**Done when:** Exception node detects at least one synthetic delay and appends a resolution to state.exceptions in a test run.

**Tomorrow's setup:** Report Agent is the simplest node — it just formats state into a structured output. Prepare the output schema in `api/schemas/result.py` first.

---

#### DAY 12 — Report Agent + Full Graph Run
**Focus:** Report Agent generates the customer-facing shipment summary
**Time budget:** 4 hours

| Task | Time |
|---|---|
| Write `api/schemas/result.py`: Pydantic model for the final report — selected_route summary, cost_reduction_pct, eta_confidence_interval, exceptions_detected, recommended_actions | ~0.5 hrs |
| Write `src/agents/report.py`: accept full state | ~0.25 hrs |
| Call OpenAI to generate plain-English summary (2–3 paragraphs, all values pulled from state — no hallucination) | ~1 hr |
| Serialize to result.py schema | ~0.5 hrs |
| Set state.final_report | ~0.25 hrs |
| Run full graph: Planner → Route → Exception → Report on 3 different shipment briefs | ~1 hr |
| Print final_report for each — manually verify accuracy | ~0.25 hrs |
| Extend integration test to assert final_report is non-empty string and result schema validates | ~0.25 hrs |

**Done when:** Full 4-node graph runs on 3 briefs without error, final_report is non-empty and schema-valid for all 3.

**Tomorrow's setup:** Write the Celery task wrapper for `graph.invoke()` — that's the first thing you write on Day 13.

---

#### DAY 13 — Celery Task Integration
**Focus:** Wrap the agent graph in a Celery task for async API execution
**Time budget:** 4 hours

| Task | Time |
|---|---|
| Write `src/tasks/celery_app.py`: Celery app configured with Redis as broker and backend | ~0.5 hrs |
| Define task `run_optimization(shipment_brief: str) -> dict`: calls `graph.invoke()`, returns serialized final state | ~1 hr |
| Start Redis locally via Docker: `docker run -d -p 6379:6379 redis:7` | ~0.25 hrs |
| Start Celery worker: `celery -A src.tasks.celery_app worker --loglevel=info` | ~0.25 hrs |
| Submit a test task via Python shell, poll for result with `task.get()` | ~0.5 hrs |
| Confirm result matches expected schema | ~0.25 hrs |
| Write `pipelines/dvc.yaml` evaluation stage: runs 20 test briefs, outputs `data/processed/eval_results.json` with cost reduction stats | ~1 hr |
| Run `dvc repro` full pipeline | ~0.25 hrs |

**Done when:** Celery task runs async and returns valid result, `dvc repro` full pipeline exits clean.

**Tomorrow's setup:** DVC remote setup — you need an S3 bucket name and IAM credentials before Day 14. Create the S3 bucket now.

---

#### DAY 14 — Week 2 Review + DVC Remote
**Focus:** Push pipeline to DVC remote, test reproducibility from scratch
**Time budget:** 4 hours

| Task | Time |
|---|---|
| Configure DVC S3 remote: `dvc remote add -d s3remote s3://your-bucket/freightmind` | ~0.25 hrs |
| Push all tracked data: `dvc push` | ~0.25 hrs |
| Delete `data/` directory locally, run `dvc pull` — confirm all data restores | ~0.5 hrs |
| Run `dvc repro` from clean state — confirm full pipeline runs reproducibly | ~0.5 hrs |
| Write unit tests for any untested modules in `src/` — target 70%+ coverage | ~1 hr |
| Run `pytest tests/` — all tests must pass | ~0.25 hrs |
| Run `make lint` — zero violations | ~0.25 hrs |
| Commit and tag `v0.2.0-week2` | ~0.25 hrs |
| Write `docs/architecture.md` with a text-based diagram of the agent graph flow | ~0.5 hrs |

**Done when:** `dvc pull && dvc repro` runs clean from empty data dir, all tests pass, `v0.2.0-week2` pushed.

**Tomorrow's setup:** FastAPI app. Write the router stubs in `api/routers/` — leave `optimize.py` open for Day 15.

---

### WEEK 3 — API, DASHBOARD, MLOPS
**Goal:** FastAPI serving the agent graph, Streamlit dashboard live, full Docker Compose stack running locally.

---

#### DAY 15 — FastAPI App
**Focus:** Build the prediction API with async task submission
**Time budget:** 4 hours

| Task | Time |
|---|---|
| Write `api/main.py`: init FastAPI app, include routers, configure CORS | ~0.5 hrs |
| Write `api/routers/health.py`: `GET /health` returns `{"status": "ok", "version": "1.0.0"}` | ~0.25 hrs |
| Write `api/routers/optimize.py`: `POST /optimize` accepts ShipmentRequest (Pydantic: shipment_brief str), submits Celery task, returns `{"task_id": "..."}` | ~1 hr |
| Input validation: brief must be 10–500 chars, reject empty strings | ~0.5 hrs |
| Write `api/routers/status.py`: `GET /status/{task_id}` polls Celery result, returns task state + result when complete | ~1 hr |
| Write `api/schemas/shipment.py`: ShipmentRequest model with validators | ~0.25 hrs |
| Test manually with curl or httpx: `POST /optimize`, poll `GET /status/{id}` until COMPLETE | ~0.5 hrs |

**Done when:** Full async request-poll cycle works in curl, `/health` returns 200, bad inputs return 422.

**Tomorrow's setup:** Rate limiting uses SlowAPI. Install it tonight: `pip install slowapi`.

---

#### DAY 16 — FastAPI Hardening
**Focus:** Production-grade API — rate limiting, error handling, logging
**Time budget:** 4 hours

| Task | Time |
|---|---|
| Write `api/middleware/rate_limit.py`: SlowAPI limiter, 10 requests/minute per IP on `/optimize` | ~0.5 hrs |
| Add global exception handler in `main.py`: catch unhandled exceptions, return `{"error": "internal", "detail": str(e)}` with 500 status | ~0.5 hrs |
| Add Loguru structured logging to all routers: log request body (redacted), task_id, response status | ~1 hr |
| Add request ID middleware: generate UUID per request, attach to logs and response headers | ~0.5 hrs |
| Write `tests/integration/test_api.py`: test /health, /optimize with valid input, /optimize with invalid input, /status with fake task_id | ~1 hr |
| Run all tests — confirm pass | ~0.5 hrs |

**Done when:** Rate limit returns 429 on the 11th request, all integration tests pass, Loguru outputs structured JSON logs.

**Tomorrow's setup:** Dockerfile. Have the multi-stage build pattern ready — you'll write it in one shot on Day 17.

---

#### DAY 17 — Dockerfile
**Focus:** Multi-stage Docker image for the API + Celery worker
**Time budget:** 4 hours

| Task | Time |
|---|---|
| Write `docker/Dockerfile.api` — Stage 1 (builder): Python 3.11-slim, install deps from requirements.txt | ~0.5 hrs |
| Stage 2 (runtime): copy only installed packages and src/, set non-root user `appuser` | ~0.5 hrs |
| Add `HEALTHCHECK CMD curl -f http://localhost:8000/health \|\| exit 1` | ~0.25 hrs |
| Set `CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]` | ~0.25 hrs |
| Write `docker/Dockerfile.dashboard`: single stage, Streamlit on port 8501 | ~0.5 hrs |
| Build API image locally: `docker build -f docker/Dockerfile.api -t freightmind-api .` | ~0.25 hrs |
| Run container: mount `.env`, test `/health` from host | ~0.5 hrs |
| Fix any import path issues that appear in containerized context | ~0.5 hrs |
| Confirm image size under 800MB | ~0.25 hrs |
| Commit Dockerfiles | ~0.25 hrs |

**Done when:** `docker run freightmind-api` starts and `/health` returns 200 from the host machine.

**Tomorrow's setup:** Pull up Streamlit multipage docs. Pages go in `dashboard/pages/` — naming convention matters (`01_`, `02_`).

---

#### DAY 18 — Streamlit Dashboard
**Focus:** Build all 5 dashboard pages connected to the FastAPI backend
**Time budget:** 4 hours

| Task | Time |
|---|---|
| Write `dashboard/utils/api_client.py`: httpx client with `submit_optimization()` and `poll_status()` functions | ~0.5 hrs |
| Write `dashboard/pages/01_submit_shipment.py`: text area for brief, submit button, spinner while polling, display task_id | ~0.5 hrs |
| Write `dashboard/pages/02_route_map.py`: Plotly scatter_mapbox showing origin, destination, waypoints — use Mapbox public tiles | ~1 hr |
| Write `dashboard/pages/03_cost_comparison.py`: bar chart — OR-Tools cost vs greedy cost, cost_reduction_pct metric card | ~0.5 hrs |
| Write `dashboard/pages/04_exception_monitor.py`: table of exceptions from state.exceptions with severity badge | ~0.5 hrs |
| Write `dashboard/pages/05_drift_report.py`: placeholder for Evidently HTML report embed (Day 19) | ~0.25 hrs |
| Write `dashboard/app.py`: set page config, navigation | ~0.25 hrs |
| Run locally: `streamlit run dashboard/app.py` — manually test all pages | ~0.5 hrs |

**Done when:** All 5 pages load without errors, route map displays correctly, cost comparison chart renders with real data from a test optimization run.

**Tomorrow's setup:** Evidently needs a reference dataset. Export 100 routing_inputs records as `data/processed/reference.json` before Day 19.

---

#### DAY 19 — Evidently Monitoring
**Focus:** Drift detection on shipment feature distributions
**Time budget:** 4 hours

| Task | Time |
|---|---|
| Write `src/monitoring/drift.py`: load reference dataset and current dataset (last N optimization inputs) | ~0.5 hrs |
| Build Evidently `Report` with `DataDriftPreset` and `DataQualityPreset` | ~0.5 hrs |
| Define drift threshold: alert if >30% of features show drift | ~0.5 hrs |
| Save HTML report to `data/processed/drift_report.html` | ~0.25 hrs |
| Return structured drift summary dict | ~0.25 hrs |
| Add DVC pipeline stage `monitor`: runs drift.py, outputs drift_report.html | ~0.5 hrs |
| Embed HTML report in `dashboard/pages/05_drift_report.py` using `st.components.v1.html()` | ~0.5 hrs |
| Run `dvc repro monitor`, verify report generates | ~0.5 hrs |
| Commit | ~0.25 hrs |

**Done when:** `dvc repro monitor` exits clean, drift_report.html renders in Streamlit page 05.

**Tomorrow's setup:** Write the `docker-compose.yml` on paper before coding it. Services: api, celery-worker, dashboard, redis. Draw the port mapping.

---

#### DAY 20 — Docker Compose Full Stack
**Focus:** Wire all services together, test the full stack locally
**Time budget:** 4 hours

| Task | Time |
|---|---|
| Write `docker/docker-compose.yml` — `redis`: redis:7-alpine, port 6379 | ~0.25 hrs |
| `api`: freightmind-api image, port 8000, env_file .env, depends_on redis | ~0.5 hrs |
| `celery-worker`: same freightmind-api image, override CMD to celery worker, depends_on redis | ~0.5 hrs |
| `dashboard`: freightmind-dashboard image, port 8501, env API_URL=http://api:8000 | ~0.25 hrs |
| Build all images: `docker compose build` | ~0.5 hrs |
| Start stack: `docker compose up` | ~0.25 hrs |
| Submit an optimization via Streamlit UI — confirm full cycle works through containers | ~0.5 hrs |
| Fix any network/env issues | ~0.5 hrs |
| Add healthcheck to docker-compose for api and redis services | ~0.25 hrs |
| Commit working compose file | ~0.25 hrs |

**Done when:** `docker compose up` starts all 4 services, a full optimization request submitted via Streamlit UI returns a result.

**Tomorrow's setup:** Load testing. Install `locust` in requirements-dev.txt tonight.

---

#### DAY 21 — Week 3 Review + Load Test
**Focus:** Stress test the API, fix bottlenecks, stable commit
**Time budget:** 4 hours

| Task | Time |
|---|---|
| Write `tests/locustfile.py`: 10 concurrent users, `POST /optimize` with a fixed brief, poll `/status` until complete | ~1 hr |
| Run: `locust -f tests/locustfile.py --headless -u 10 -r 2 --run-time 2m` | ~0.5 hrs |
| Identify bottleneck (likely: Celery worker is single-process — increase concurrency with `--concurrency 4`) | ~0.5 hrs |
| Fix any failures, re-run load test | ~0.5 hrs |
| Run full `pytest tests/` — all pass | ~0.25 hrs |
| Run `make lint` — zero violations | ~0.25 hrs |
| Commit and tag `v0.3.0-week3` | ~0.25 hrs |

**Done when:** Locust test completes with <5% error rate at 10 concurrent users, all tests pass, `v0.3.0-week3` pushed.

**Tomorrow's setup:** Create ECR repository in AWS Console — name it `freightmind`. Note the repository URI — you'll need it in the GitHub Actions workflow.

---

### WEEK 4 — CI/CD, CLOUD, POLISH
**Goal:** Live on AWS EC2, GitHub Actions CI/CD running, project ready to show to any hiring manager.

---

#### DAY 22 — GitHub Actions CI/CD
**Focus:** Automated lint, test, Docker build, ECR push on every merge to main
**Time budget:** 4 hours

| Task | Time |
|---|---|
| Write `.github/workflows/ci.yml`: trigger on push to main and PRs to main | ~0.5 hrs |
| Jobs: `lint` (flake8 + black --check), `test` (pytest with coverage), `build` (docker build API image) | ~1.5 hrs |
| Add `pytest --cov=src --cov-report=xml` and upload coverage artifact | ~0.5 hrs |
| Write `.github/workflows/deploy.yml`: trigger on push to main only | ~0.25 hrs |
| Configure AWS credentials from GitHub Secrets (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION) | ~0.5 hrs |
| Login to ECR, build and push `freightmind-api:${{ github.sha }}` tag | ~0.5 hrs |
| Add required GitHub Secrets: OPENAI_API_KEY, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY | ~0.25 hrs |
| Push to main, confirm CI runs green | ~0.25 hrs |

**Done when:** CI workflow shows green on GitHub Actions, Docker image tagged with commit SHA appears in ECR repository.

**Tomorrow's setup:** EC2 setup. Use `t3.medium` in `us-east-1` (same region as your ECR). Generate a key pair tonight, save the `.pem` file.

---

#### DAY 23 — AWS Infrastructure Setup
**Focus:** EC2 instance, IAM roles, security groups, ECR access configured
**Time budget:** 4 hours

| Task | Time |
|---|---|
| Launch EC2 `t3.medium`, Amazon Linux 2023, 30GB EBS | ~0.5 hrs |
| Configure security group: inbound TCP 22 (SSH), 8000 (API), 8501 (Streamlit) from 0.0.0.0/0 | ~0.25 hrs |
| Create IAM role `FreightMindEC2Role` with policies: AmazonEC2ContainerRegistryReadOnly, AmazonS3ReadOnlyAccess, CloudWatchLogsFullAccess — attach to instance | ~0.5 hrs |
| SSH into instance, install Docker and Docker Compose | ~0.5 hrs |
| Configure AWS CLI on instance: `aws ecr get-login-password \| docker login --username AWS --password-stdin <ecr-uri>` | ~0.25 hrs |
| Pull the latest image from ECR: `docker pull <ecr-uri>/freightmind-api:latest` | ~0.25 hrs |
| Create `/home/ec2-user/freightmind/.env` on the instance with all secrets | ~0.5 hrs |
| Copy `docker-compose.yml` to instance via scp | ~0.25 hrs |
| Verify `docker compose up` starts cleanly | ~0.5 hrs |
| Note the EC2 public IP — add to README as LIVE_API_URL | ~0.25 hrs |

**Done when:** `docker compose up` runs on EC2, `/health` returns 200 from your local machine hitting the EC2 public IP.

**Tomorrow's setup:** Test the full optimization flow from your local Streamlit pointed at the EC2 API. If it works — deployment is done.

---

#### DAY 24 — Cloud Deployment + Live Endpoint Test
**Focus:** Verify live endpoint, configure auto-restart, update deploy workflow
**Time budget:** 4 hours

| Task | Time |
|---|---|
| Update `docker-compose.yml` with `restart: unless-stopped` on all services | ~0.25 hrs |
| Start stack with `docker compose up -d` on EC2 | ~0.25 hrs |
| Run a full optimization request via curl against the EC2 public IP — confirm end-to-end works | ~0.5 hrs |
| Update `dashboard/utils/api_client.py` to read API_URL from env so it can point to EC2 | ~0.25 hrs |
| Update `.github/workflows/deploy.yml`: after ECR push, SSH into EC2 and run `docker compose pull && docker compose up -d` | ~1 hr |
| Push to main — confirm deploy workflow auto-updates the EC2 instance | ~0.5 hrs |
| Run a full optimization via the live Streamlit dashboard (pointed at EC2 API) | ~0.5 hrs |
| Set up CloudWatch log group — update docker-compose with `awslogs` log driver | ~0.5 hrs |
| Confirm logs appear in CloudWatch | ~0.25 hrs |

**Done when:** Pushing to main triggers CI → ECR push → EC2 pulls new image → live endpoint updated automatically. CloudWatch shows logs.

**Tomorrow's setup:** Monitoring alert. You'll wire Evidently to CloudWatch tomorrow — have the drift threshold value from Day 19 ready.

---

#### DAY 25 — Monitoring Live
**Focus:** Connect Evidently drift detection to live data, verify alerts
**Time budget:** 4 hours

| Task | Time |
|---|---|
| Modify `src/monitoring/drift.py`: persist each optimization's routing_inputs to S3 as current batch data | ~0.5 hrs |
| Write `src/monitoring/scheduled_drift.py`: pull current batch from S3, run drift report, push HTML to S3, log drift_detected to CloudWatch Metrics | ~1 hr |
| Add a CloudWatch Alarm: trigger when drift_detected = 1 for 2 consecutive periods | ~0.5 hrs |
| Deploy as a cron job on EC2: `*/30 * * * * python /app/src/monitoring/scheduled_drift.py` | ~0.5 hrs |
| Inject synthetic drift (send 10 requests with artificially extreme cargo weights) and confirm alarm triggers | ~0.5 hrs |
| Update `dashboard/pages/05_drift_report.py` to load latest HTML report from S3 | ~0.5 hrs |
| Commit and push | ~0.25 hrs |

**Done when:** Synthetic drift injection triggers CloudWatch alarm, updated drift report appears in Streamlit dashboard.

**Tomorrow's setup:** README. Pull up the `docs/architecture.md` text diagram you wrote on Day 14 — you'll convert it to a Mermaid diagram for the README.

---

#### DAY 26 — README + Architecture Diagram
**Focus:** Professional README that sells the project in 30 seconds
**Time budget:** 4 hours

| Task | Time |
|---|---|
| Write `README.md` — project name + one-line description | ~0.25 hrs |
| Business problem section (3 sentences, UAE logistics context) | ~0.25 hrs |
| Architecture diagram — Mermaid flowchart: Input Brief → Planner Agent → Route Agent (OR-Tools) → Exception Agent → Report Agent → Output Report | ~1 hr |
| Tech stack table | ~0.25 hrs |
| Results section: cost reduction % achieved, exception detection lead time, load test results | ~0.5 hrs |
| Quick start: `git clone`, `cp .env.example .env`, `docker compose up` | ~0.25 hrs |
| Live demo link (EC2 public IP or Streamlit Cloud URL) | ~0.25 hrs |
| MLflow screenshot showing experiment runs | ~0.25 hrs |
| Verify the README renders correctly on GitHub | ~0.5 hrs |
| Commit | ~0.25 hrs |

**Done when:** README renders on GitHub with Mermaid diagram displaying, live link is clickable and works, results section has real numbers.

**Tomorrow's setup:** SHAP and performance benchmarks. You'll run these on the solver output — not the LLM. Have `data/processed/routes.json` ready.

---

#### DAY 27 — Final Polish
**Focus:** SHAP for solver feature importance, performance benchmarks, repo cleanup
**Time budget:** 4 hours

| Task | Time |
|---|---|
| Add SHAP analysis: train a lightweight XGBoost model to predict OR-Tools cost from routing features (distance, weight, time_window_slack), run SHAP to explain which features drive cost | ~1.5 hrs |
| Add SHAP bar chart to `dashboard/pages/03_cost_comparison.py` as a second tab | ~0.5 hrs |
| Write `benchmarks/performance.py`: run 100 optimization requests against the live API, measure p50/p95/p99 latency, total throughput | ~0.5 hrs |
| Add benchmark results to README results section | ~0.25 hrs |
| Delete all commented-out code, `print()` debug statements, unused imports | ~0.5 hrs |
| Ensure `data/` directory in repo only has `.gitkeep` files (all real data is DVC-tracked) | ~0.25 hrs |
| Confirm `.env` is not committed (`git log --all --full-history -- .env` should return empty) | ~0.25 hrs |
| Commit clean state | ~0.25 hrs |

**Done when:** SHAP chart renders in dashboard, benchmark results show p95 latency under 30 seconds, repo is clean with no secrets or debug code.

**Tomorrow's setup:** Final end-to-end test. Write out the exact test scenario you'll run tomorrow — a specific shipment brief with known expected output.

---

#### DAY 28 — Done
**Focus:** Final validation, demo recording, release tag
**Time budget:** 4 hours

| Task | Time |
|---|---|
| Run the MLOps checklist — every unchecked item gets resolved before proceeding | ~0.5 hrs |
| Run full end-to-end test: submit shipment brief via Streamlit UI → confirm route map, cost comparison, exception monitor, drift report all load | ~0.5 hrs |
| Run `dvc repro` from clean state one final time — must exit 0 | ~0.25 hrs |
| Run `pytest tests/` — all pass | ~0.25 hrs |
| Record a 2-minute Loom: 0:00–0:20 problem statement · 0:20–1:00 agent graph running · 1:00–1:30 route map and cost chart · 1:30–2:00 exception monitor and drift report | ~1 hr |
| Push final commit, tag `v1.0.0-release` | ~0.25 hrs |
| Add Loom link to README | ~0.25 hrs |
| Make GitHub repo public | ~0.25 hrs |

**Done when:** `v1.0.0-release` is pushed, repo is public, Loom link is in the README, all checklist items are checked.

---

## MLOPS CHECKLIST

### Pipeline
- [ ] DVC pipeline runs end-to-end with `dvc repro`
- [ ] All stages (featurize, solve, monitor) have defined inputs and outputs in `dvc.yaml`
- [ ] Data versioned in DVC S3 remote
- [ ] Model artifacts (solver configs) saved and versioned in MLflow

### Experiment Tracking
- [ ] MLflow tracking server running (local or remote)
- [ ] All solver runs logged with strategy name, time_limit, cost metrics
- [ ] Best solver config registered in MLflow Model Registry as FreightSolver-v1
- [ ] Evaluation metrics exported as DVC metrics in `data/processed/eval_results.json`

### Agent System
- [ ] LangGraph graph traverses all 4 nodes without error on 10 different briefs
- [ ] Planner Agent correctly extracts structured fields from free-text input
- [ ] Route Agent calls OR-Tools and returns cost_reduction > 0 vs greedy baseline
- [ ] Exception Agent detects synthetic delay and appends resolution to state
- [ ] Report Agent generates schema-valid, non-hallucinated final report
- [ ] State TypedDict validated at entry and exit of each node

### API
- [ ] FastAPI app runs locally on port 8000
- [ ] `POST /optimize` accepts ShipmentRequest and returns task_id
- [ ] `GET /status/{task_id}` returns result when Celery task completes
- [ ] `GET /health` returns 200
- [ ] Input validation rejects briefs under 10 chars or over 500 chars with 422
- [ ] Rate limiting returns 429 on 11th request within 1 minute
- [ ] Non-root user (`appuser`) in Dockerfile
- [ ] Request IDs logged on every request

### Monitoring
- [ ] Evidently drift report generates without errors on reference vs current data
- [ ] Drift threshold defined as >30% features drifted
- [ ] CloudWatch alarm triggers when drift detected
- [ ] Drift report visible in Streamlit page 05

### CI/CD
- [ ] GitHub Actions `ci.yml` triggers on push to main
- [ ] Lint stage (flake8 + black) passes
- [ ] Test stage (pytest) passes
- [ ] Docker build stage succeeds
- [ ] `deploy.yml` pushes image to ECR with SHA tag on merge to main
- [ ] EC2 auto-pulls new image on deploy

### Cloud
- [ ] EC2 t3.medium running in AWS
- [ ] All 4 Docker containers live on EC2 via docker compose
- [ ] Live `/health` endpoint responds from public IP
- [ ] CloudWatch log group capturing all container stdout
- [ ] S3 bucket storing DVC artifacts and drift reports
- [ ] IAM role attached to EC2 (no hardcoded AWS credentials on instance)

### Final
- [ ] README complete with Mermaid architecture diagram
- [ ] Live link in README and working
- [ ] Loom demo link in README
- [ ] GitHub repo public with clean commit history
- [ ] No `.env` file in git history
- [ ] No `print()` debug statements in `src/`
- [ ] `v1.0.0-release` tag pushed

---

## RISK FLAGS

### Risk 1 — OR-Tools cost reduction gap too small
> **RISK:** OR-Tools VRP fails to reach 12% cost reduction vs greedy on the synthetic dataset — the gap may be smaller because the synthetic data doesn't have enough routing complexity (few vehicles, simple port pairs).

| Field | Detail |
|---|---|
| **Likelihood** | High |
| **Happens at** | Day 6 |
| **Fix** | On Day 3 EDA, deliberately design the synthetic generator to create complex scenarios — multi-stop consolidation opportunities, shipments with tight time windows that force mode switching. The OR-Tools advantage only shows on hard instances. If Day 6 still misses the target, add a vehicle capacity constraint that the greedy ignores — this alone typically forces a 15%+ gap. |

---

### Risk 2 — LangGraph state corruption between agent nodes
> **RISK:** LangGraph agent graph produces inconsistent state between nodes — specifically, the Route Agent receives malformed decomposed_tasks from the Planner because OpenAI function calling returns an unexpected schema variant.

| Field | Detail |
|---|---|
| **Likelihood** | High |
| **Happens at** | Day 10 |
| **Fix** | On Day 9, add strict JSON schema validation at the Planner node exit using `jsonschema.validate()` before writing to state. If validation fails, retry the OpenAI call once with an explicit correction prompt. Never let malformed state propagate to OR-Tools — the solver will crash silently on bad input types. |

---

### Risk 3 — MarineTraffic API quota exhausted during demo
> **RISK:** MarineTraffic free-tier API rate limit (100 calls/day) exhausted during demo, breaking the Exception Agent and making the live demo look broken.

| Field | Detail |
|---|---|
| **Likelihood** | Medium |
| **Happens at** | Day 24 (live deployment) or any demo session |
| **Fix** | On Day 11, build the synthetic delay fallback as the primary path, not the fallback. Wrap the MarineTraffic call in a feature flag `USE_LIVE_VESSEL_API=false` in `.env`. Default to synthetic delays in all demo contexts. Only enable live API for development testing. Document this clearly in the README so hiring managers understand it's an intentional demo choice, not a limitation. |
