# sunhacks26-hackathon

A capability-aware application resilience platform.

The project discovers what an application depends on, connects those dependencies to business capabilities and user journeys, predicts the blast radius of a failure, safely injects a controlled fault, and compares the predicted impact with the observed result.

## Hackathon MVP

The first demo should prove one complete path:

1. Run a small cloud-native sample application locally.
2. Use LocalStack for AWS services such as DynamoDB and SQS.
3. Capture runtime dependency evidence.
4. Enter or select an endpoint such as DynamoDB.
5. Show which services and application capabilities use it.
6. Predict what should fail if it becomes unavailable.
7. inject a temporary, scoped LocalStack fault.
8. Measure the actual application-level impact.
9. Restore the dependency automatically.
10. Report predicted versus observed impact.

## Start here

Codex and contributors should read these files before implementation:

- [AGENTS.md](AGENTS.md): repository rules and engineering boundaries
- [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md): product purpose, requirements, architecture, and decisions
- [PLANS.md](PLANS.md): ordered implementation phases and acceptance criteria

## Current status

Planning and repository foundation. No application code has been implemented yet.
