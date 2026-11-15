# 0002: Put Pitwall in the request path

Decided on November 15, 2026, for the local Quiz demo.

## Why the Quiz app

The existing Serverless Quiz sample already uses database writes, queues, scoring, and result emails. It gives us several useful failure paths without building another sample app first. It replaces the earlier store proposal.

## Why a gateway

Route the Quiz app's browser API calls and Lambda SDK calls through Pitwall before they reach LocalStack. Then Pitwall can record what happened and return a temporary error for a chosen service, operation, or resource.

This works with our tested Community image and does not need a paid fault API. It measures the app's behaviour, not AWS's internal service dependencies.

## Keep the connection reversible

Add a small Lambda entry wrapper and keep the business handlers unchanged. The wrapper carries the run ID across queue messages and workflows, keeps queue URLs going through Pitwall, and limits SDK attempts to two.

Back up the original code, settings, and changed frontend files before connecting. Disconnect restores them. The setup files and email test patch live in this repo so the lab can be prepared again from the tested upstream version.

## Keep results honest

Define the first paths and expected effects from the source. Pair them with observed requests and real feature checks. Keep the before, during, and after results separate.

Wait for the new score, leaderboard entry, and matching email. Do not accept an old result as proof that this run worked. Show unknown when a check was not finished.

We do not see every link inside managed services. Full automatic discovery and a general graph engine are later work.

## Keep faults contained

Use one local API worker, one known LocalStack target, and one fault at a time. Each fault has a short countdown checked on every request. Restore traffic when checks finish, when the timer ends, when the user stops, or when a worker fails.

Do not reload an old fault after a restart. Keep the report, mark it interrupted, and leave recovery unverified until checked. Keep control and health requests outside the fault path.

The runner uses private test data. After restoration, check fresh requests and the submission accepted during the fault separately. The original scoring code can hide an error and leave a score missing; we preserve that behaviour so the test can show it.
