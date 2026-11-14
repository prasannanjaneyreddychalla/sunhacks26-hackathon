# Implementation Plan

## Status legend

- Not started
- In progress
- Blocked
- Complete

Only one implementation phase should be in progress at a time.

## Hackathon delivery path

The hackathon goal is one polished vertical slice, not the full enterprise platform.

The critical demo path is:

`sample capability → observed dependency → endpoint search → predicted impact → LocalStack fault → measured capability impact → automatic recovery → report`

---

## Phase 0: Repository foundation

**Status:** Not started

### Objective

Create the minimal development structure and verify that contributors can run it consistently.

### In scope

- Select package structure
- Add backend and frontend skeletons
- Add Docker Compose
- Add environment example without secrets
- Add linting and test commands
- Add architecture decision record for the selected graph approach
- Add CI for basic checks if time permits

### Decisions required

- Neo4j immediately or in-memory graph for the first slice
- LocalStack edition and Chaos API availability
- Exact sample application

### Acceptance criteria

- A new contributor can start the empty application from documented commands.
- Backend health endpoint responds.
- Frontend loads.
- Tests run locally.
- No credentials are committed.

---

## Phase 1: Sample application and capability catalog

**Status:** Not started

### Objective

Build the smallest application that can demonstrate partial failure at the capability level.

### Proposed sample

An online store with:

- Product browsing
- Cart access
- Order creation

Suggested dependencies:

- DynamoDB for products or orders
- SQS for deferred order processing or fallback
- One simple API and frontend

### Acceptance criteria

- At least two capabilities work normally.
- One capability depends on DynamoDB.
- At least one capability remains available when the selected DynamoDB operation fails.
- Capability definitions have stable identifiers.
- Automated user-journey probes exist.

---

## Phase 2: LocalStack integration

**Status:** Not started

### Objective

Run the sample AWS dependencies locally and create repeatable state.

### In scope

- LocalStack container
- Resource initialization
- DynamoDB table
- SQS queue if used
- Seed data
- Readiness checks
- Cleanup and reset commands

### Acceptance criteria

- The sample application runs without a real AWS account.
- Resource creation is repeatable.
- Reset produces a known state.
- Tests verify normal DynamoDB behavior.

---

## Phase 3: Runtime evidence collection

**Status:** Not started

### Objective

Capture evidence showing which application component uses which dependency and operation.

### In scope

- OpenTelemetry or structured instrumentation
- Service identity
- Endpoint and operation
- Timestamp
- Capability or journey correlation
- Evidence persistence

### Acceptance criteria

- A normal user journey produces a dependency observation.
- The observation identifies the caller, target, operation, and capability.
- Evidence is queryable.
- Missing or ambiguous data is represented honestly.

---

## Phase 4: Dependency graph and capability mapping

**Status:** Not started

### Objective

Represent the sample application, capabilities, services, operations, and endpoints as a traversable graph.

### In scope

- Graph schema
- Entity normalization
- Relationship provenance
- Confidence values
- Graph query service
- Small visualization

### Acceptance criteria

- The graph shows a path from capability to service to AWS operation or endpoint.
- Every runtime-derived edge links to evidence.
- Duplicate observations do not create duplicate logical nodes.
- A test confirms the expected blast-radius traversal.

---

## Phase 5: Endpoint and dependency search

**Status:** Not started

### Objective

Allow a user to enter an endpoint, AWS service, or operation and understand how the application uses it.

### In scope

- Search input
- Name and endpoint normalization
- Matched graph nodes
- Evidence summary
- Calling services
- Related capabilities
- Confidence and last-seen time

### Acceptance criteria

- Searching for DynamoDB or its endpoint returns the correct dependency.
- Results show the calling component and capability.
- Unknown endpoints return "no evidence found" rather than "not used."
- The interface explains evidence blind spots.

---

## Phase 6: Passive blast-radius prediction

**Status:** Not started

### Objective

