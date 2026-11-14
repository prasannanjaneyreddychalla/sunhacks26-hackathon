# 0001: A small foundation for the shared application graph

Status: Accepted for the first vertical slice.

The product combines application security, exposure, and resilience through evidence linked to business capabilities. The hackathon demonstrates one end-to-end resilience path.

## Decisions

- Use FastAPI and React/TypeScript, with a same-origin `/api` proxy for local development. The foundation exposes process health only.
- Start Phase 4 with an in-memory graph behind a repository interface. Preserve stable entity IDs, typed relationships, evidence references, source, observation times, and confidence. Persistence and Neo4j can be added behind that interface when required. No graph implementation is claimed in Phase 0.
- Keep business, application, security, and recovery entities in the same conceptual model. Add collectors incrementally, including explicit coverage gaps; an empty graph is not evidence of safety.
- Use static product browsing and DynamoDB-backed order reads/writes as the sample. A scoped `PutItem` failure should leave browsing and reads available. This remains a hypothesis until measured.
- Provide an optional LocalStack container for local DynamoDB. Initialize resources in Phase 2. Check paid Chaos API availability in Phase 7 and retain a labeled application-side fallback; no paid feature is required for the demo.
- Defer SQS, scanner integrations, cloud accounts, and active experiments until their planned phases.

## Consequences

The first graph will lose state on restart and support one local process. A durable evidence store and multi-user isolation are required before broader usage. The current frontend is a development shell, and the API health response does not assess a customer application. Dependency discovery and experiment permissions remain separate when those integrations arrive.
