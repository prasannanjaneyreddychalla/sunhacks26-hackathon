#!/bin/bash
set -euo pipefail
command="${1:-status}"
if [[ "$command" == "check-tools" ]]; then
  node --version
  python3 --version
  aws --version
  pytest --version
  bash -n /opt/lab/tools.sh /usr/local/bin/lstk
  python3 -c 'import ast,pathlib; [ast.parse(p.read_text()) for p in pathlib.Path("/opt/lab").glob("*.py")]'
  exit 0
fi
export AWS_ENDPOINT_URL="${LAB_INTERNAL_ENDPOINT:?}"
export AWS_PAGER=""
if [[ "$command" == "status" ]]; then
  lstk aws apigateway get-rest-apis --query 'items[].{Name:name,ID:id}'
  lstk aws lambda list-functions --query 'Functions[].{Name:FunctionName,State:State}'
  lstk aws dynamodb list-tables
  exit 0
fi
mkdir -p /workspace
tar -C /source --exclude=.git --exclude=local-lab --exclude=node_modules --exclude=build \
  --exclude=.env --exclude='.env.*' --exclude=volume --exclude=__pycache__ -cf - . \
  | tar -C /workspace -xf -
find /workspace/bin /workspace/frontend/scripts -name '*.sh' -type f -exec sed -i 's/\r$//' {} +
chmod +x /workspace/bin/*.sh /workspace/frontend/scripts/*.sh
cd /workspace
case "$command" in
  deploy)
    if [[ "${QUIZ_LAB_MODE:-licensed}" == "community" ]]; then
      python3 /opt/lab/deploy_community.py deploy
      (cd frontend && npm ci --no-audit --no-fund && AWS_ENDPOINT_URL="${LAB_PUBLIC_ENDPOINT:?}" npm run build)
      python3 /opt/lab/deploy_community.py upload
      # Seed once per emulator lifetime, retaining upstream sample questions and answers.
      if [[ "$(lstk aws dynamodb scan --table-name Quizzes --select COUNT --query Count --output text)" == "0" ]]; then
        bash -e bin/seed.sh
      fi
      exit 0
    fi
    existing="$(lstk aws apigateway get-rest-apis --query "items[?name=='QuizAPI'].id" --output text)"
    if [[ -n "$existing" && "$existing" != "None" ]]; then
      echo "QuizAPI already exists. Use Test or Status; existing state was preserved." >&2
      exit 2
    fi
    # SES is the local emulator; no SMTP service or real mailbox is configured.
    lstk aws ses verify-email-identity --email-address sender@example.com
    (cd frontend && npm ci --no-audit --no-fund)
    export AWS_ENDPOINT_URL="${LAB_PUBLIC_ENDPOINT:?}"
    bash bin/deploy.sh
    echo "Local frontend: http://localhost:3002"
    echo "Public emulator endpoint: ${LAB_PUBLIC_ENDPOINT}"
    ;;
  test)
    pytest -p no:cacheprovider tests/test_infra.py
    if [[ "${QUIZ_LAB_MODE:-licensed}" == "community" ]]; then
      pytest -p no:cacheprovider -o addopts= /opt/lab/test_community.py
    fi
    ;;
  *)
    echo "Expected check-tools, deploy, test, or status." >&2
    exit 2
    ;;
esac
