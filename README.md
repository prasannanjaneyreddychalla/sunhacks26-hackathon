# sunhacks26-hackathon

A unified application security, exposure, and resilience workspace.

The project discovers what an application depends on, connects those dependencies to business capabilities and user journeys, predicts the blast radius of a failure, safely injects a controlled fault, and compares the predicted impact with the observed result.

## Hackathon MVP

The first demo should prove one complete path:

1. Run a small cloud-native sample application locally.
2. Use LocalStack for AWS services such as DynamoDB and SQS.
3. Capture runtime dependency evidence.
4. Enter or select an endpoint such as DynamoDB.
5. Show which services and application capabilities use it.
6. Predict what should fail if it becomes unavailable.
7. Inject a temporary, scoped LocalStack fault.
8. Measure the actual application-level impact.
9. Restore the dependency automatically.
10. Report predicted versus observed impact.

## Start here

Codex and contributors should read these files before implementation:

- [AGENTS.md](AGENTS.md): repository rules and engineering boundaries
- [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md): product purpose, requirements, architecture, and decisions
- [PLANS.md](PLANS.md): ordered implementation phases and acceptance criteria

## Product direction

One evidence-backed application graph connects business capabilities, services and dependencies, security exposure, and recovery paths. Investigate a finding, understand its business consequences, predict a disruption, and validate recovery from the same application workspace. Integrate existing scanners and telemetry and always show source coverage, recency, confidence, and unknowns.

The first hackathon slice validates resilience; broader security integrations remain on the roadmap.

## Current status

Phase 0 foundation: FastAPI process health, React/TypeScript workspace shell, local Compose configuration, and basic checks. No application, collector, graph, security assessment, or experiment is connected yet. See [PLANS.md](PLANS.md) for actual verification status and [foundation decision](docs/decisions/0001-foundation.md) for selected tradeoffs.

## Run locally

Requirements: Python 3.12+, Node.js 22+, npm, and Make. Run commands from the repository root.

```sh
make setup
```

Start each server in a separate terminal:

```sh
make dev-api
```

```sh
make dev-ui
```

Open http://localhost:5173. The connection indicator should say **Platform API connected**. API documentation is at http://localhost:8000/docs; process health is at http://localhost:8000/api/health. The frontend proxies `/api` to the backend. Stop either server with Ctrl-C. Dependencies install into `backend/.venv` and `frontend/node_modules`.

## Run with Docker Compose

Requirements: Docker with Compose v2. The default starts only the platform backend and frontend:

```sh
docker compose up --build -d
docker compose ps
```

Open http://localhost:5173. For optional local AWS infrastructure:

```sh
docker compose --profile aws up -d
```

LocalStack is exposed at http://localhost:4566. Resource initialization and fault injection are later phases; no AWS account or paid LocalStack feature is needed for the foundation. Services bind to loopback. `.env.example` documents optional host port overrides; copy it to `.env` only if needed. Never supply production credentials for this local demo.

Stop and remove this project's containers:

```sh
make down
```

The frontend container runs the development server; this is a local development setup.

## Checks

```sh
make check
```

Runs Ruff lint/format checks, backend API tests, TypeScript checks, and the production frontend build. GitHub Actions runs the same checks after a push or pull request. Container startup is verified separately from these checks.
