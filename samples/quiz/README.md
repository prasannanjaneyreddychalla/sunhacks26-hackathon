# The Quiz app

We use the [official Serverless Quiz sample](https://github.com/localstack-samples/sample-serverless-quiz-app) as the app Pitwall tests. It has quizzes, queued answers, scores, leaderboards, and result emails.

This folder saves our setup files and a small test fix. The full Quiz source stays in a separate checkout next to Pitwall. That keeps the original app easy to compare with our changes.

## Get it ready

Open Docker Desktop with Linux containers, then run this from Pitwall's folder in PowerShell 7:

```powershell
.\samples\quiz\setup.ps1
```

The script:

1. Downloads the Quiz app into `../aws-serverless-quiz-lab` at the version we tested.
2. Copies our `local-lab` files into that checkout.
3. Fixes the email test so it waits for a new result instead of checking too early.
4. Downloads our tested Community image if it is missing, then gives it the local tag used by the launcher.

The first download can take a few minutes. The image is pinned to an exact digest; the script does not use `latest`. It does not need a LocalStack token. It leaves existing source edits and different image tags alone, and stops with a message when they need attention.

You can choose another folder with `-Path`. Use `-SkipImage` when you only want the files. Running the script again with unchanged files is safe.

## Start the Quiz

From Pitwall's folder:

```powershell
..\aws-serverless-quiz-lab\local-lab\lab.ps1 Build
..\aws-serverless-quiz-lab\local-lab\lab.ps1 Deploy
.\scripts\pitwall.ps1 Up
```

Then open [Pitwall](http://localhost:5173/) or the [Quiz through Pitwall](http://localhost:8000/quiz-lab-webapp/index.html).

Quiz data lives in the free emulator's memory. Restarting that emulator clears it. If you need to deploy the Quiz again, disconnect Pitwall first, redeploy, and reconnect. You can lose Quiz data when the emulator restarts.

## What we changed

The free setup serves the frontend from S3, uses Lambda and EventBridge instead of Pipes, and sends captured email through SES v1. It adds two helper functions. The eight original business handlers stay unchanged.

`wait-for-email.patch` changes only the workflow test. It waits for a fresh email to the expected address with the expected score. `local-lab` contains the launcher, deployment code, helpers, and adapter tests.

When editing this setup, keep this saved copy in step with the separate Quiz checkout. GitHub stores this folder; the sibling checkout is the working copy used to run it.

## Source and license

The tested upstream commit is `f20e26d45758cfa8d8aa514cdd8472de2a29b0a2`. The sample uses Apache-2.0; its license is kept unchanged in [UPSTREAM_LICENSE](UPSTREAM_LICENSE). The download script checks the source version before applying our files.
