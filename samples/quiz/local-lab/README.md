# Run the Quiz lab

This folder runs the [Serverless Quiz sample](https://github.com/localstack-samples/sample-serverless-quiz-app) on Windows using Docker. It is the app we test with Pitwall.

Use Pitwall's `samples/quiz/setup.ps1` first. It gets the source and the exact Community image we tested. No LocalStack account or token is needed for this mode.

## Start it

Run these from the Quiz checkout in PowerShell 7:

```powershell
.\local-lab\lab.ps1 Build
.\local-lab\lab.ps1 Deploy
.\local-lab\lab.ps1 Test
.\local-lab\lab.ps1 Status
```

Before connecting Pitwall, open [the Quiz](http://localhost:4567/quiz-lab-webapp/index.html). Pick a quiz, enter a username, answer the questions, and look at the leaderboard. The sample includes AWS, comic book, and Star Wars quizzes.

To connect Pitwall, run `scripts/pitwall.ps1 Up` from the Pitwall repo. Then use [the Quiz through Pitwall](http://localhost:8000/quiz-lab-webapp/index.html). Pitwall's README explains how to run faults and compare the results.

## What runs locally

The app uses API Gateway, Lambda, DynamoDB, SQS, SNS, S3, Step Functions, SES, EventBridge, IAM, and CloudWatch Logs. The eight original business handlers and frontend source stay unchanged.

The free setup makes three changes around them:

| Original setup | Free setup |
| --- | --- |
| CloudFront serves the frontend | Local S3 serves it directly |
| EventBridge Pipes moves failed messages to SNS | A helper Lambda and EventBridge rule do it |
| Step Functions sends email through SES v2 | A helper Lambda sends it through SES v1 |

There are two extra helper Lambdas. The deployment also gives the submission handler permission to send queue messages. The sample leaves that permission out on purpose for its IAM demo.

Emails stay inside LocalStack. They are not sent to real inboxes. The scoring handler can catch an error without retrying the lost work; we keep that behaviour so Pitwall can show it.

## Stop or redeploy

Disconnect Pitwall before stopping or redeploying the Quiz. From the Pitwall repo, run `scripts/pitwall.ps1 Disconnect`. Then, from the Quiz checkout:

```powershell
.\local-lab\lab.ps1 Stop
```

The Community emulator keeps AWS resources and Quiz data in memory. Stopping or restarting it clears them. Run Deploy again to recreate the app and sample data, then reconnect Pitwall. Docker keeps the downloaded Node packages and frontend build in a separate workspace volume.

## Checks

Test runs the original app workflow and two tests for our helpers. It checks scores, saved submissions, leaderboard entries, a fresh result email, and the failed-message path. It does not inject faults.

The email test waits up to 45 seconds for a new email to the right address with the right score. This avoids passing because of an old email or failing because the new one has not arrived yet.

On November 15, 2026, all three tests passed with Pitwall disconnected. We also created a quiz in the browser, answered it, and saw the correct score and leaderboard entry. The frontend build and PowerShell, Compose, Bash, and Python checks passed. Pitwall's own fault-test results are in its `PLANS.md`.

## Optional licensed mode

`compose.yaml` also pins a newer image for the original deployment path. That mode has not been verified. It needs a LocalStack token and access to the services used by the original sample, including CloudFront, Pipes, and SES v2. Check [LocalStack's licensing docs](https://docs.localstack.cloud/aws/licensing/) for your account's coverage.

After disconnecting Pitwall and stopping the Community lab:

```powershell
.\local-lab\lab.ps1 Deploy -Mode Licensed -PromptForToken
```

The prompt hides the token and does not save it. This mode refuses to deploy over an existing Quiz API. Its frontend opens on [localhost:3002](http://localhost:3002/).

## A few setup details

Ports are bound to this computer only. The scripts use fake AWS credentials and explicit local endpoints. Lambda needs the Docker socket to start its containers. The tools copy the read-only source into a Docker workspace and fix shell line endings there.

The small `lstk` script is a local AWS CLI helper. It is not the LocalStack account CLI. Keep tokens and local data out of Git.

The source is pinned to commit `f20e26d45758cfa8d8aa514cdd8472de2a29b0a2` and uses the Apache-2.0 license.
