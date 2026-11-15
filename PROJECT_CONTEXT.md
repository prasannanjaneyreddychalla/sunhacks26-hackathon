# What Pitwall is for

Pitwall helps answer a practical question: when one part of an app fails, what can people still do?

The first version tests a local Quiz app. The bigger goal is to connect app behaviour, dependencies, security findings, and recovery in one place. The [README](README.md) explains today's setup. [PLANS.md](PLANS.md) records what has actually passed.

## The basic loop

Start with a working app. Pick a dependency, look at the expected effect, and run a short fault. Check the same features before, during, and after. Show which results matched the expectation, which did not, and what could not be checked.

The useful result is about the app. For example, scores may stop saving while quiz browsing keeps working. SQS and Lambda can still be available even when they cannot finish the work that needs the database.

Returning traffic to normal is only part of recovery. A new submission might work while an earlier submission is still missing. Pitwall should make that difference easy to see.

## What works today

Pitwall sits between the Quiz app's AWS calls and its LocalStack instance. It can return temporary errors for seven selected targets and check nine app features.

The dashboard shows dependencies next to the feature results. You can inspect recorded calls, see a timeline, reopen a saved run, or restore traffic early.

The paths and expected effects come from the Quiz source. We then check real requests and real results. This is not automatic discovery of every dependency. Some links inside managed services are still outside our view.

The current lab is local. It does not use a real AWS account, run production faults, or assess security. The free setup uses S3 hosting, a Lambda/EventBridge relay, and SES v1 in place of the original sample's CloudFront, Pipes, and SES v2 setup.

## Start from features, not just services

A feature is something a user or operator needs to do: log in, browse quizzes, submit answers, save a score, receive an email, deploy, or recover the app.

Over time, each feature should have a stable ID, a name, an owner, how important it is, its data and service needs, and its fallback and recovery expectations. Availability and recovery-time goals belong here too.

Connect observed calls to these features. Keep the source, when it was seen, and the confidence for each connection. A path read from source and a path observed during a run are different kinds of information.

## What we want to add

People should eventually be able to search for a service, operation, endpoint, domain, IP, identity provider, resource, or software package. Pitwall should show whether the app uses it, which features depend on it, and what is likely to be affected by a failure or security finding.

The app map may include features, services, functions, containers, cloud resources, data stores, queues, endpoints, identities, access rules, packages, monitoring, and recovery systems. Connections should say how those parts relate, such as "calls," "depends on," "runs on," or "is allowed by."

Use stable IDs. Keep the reason for each link. Record when it was first and last seen, and leave room to replace the storage or graph tool later.

Useful sources could include:

- Application requests, logs, and OpenTelemetry traces.
- DNS and network-flow observations.
- CloudTrail, AWS Config, cloud inventories, and deployment files.
- IAM policies, security groups, firewalls, and routing.
- Package lists, software bills of materials, and known-vulnerability results.

We do not need all of them in the first demo. Add each one only when it helps answer a real app-level question.

## Show what we know

Keep confirmed, likely, possible, and unknown links distinct. Show the source and age of the information. Never turn "not observed" into "not used" or "safe."

A service returning HTTP 200 does not prove a user journey works. A prediction is not a test result. LocalStack results also do not prove how AWS services depend on one another internally.

The read-only view should stay useful without permission to inject faults. Recommendations should stay separate from actions the user has approved.

## Keep faults small and reversible

Each experiment needs a clear local or staging target, a small scope, a time limit, automatic expiry, a manual stop, checks before and after, and a saved record.

Restore traffic after success, failure, cancellation, or an interrupted run. Check both fresh requests and unfinished work. Do not assume a queue will retry correctly just because it is configured to do so.

Other failure types can come later: delays, throttling, timeouts, DNS failures, connection loss, authentication errors, TLS errors, process stops, or zone failures. Use an adapter that supports the exact fault. Check AWS FIS coverage before relying on it.

Start locally. Staging comes next. Production canaries need separate, exact approval and stronger stop, rollback, and recovery controls. Shared network or access changes are outside the first demo.

## The longer-term workspace

Security findings should connect to the same app map. A known vulnerable package matters more when we can show whether it is reachable, which feature uses it, and what isolating it would affect.

Use existing scanners instead of rebuilding them. Show their source, coverage, and limits. Do not claim to find unknown zero-days.

Monitoring and recovery access matter too. An identity-provider failure might block both customer login and the engineer trying to fix it. Those paths should become part of the same view.

Multi-cloud support, broad scanning, and guarded production experiments are later work. The first goal is a clear, repeatable local demo backed by real checks.

## A useful result

A report should explain the chosen dependency, why we think the app uses it, what we expected, what we changed, and what happened. Include affected and unaffected features, timing, retries or queues when measured, restoration, missing work, and a practical next step.

Keep the difference between expected and observed results visible. If a check was skipped or the result is unclear, say so plainly.
