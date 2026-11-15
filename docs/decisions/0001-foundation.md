# 0001: Start with a small, working app

This is the early foundation decision. The Quiz choice in [decision 0002](0002-pitwall-quiz-lab.md) replaces the original store idea below.

## What we chose first

Use FastAPI for the backend, React with TypeScript for the frontend, and Docker Compose to run the local services. Start with process health and a small set of checks.

Keep app features, dependencies, security findings, and recovery paths in the same overall model. Every link should have a stable ID and a clear source. An empty graph does not mean an app is safe.

The first sample idea was a store with static browsing and DynamoDB-backed orders. We expected a write failure to leave browsing and order reads available. That was a plan, not a measured result.

LocalStack would provide the local AWS services. The demo should have a free path, with a clearly labelled app-side or proxy fault if needed. Queues, scanners, cloud accounts, and active tests would be added when their next agreed step needed them.

## What still matters

Keep the first version small and easy to run. Put storage and adapters behind simple interfaces so they can be replaced later. Add a real graph when the next working example needs it; this note does not say one was built.

Process health only says the process is up. It does not show that a customer feature works. Keep read-only views separate from permission to run faults.