Predict capability impact without modifying the running application.

### In scope

- Mark a selected node or edge as unavailable in a simulation
- Traverse dependent paths
- Classify impact
- Show affected and unaffected capabilities
- Record the prediction for comparison

### Acceptance criteria

- The engine predicts the expected capability failure for the sample.
- It identifies at least one unaffected capability.
- Results include the reasoning path.
- Results distinguish confirmed relationships from uncertain ones.

---

## Phase 7: Controlled local fault experiment

**Status:** Not started

### Objective

Inject one safe fault against the LocalStack-backed dependency.

### First experiment

Make a selected DynamoDB operation return an error or become unavailable for a short period.

### Required guardrails

- Explicit local environment check
- Exact service and operation
- Short maximum duration
- Automatic removal
- Manual stop
- Audit record
- Idempotent cleanup

### Fallback

If LocalStack Chaos API licensing is unavailable, implement the same demonstration using a small application-side fault adapter, Envoy, or Toxiproxy. Clearly label it as an emulated dependency failure.

### Acceptance criteria

- The experiment cannot target a non-local environment.
- The fault affects only the intended dependency or operation.
- It expires automatically.
- Cleanup succeeds after normal completion and interruption.
- The application returns to normal health.

---

## Phase 8: Application-level measurement

**Status:** Not started

### Objective

Measure baseline, experiment, and recovery behavior.

### In scope

- Automated journey probes
- Success and failure counts
- Latency
- Error types
- Retry behavior
- Queue depth if used
- Experiment timeline
- Recovery time

### Acceptance criteria

- Baseline health is recorded before the fault.
- The intended capability degradation is observed.
- An unaffected capability remains healthy.
- Recovery is detected after cleanup.
- Measurements are tied to the experiment ID.

---

## Phase 9: Predicted-versus-observed report

**Status:** Not started

### Objective

Produce the primary hackathon result.

### Report contents

- Selected dependency
- Usage evidence
- Predicted capability impact
- Experiment configuration
- Actual capability impact
- Affected and unaffected journeys
- Failure propagation path
- Detection and recovery time
- Prediction mismatches
- Recommended improvement

### Acceptance criteria

- A judge can understand the result without reading raw logs.
- Prediction and observation are visually distinct.
- The report includes a complete experiment timeline.
- The report identifies at least one actionable resilience improvement.

---

## Phase 10: Demo hardening

**Status:** Not started

### Objective

Make the vertical slice reliable and understandable for a live demonstration.

### In scope

- One-command startup
- Seed and reset flow
- Clear empty, loading, and error states
- Demo script
- Failure recovery rehearsal
- Screenshots or short backup recording
- Focused security review
- Final test run

### Acceptance criteria

- The complete demo can be repeated from a clean environment.
- Startup and reset instructions are verified.
- No manual database editing is required.
- A failed experiment can be safely cleaned up.
- The demo fits the available presentation time.

---

# Post-hackathon roadmap

## Phase 11: Additional failure types

Add DNS, connection, latency, throttling, authentication, and TLS experiments through adapter interfaces.

## Phase 12: AWS staging integration

Add real AWS inventory and telemetry collectors, validate IAM and network analysis, and run explicitly approved staging experiments.

## Phase 13: Security correlation

Import SBOM, known-vulnerability, IAM, exposure, and reachability findings into the application graph.

## Phase 14: Multi-cloud and third-party dependencies

Add provider-specific collectors and normalize external SaaS, CDN, identity, and cloud relationships.

## Phase 15: Guarded production canaries

Only after strong staging evidence, add narrow canary targeting, approval workflows, alarm stop conditions, break-glass verification, and audited rollback.

# Verification expectations

A phase is complete only when:

- Its acceptance criteria are observable.
- Relevant tests have been run.
- Actual results are recorded.
- Cleanup and failure paths are checked.
- Documentation reflects the implemented behavior.
- No later phase was silently pulled into scope.
