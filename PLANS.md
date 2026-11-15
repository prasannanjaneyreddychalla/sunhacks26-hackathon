# Plan and test notes

## Where we are

The first Pitwall Quiz lab is built and has been checked locally. The wider product is still in progress.

Today, Pitwall can observe the Quiz app's AWS requests, apply one short fault, and compare the same features before, during, and after. The dashboard keeps the results side by side and shows the recorded calls behind them.

The product is called Pitwall. SunHacks is the hackathon name.

## What is finished in this version

- The clean dashboard, with service filtering, saved runs, request details, and a timeline.
- A connection to the existing Quiz app, with backups and a way to disconnect it.
- Seven choices of temporary HTTP 503 failures.
- Nine feature checks, including fresh scores, leaderboard entries, and captured emails.
- A maximum fault window, automatic expiry, a manual restore button, and cleanup after errors.
- Saved reports and a clear interrupted-run status after a restart.
- Quiz setup files and the email test fix kept in this repo under `samples/quiz`.
- Dependabot alerts, security-fix pull requests, and weekly dependency updates on GitHub.

The app's business handlers stay unchanged. The small entry wrapper routes calls through Pitwall, carries the run ID between steps, and limits SDK attempts to two.

## What we checked on November 15, 2026

All **30 backend tests** passed. Ruff checks and the TypeScript/Vite frontend build passed too. The backend tests still show an upstream TestClient deprecation warning.

Before pushing this version, we ran those checks again. We also tried the saved Quiz setup in a fresh checkout, then ran it a second time. Both runs worked without changing the running lab.

The live tests covered all seven targets. Every run passed all nine features before the fault and all nine again after restoration.

| Fault | Features affected during the fault |
| --- | --- |
| Score writes | Saving the score, updating the leaderboard, and receiving the email |
| Submission queue | Accepting answers and the three steps that follow |
| Result email | Receiving the email |
| Email workflow | Receiving the email |
| All Quiz DynamoDB calls | Eight features; the frontend page still loaded |
| Quiz API requests | Eight features; the frontend page still loaded |
| Frontend downloads | Loading the frontend page; the separate API checks still worked |

The final score-write run showed **9 working before, 6 during, and 9 after**. The three affected features matched the expectation from the source.

The submission accepted during that fault still had no saved score after recovery. We report that as a missing result at the time we checked, not proof of permanent data loss.

We also checked:

- **Manual restore:** clicked Restore all during a real fault. The run stopped, the fault cleared, and all nine recovery checks passed. Checks stopped too early were marked unknown.
- **Restart:** restarted Pitwall with an active email fault. The fault cleared, the saved run became interrupted, and recovery stayed unverified until checked again.
- **Disconnect and reconnect:** restored the Quiz's direct LocalStack connection. Its workflow test and both adapter tests passed. We then reconnected it and ran the final score-write test above.
- **The UI:** checked 390px mobile, 820px tablet, and the default desktop size. There was no horizontal page overflow. Filtering, Ctrl-K, navigation, the About dialog, Escape, saved runs, and the connected Quiz list worked. The final browser error log was empty.

The request log keeps at most 8,000 records. The activity table shows the latest 300 for a run, while service counts use all retained records for that run.

## What those results do not prove

The dependency paths and expected effects are based on the Quiz source. We attach observed calls and feature checks to them; we have not built full automatic discovery or a general graph engine.

We do not trace every managed-service link or AWS's internal infrastructure. Service replies do not amount to a security assessment. The current fault type is HTTP 503, not a real cloud service shutdown.

The frontend check reads the HTML page. The other checks use real APIs and verify their results. They are not a full browser test suite.

Queue-backlog charts, wider security sources, report exports, and production experiments are not built yet. A full destructive reset was not part of the checks above.

## What to work on next

These are possible next steps, not work to start without agreement:

1. Show queue depth and how long unfinished work stays pending.
2. Compare the current scoring behaviour with a version that retries failed score writes correctly.
3. Add another sample app to check that the model is useful beyond quizzes.
4. Build a real dependency graph from more sources, keeping unknown links visible.
5. Add report export and clearer next-step suggestions.
6. Add other fault types through small, replaceable adapters.

## How this fits the wider plan

| Area | Current state |
| --- | --- |
| Repo, API, frontend, and checks | In place |
| Quiz features and local AWS setup | Working; full reset check is still missing |
| Request collection | Working for the connected calls; more sources later |
| Dependency graph | Source-defined paths only |
| Endpoint search | Service filter and fixed targets; general search later |
| Expected impact | Source-based expectations; no graph-based prediction yet |
| Local faults | Working for the seven listed targets |
| Feature measurements | Working; queue metrics still missing |
| Before/during/after report | Working in the UI; wider exports and advice later |
| Demo preparation | Startup and recovery checked; a reset rehearsal and backup video remain |

Later work can add delays, throttling, DNS and connection failures, then carefully approved AWS staging tests. Security sources, other clouds, and guarded production canaries come after the local path is reliable. Production work always needs approval for the exact target and test.

## Earlier checks

On November 14, the basic API, frontend, Docker setup, and project checks worked. The first small Flaskr fixture later passed its own tests, but it was removed on November 15 at the user's request. The Quiz app is now the test application.

The original store idea was replaced by the existing Quiz sample. [Decision 0001](docs/decisions/0001-foundation.md) records the early choice; [decision 0002](docs/decisions/0002-pitwall-quiz-lab.md) explains the current gateway.

## Before calling a step done

Keep one agreed step in progress at a time. Check the behaviour, run the relevant tests, check cleanup and interruption, record the actual result, and update the docs. Leave later work for the next agreed step.
