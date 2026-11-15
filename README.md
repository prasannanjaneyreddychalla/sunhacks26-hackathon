# Pitwall

**See what breaks. Know what recovers.**

Pitwall shows you what breaks when part of your app goes down. Switch off a dependency, see which features stop working, and check that everything recovers.

Built for SunHacks 2026. The current lab uses a Quiz app and AWS services running locally in LocalStack.

## Try it

Open [Pitwall](http://localhost:5173/), choose a dependency, and click **Run experiment**.

Pitwall checks the app before the fault, while the fault is on, and after traffic is restored. The results sit side by side. You can see which features worked, which failed, and which could not run because an earlier step failed.

Use **Check baseline** to test the app without a fault. **Restore all** turns the fault off right away, then the runner finishes its recovery checks.

## Set it up on Windows

You need Git, PowerShell 7, and Docker Desktop with Linux containers. You do not need Python or Node installed on the host.

From this repo's folder:

```powershell
.\samples\quiz\setup.ps1
..\aws-serverless-quiz-lab\local-lab\lab.ps1 Build
..\aws-serverless-quiz-lab\local-lab\lab.ps1 Deploy
.\scripts\pitwall.ps1 Up
```

The first command gets the tested Quiz source, our setup files, and the pinned Community image. The first download and build can take a few minutes. This setup does not need a LocalStack token.

The full Quiz checkout sits next to this repo. Our changes to it are saved here in [samples/quiz](samples/quiz/), including the small email test fix. See that folder for details or a custom checkout path.

| Open | Address |
| --- | --- |
| Pitwall dashboard | [localhost:5173](http://localhost:5173/) |
| Quiz through Pitwall | [localhost:8000/quiz-lab-webapp/index.html](http://localhost:8000/quiz-lab-webapp/index.html) |
| API docs | [localhost:8000/docs](http://localhost:8000/docs) |
| Quiz's LocalStack instance | [localhost:4567](http://localhost:4567/) |

## What you can test

There are seven choices: score writes, the submission queue, result emails, the email workflow, all Quiz DynamoDB calls, Quiz API requests, and frontend downloads.

Pitwall checks nine features: loading the frontend page, browsing quizzes, opening a quiz, creating a quiz, accepting answers, saving a score, updating the leaderboard, capturing a result email, and reading an older result.

The runner uses private test quizzes. It does not edit or delete your quizzes. Test emails stay in LocalStack and go nowhere near a real inbox.

For example, blocking score writes left **6 of 9 features working**. Saving the score failed, while the leaderboard update and result email could not finish. After restoration, **all 9 worked again**. The earlier submission still had no saved score, so Pitwall showed that separately.

## How it works

The Quiz app's browser API calls and Lambda SDK calls go through Pitwall before reaching LocalStack. Pitwall records the caller, service, operation, result, and time taken. For the selected target, it returns a temporary HTTP 503 error. The AWS service containers keep running.

Only one fault runs at a time. You choose a maximum window of 30, 45, or 60 seconds. The fault ends when the checks finish or the timer expires, whichever comes first. Closing the browser does not leave the fault on.

The paths and expected effects come from reading the Quiz source. The request log and feature checks show what happened. We do not yet trace every link inside LocalStack or discover a full dependency graph automatically. A service replying to a request does not prove the whole app is working or secure.

## Stop or disconnect

Run these from Pitwall's folder:

```powershell
.\scripts\pitwall.ps1 Status
.\scripts\pitwall.ps1 Disconnect
.\scripts\pitwall.ps1 Connect
.\scripts\pitwall.ps1 Stop
```

Disconnect puts the Quiz back on its direct LocalStack connection. Stop does that before stopping Pitwall, so the Quiz is not left pointing at a stopped gateway. Use this launcher rather than stopping the connected backend with a raw Docker command.

Pitwall keeps its reports and original connection backups in a Docker volume. If Pitwall restarts during a test, it clears the fault and marks the run interrupted. It does not claim recovery until it checks again.

The free Quiz emulator keeps its AWS resources and Quiz data in memory. Restarting it clears that data. Disconnect Pitwall before redeploying the Quiz, then reconnect it.

## Check the code

With Python 3.12, Node 22, npm, and Make available:

```sh
make setup
make check
```

This runs the backend checks and frontend build. GitHub runs the same checks on pushes. The local lab has also passed all seven real fault tests. The [test notes](PLANS.md) say what we checked and what is still missing.

To rerun the live fault tests in the running lab:

```powershell
Get-Content scripts\verify_lab.py -Raw | docker exec -i sunhacks26-hackathon-backend-1 python -
```

This creates private test data and briefly interrupts the selected Quiz calls. It checks all seven targets and saves its report at `/data/verification.json` inside the backend container.

For more background, read [the product notes](PROJECT_CONTEXT.md), [the plan and test results](PLANS.md), or [why we chose a gateway](docs/decisions/0002-pitwall-quiz-lab.md). [AGENTS.md](AGENTS.md) has the working rules for coding agents.
