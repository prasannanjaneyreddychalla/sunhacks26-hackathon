# Working on Pitwall

Pitwall helps people see what breaks when an app loses a dependency, what still works, and what happens after traffic comes back. SunHacks 2026 is the first demo.

Keep the language plain. Explain changes as you would to a teammate. Markdown should use short sentences, simple words, and useful examples. Explain a technical term when it matters; leave it out when it does not.

## Read before making changes

Read `README.md`, `PROJECT_CONTEXT.md`, `PLANS.md`, and the code and tests for the part you are changing. Check the latest test notes too.

The code and tests tell us what works today. The wider plan is not a list of finished features. Do not say something works until it has been run and checked.

## Focus on what the app can do

Show the effect on real features. "The score was never saved" is more useful than just "DynamoDB returned 503."

Keep these separate:

- What the source suggests will happen.
- What we saw in requests, logs, and feature checks.
- What we could not check.

A successful API response does not prove the job finished. An empty queue does not prove every message was handled. Missing information means unknown, not healthy or safe.

Each dependency observation should keep its source, caller, target and operation, first and last seen times, and confidence. Keep stable IDs for apps and features. Do not invent links or percentages to fill gaps.

## Keep the first demo small

The first demo is local and AWS-focused. Use one sample app, a small list of features, a clear expected failure, a short fault, recovery checks, and a before/during/after report.

The current sample is the Serverless Quiz app. Its paths are defined from source and paired with observed requests. We have not built general automatic discovery, a full graph engine, or a security scanner.

Later, Pitwall should connect app features to services, identities, network paths, known vulnerabilities, monitoring, and recovery access. Use existing scanners and data sources where they fit. Keep the source, age, confidence, and missing coverage visible for each result.

Do not claim to detect unknown zero-days. Known-vulnerability results depend on available vulnerability data. Unusual runtime behaviour is a separate signal.

## Keep experiments contained

Start with a local emulator. Use isolated staging only when the user asks. A production canary needs explicit approval for the exact target and experiment. Never run or prepare a production fault without that approval.

Every active fault needs:

- A specific target and a small scope.
- A maximum duration and automatic expiry.
- A stop control and cleanup that is safe to repeat.
- Health checks before and after.
- A record of what happened.

Do not change shared DNS, firewalls, IAM, network ACLs, or routing for the MVP. Keep read-only discovery separate from fault controls and permissions.

Check what a fault tool actually supports before using it. Do not assume AWS FIS can fail every AWS API. LocalStack faults and proxy faults have different coverage. Label simulated failures clearly.

## Work in small, testable steps

For each approved piece of work:

1. Read the relevant plan and current code.
2. State the assumptions and the smallest check that would show it works.
3. Make the change within the approved scope.
4. Run focused tests, then the available project checks.
5. Check cleanup, including failures and interrupted runs.
6. Record actual results and update the docs.
7. Stop before starting later work unless the user asked to continue.

Keep only one delivery step in progress at a time. A step is done when its checks pass, cleanup is verified, and the docs match the code.

## Code and data

Prefer simple code. Keep adapters separate so the gateway, emulator, storage, or cloud connection can be replaced later. The current stack is FastAPI, React/TypeScript, Docker Compose, and LocalStack. Add tools only when the next working example needs them.

Validate fault input. Put timeouts on network calls. Use structured logs and UTC timestamps. Test failed cleanup and interrupted experiments. Keep prediction and observation separate in stored results.

Never commit real credentials, tokens, private account details, or sensitive request data. Local examples may use clearly fake credentials and IDs. Keep local data, backups, build output, and secrets out of Git.

## Git and other outside actions

Do not deploy, push, open pull requests, change real cloud resources, or contact outside systems unless the user asks. Updating repo docs is part of approved work. Preserve the user's edits and avoid unrelated changes.
