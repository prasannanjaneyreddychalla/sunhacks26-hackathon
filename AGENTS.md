# AGENTS.md

## Project goal

Build a unified application security, exposure, and resilience platform. The SunHacks 2026 demo is the first validated slice.

The platform must help a user answer:

- Does the application use a selected endpoint or dependency?
- Which services, user journeys, and business capabilities depend on it?
- What is the predicted blast radius if it fails?
- Can the failure be simulated safely?
- What actually failed, to what extent, and how quickly did it recover?

The platform is not merely an infrastructure inventory or endpoint blocker. Its primary output is application-level impact.

## Platform vision

The destination is a central application security, exposure, and resilience workspace. One evidence-backed application graph connects:

- Business capabilities, user journeys, owners, criticality, and recovery objectives.
- Services, APIs, cloud resources, databases, queues, and external dependencies.
- Identities, permissions, network reachability, exposure, packages, and known vulnerabilities.
- Failure propagation, fallbacks, monitoring, administrative access, recovery paths, and experiment results.

The application is the entry point: select an application, inspect capabilities and dependencies, investigate exposure, predict impact, validate through controlled experiments, and review evidence and recommended actions.

Example questions include: Is a vulnerable service reachable, which customer capability depends on it, and what would isolation affect? If the identity provider fails, can customers log in and can engineers still access recovery systems?

Integrate existing scanners, inventories, and telemetry through collectors. Preserve provenance and limitations rather than rebuilding every tool. Every assessment must expose sources, recency, confidence, and coverage gaps. Missing or stale evidence means unknown, not healthy or secure. A confirmed dependency does not confirm a predicted failure; predictions and observations remain separate. Do not invent completeness percentages without a measurable denominator.

The hackathon is the first validated resilience path through this shared foundation. Broader security integrations remain staged later work.

## Required reading

Before planning or implementation, read:

1. `PROJECT_CONTEXT.md`
2. `PLANS.md`
3. The current repository code and tests
4. The latest recorded phase status

Treat the repository and observed test results as the source of truth. Do not claim that a feature works unless it has been run and verified.

## MVP boundary

The hackathon MVP is AWS-focused and local-first.

It should demonstrate:

- One sample application
- A small capability catalog and user journey
- LocalStack-backed AWS dependencies
- Runtime dependency evidence
- Endpoint or dependency search
- Passive blast-radius prediction
- One controlled fault experiment
- Automatic restoration
- Application-level impact measurement
- A predicted-versus-observed report

Multi-cloud support, arbitrary production fault injection, enterprise identity integrations, and advanced vulnerability correlation are later work unless the user explicitly changes the scope.

## Engineering principles

### Capability first

Model business capabilities and user journeys before infrastructure. A result such as "DynamoDB returned 503" is incomplete. The platform should explain that order creation failed while product browsing remained available.

### Evidence over assumptions

Every discovered dependency should record:

- Evidence source
- First and last observation time
- Calling component
- Target endpoint or operation
- Confidence level

Distinguish confirmed, likely, possible, and unknown relationships.

### Safe by design

Use this environment order:

1. Local emulator
2. Isolated staging
3. Production canary only with explicit approval

Never run or prepare a production fault against a live account without explicit user authorization for the exact target and experiment.

Every active experiment must have:

- Narrow target scope
- Maximum duration
- Automatic expiration
- Rollback or cleanup
- Health checks
- Audit record

Do not use shared, organization-wide DNS, firewall, IAM, NACL, or routing changes for an MVP experiment.

### Separate prediction from execution

The read-only discovery and graph-analysis path must remain useful without fault-injection permissions. Keep active experiment permissions separate and minimal.

### Be precise about security claims

Do not claim that the platform detects unknown zero-days. Package scanners identify known or newly disclosed vulnerabilities after intelligence becomes available. Runtime anomaly detection is a separate capability.

### Be precise about AWS FIS

Do not assume AWS Fault Injection Service can inject API failures into every AWS service. Verify current supported actions before documenting or implementing an FIS experiment. LocalStack Chaos API and proxy-based faults cover different cases.

## Proposed technical baseline

Use the smallest stack that can prove the MVP. The current proposal is:

- Backend: Python and FastAPI
- Frontend: React with TypeScript
- Local environment: Docker Compose
- AWS emulator: LocalStack
- Graph: Neo4j, or an in-memory graph for the earliest vertical slice
- Telemetry: OpenTelemetry plus application health probes
- Fault injection: LocalStack Chaos API first; Toxiproxy or Envoy later
- Tests: pytest for backend and focused frontend tests

This is a proposed baseline, not a license to add every component immediately. Prefer a working vertical slice over a broad incomplete architecture.

## Implementation workflow

For each phase:

1. Read the phase and its dependencies in `PLANS.md`.
2. Inspect the current repository.
3. State assumptions and unresolved decisions.
4. Define the smallest observable acceptance test.
5. Implement only the approved phase.
6. Run focused tests.
7. Run the broader available test suite.
8. Record actual evidence.
9. Update phase status and relevant documentation.
10. Stop before beginning the next phase unless the user asks to continue.

## Code quality

- Prefer simple, readable code.
- Keep integrations behind interfaces so LocalStack, proxies, and future cloud adapters can be replaced.
- Validate all experiment input.
- Use structured logs.
- Store timestamps in UTC.
- Do not commit credentials, tokens, account identifiers, or sensitive telemetry.
- Include timeouts on all network operations.
- Make cleanup idempotent.
- Include tests for failed cleanup and interrupted experiments.
- Keep application-capability identifiers stable.

## Git and external actions

Do not deploy, push branches, open pull requests, change cloud resources, or contact external systems unless explicitly requested.

Repository documentation may be updated as part of an approved implementation phase. Preserve user work and avoid unrelated changes.
