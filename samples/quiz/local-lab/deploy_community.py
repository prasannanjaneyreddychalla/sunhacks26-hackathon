"""Deploy the upstream quiz on public Community APIs, confined to a local emulator."""
import base64
import hashlib
import io
import json
import mimetypes
import os
import sys
import zipfile
from pathlib import Path
from urllib.parse import urlparse

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

ROOT = Path("/workspace")
REGION = "us-east-1"
ACCOUNT = "000000000000"
ENDPOINT = os.environ["LAB_INTERNAL_ENDPOINT"]
PUBLIC = os.environ.get("LAB_PUBLIC_ENDPOINT", "http://localhost:4567")
parsed = urlparse(ENDPOINT)
if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "localstack"}:
    raise RuntimeError("Deployment is restricted to a local emulator")
CONFIG = Config(connect_timeout=5, read_timeout=45, retries={"mode": "standard", "max_attempts": 3})
STATE = ROOT / "community-state.json"
BUCKET = "quiz-lab-webapp"
FUNCTIONS = {
    "CreateQuizFunction": ("create_quiz", "CreateQuizRole", "create_quiz_policy.json"),
    "GetQuizFunction": ("get_quiz", "GetQuizRole", "get_quiz_policy.json"),
    "SubmitQuizFunction": ("submit_quiz", "SubmitQuizRole", "submit_quiz_policy.json"),
    "ScoringFunction": ("scoring", "ScoringRole", "scoring_policy.json"),
    "GetSubmissionFunction": ("get_submission", "GetSubmissionRole", "get_submission_policy.json"),
    "GetLeaderboardFunction": ("get_leaderboard", "GetLeaderboardRole", "get_leaderboard_policy.json"),
    "ListPublicQuizzesFunction": ("list_quizzes", "ListQuizzesRole", "list_quizzes_policy.json"),
    "RetryQuizzesWritesFunction": ("retry_quizzes_writes", "RetryQuizzesWritesRole", "retry_quizzes_writes_policy.json"),
}


def client(service):
    return boto3.client(service, endpoint_url=ENDPOINT, region_name=REGION, config=CONFIG)


def already_exists(operation, **kwargs):
    try:
        return operation(**kwargs)
    except ClientError as error:
        if error.response["Error"]["Code"] not in {
            "ResourceInUseException", "ResourceAlreadyExistsException", "EntityAlreadyExists",
            "ResourceConflictException", "BucketAlreadyOwnedByYou", "StateMachineAlreadyExists",
        }:
            raise
        return None


def role(name, principal, policy):
    iam = client("iam")
    arn = "arn:aws:iam::" + ACCOUNT + ":role/" + name
    already_exists(
        iam.create_role,
        RoleName=name,
        AssumeRolePolicyDocument=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{"Effect": "Allow", "Principal": {"Service": principal}, "Action": "sts:AssumeRole"}],
        }),
    )
    iam.put_role_policy(RoleName=name, PolicyName="QuizLabPolicy", PolicyDocument=json.dumps(policy))
    return arn


def function(name, source, role_arn):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as package:
        entry = zipfile.ZipInfo("handler.py")
        entry.create_system = 3
        entry.external_attr = 0o100644 << 16
        entry.compress_type = zipfile.ZIP_DEFLATED
        package.writestr(entry, source.read_bytes())
    content = buf.getvalue()
    lambdas = client("lambda")
    created = already_exists(
        lambdas.create_function,
        FunctionName=name, Runtime="python3.10", Handler="handler.lambda_handler",
        Code={"ZipFile": content}, Role=role_arn, Timeout=30,
    )
    if not created:
        existing = lambdas.get_function_configuration(FunctionName=name)
        digest = base64.b64encode(hashlib.sha256(content).digest()).decode()
        if existing.get("CodeSha256") != digest:
            lambdas.update_function_code(FunctionName=name, ZipFile=content)
    lambdas.get_waiter("function_active_v2").wait(
        FunctionName=name, WaiterConfig={"Delay": 2, "MaxAttempts": 90}
    )
    return "arn:aws:lambda:" + REGION + ":" + ACCOUNT + ":function:" + name


def queue(name, attributes=None):
    sqs = client("sqs")
    url = sqs.create_queue(QueueName=name)["QueueUrl"]
    if attributes:
        sqs.set_queue_attributes(QueueUrl=url, Attributes=attributes)
    arn = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["QueueArn"])["Attributes"]["QueueArn"]
    return url, arn


def mapping(function_name, queue_arn):
    lambdas = client("lambda")
    existing = lambdas.list_event_source_mappings(
        FunctionName=function_name, EventSourceArn=queue_arn
    )["EventSourceMappings"]
    if not existing:
        lambdas.create_event_source_mapping(
            FunctionName=function_name, EventSourceArn=queue_arn, BatchSize=10, Enabled=True
        )


def deploy():
    print("Deploying free-compatible quiz infrastructure...", flush=True)
    ddb = client("dynamodb")
    already_exists(
        ddb.create_table, TableName="Quizzes", BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[{"AttributeName": "QuizID", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "QuizID", "KeyType": "HASH"}],
    )
    already_exists(
        ddb.create_table, TableName="UserSubmissions", BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[
            {"AttributeName": "SubmissionID", "AttributeType": "S"},
            {"AttributeName": "QuizID", "AttributeType": "S"},
            {"AttributeName": "Score", "AttributeType": "N"},
        ],
        KeySchema=[{"AttributeName": "SubmissionID", "KeyType": "HASH"}],
        GlobalSecondaryIndexes=[{
            "IndexName": "QuizID-Score-index",
            "KeySchema": [{"AttributeName": "QuizID", "KeyType": "HASH"}, {"AttributeName": "Score", "KeyType": "RANGE"}],
            "Projection": {"ProjectionType": "ALL"},
        }],
    )
    for table in ["Quizzes", "UserSubmissions"]:
        ddb.get_waiter("table_exists").wait(TableName=table)
    dlq_url, dlq_arn = queue("QuizSubmissionDLQ")
    submission_url, submission_arn = queue("QuizSubmissionQueue", {
        "VisibilityTimeout": "35",
        "RedrivePolicy": json.dumps({"deadLetterTargetArn": dlq_arn, "maxReceiveCount": "3"}),
    })
    retry_url, retry_arn = queue("QuizzesWriteFailuresQueue", {"VisibilityTimeout": "35"})
    sns = client("sns")
    topic = sns.create_topic(Name="QuizzesWriteFailures")["TopicArn"]
    alarm_topic = sns.create_topic(Name="DLQAlarmTopic")["TopicArn"]
    sns.subscribe(TopicArn=topic, Protocol="sqs", Endpoint=retry_arn)
    client("sqs").set_queue_attributes(
        QueueUrl=retry_url,
        Attributes={"Policy": json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow", "Principal": {"Service": "sns.amazonaws.com"},
                "Action": "sqs:SendMessage", "Resource": retry_arn,
                "Condition": {"ArnEquals": {"aws:SourceArn": topic}},
            }],
        })},
    )
    for name, (directory, role_name, policy_file) in FUNCTIONS.items():
        policy = json.loads((ROOT / "configurations" / policy_file).read_text())
        # The upstream sample intentionally omits this permission for IAM demonstrations.
        if name == "SubmitQuizFunction":
            policy["Statement"].append({
                "Effect": "Allow", "Action": ["sqs:SendMessage", "sqs:GetQueueUrl"], "Resource": submission_arn,
            })
        function(name, ROOT / "lambdas" / directory / "handler.py", role(role_name, "lambda.amazonaws.com", policy))
        print("Ready: " + name, flush=True)
    helper_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {"Effect": "Allow", "Action": ["ses:SendEmail"], "Resource": "*"},
            {"Effect": "Allow", "Action": ["events:PutEvents"], "Resource": "arn:aws:events:us-east-1:000000000000:event-bus/QuizLabBus"},
            {"Effect": "Allow", "Action": ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"], "Resource": dlq_arn},
            {"Effect": "Allow", "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"], "Resource": "arn:aws:logs:us-east-1:000000000000:log-group:/aws/lambda/*"},
        ],
    }
    helper_role = role("QuizLabCompatibilityRole", "lambda.amazonaws.com", helper_policy)
    email_arn = function("QuizLabEmailFunction", Path("/opt/lab/notification_handler.py"), helper_role)
    function("QuizLabDlqRelayFunction", Path("/opt/lab/dlq_relay_handler.py"), helper_role)
    events = client("events")
    events.create_event_bus(Name="QuizLabBus") if "QuizLabBus" not in [
        item["Name"] for item in events.list_event_buses()["EventBuses"]
    ] else None
    rule_arn = events.put_rule(
        Name="QuizDlqNotifications", EventBusName="QuizLabBus",
        EventPattern=json.dumps({"source": ["sunhacks.quiz.dlq"], "detail-type": ["QuizSubmissionFailed"]}),
    )["RuleArn"]
    events.put_targets(
        Rule="QuizDlqNotifications", EventBusName="QuizLabBus",
        Targets=[{"Id": "notify", "Arn": alarm_topic}],
    )
    sns.set_topic_attributes(
        TopicArn=alarm_topic, AttributeName="Policy",
        AttributeValue=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow", "Principal": {"Service": "events.amazonaws.com"},
                "Action": "sns:Publish", "Resource": alarm_topic,
                "Condition": {"ArnEquals": {"aws:SourceArn": rule_arn}},
            }],
        }),
    )
    states = client("stepfunctions")
    machine_policy = {"Version": "2012-10-17", "Statement": [{
        "Effect": "Allow", "Action": "lambda:InvokeFunction", "Resource": email_arn,
    }]}
    machine_role = role("SendEmailStateMachineRole", "states.amazonaws.com", machine_policy)
    definition = json.dumps({
        "StartAt": "CheckEmail",
        "States": {
            "CheckEmail": {
                "Type": "Choice",
                "Choices": [{"Variable": "$.Email", "IsPresent": True, "Next": "SendEmail"}],
                "Default": "NoEmailProvided",
            },
            "SendEmail": {"Type": "Task", "Resource": email_arn, "TimeoutSeconds": 30, "End": True},
            "NoEmailProvided": {"Type": "Succeed"},
        },
    })
    machines = states.list_state_machines()["stateMachines"]
    existing_machine = next((item for item in machines if item["name"] == "SendEmailStateMachine"), None)
    if existing_machine:
        states.update_state_machine(
            stateMachineArn=existing_machine["stateMachineArn"], definition=definition, roleArn=machine_role
        )
    else:
        states.create_state_machine(name="SendEmailStateMachine", definition=definition, roleArn=machine_role)
    for email in ["sender@example.com", "user@example.com", "your.email@example.com"]:
        client("ses").verify_email_identity(EmailAddress=email)
    mapping("ScoringFunction", submission_arn)
    mapping("RetryQuizzesWritesFunction", retry_arn)
    mapping("QuizLabDlqRelayFunction", dlq_arn)

    gateway = client("apigateway")
    existing_api = next((item for item in gateway.get_rest_apis()["items"] if item["name"] == "QuizAPI"), None)
    api_id = existing_api["id"] if existing_api else gateway.create_rest_api(name="QuizAPI")["id"]
    resources = gateway.get_resources(restApiId=api_id)["items"]
    root_id = next(item["id"] for item in resources if item["path"] == "/")
    endpoints = [
        ("getquiz", "GET", "GetQuizFunction"), ("createquiz", "POST", "CreateQuizFunction"),
        ("submitquiz", "POST", "SubmitQuizFunction"), ("getsubmission", "GET", "GetSubmissionFunction"),
        ("getleaderboard", "GET", "GetLeaderboardFunction"), ("listquizzes", "GET", "ListPublicQuizzesFunction"),
    ]
    for path, method, name in endpoints:
        resource = next((item for item in resources if item.get("pathPart") == path), None)
        resource_id = resource["id"] if resource else gateway.create_resource(
            restApiId=api_id, parentId=root_id, pathPart=path
        )["id"]
        gateway.put_method(restApiId=api_id, resourceId=resource_id, httpMethod=method, authorizationType="NONE")
        arn = "arn:aws:lambda:" + REGION + ":" + ACCOUNT + ":function:" + name
        gateway.put_integration(
            restApiId=api_id, resourceId=resource_id, httpMethod=method,
            type="AWS_PROXY", integrationHttpMethod="POST",
            uri="arn:aws:apigateway:" + REGION + ":lambda:path/2015-03-31/functions/" + arn + "/invocations",
        )
        already_exists(
            client("lambda").add_permission, FunctionName=name, StatementId="QuizApi-" + path,
            Action="lambda:InvokeFunction", Principal="apigateway.amazonaws.com",
            SourceArn="arn:aws:execute-api:" + REGION + ":" + ACCOUNT + ":" + api_id + "/*/" + method + "/" + path,
        )
        gateway.put_method(restApiId=api_id, resourceId=resource_id, httpMethod="OPTIONS", authorizationType="NONE")
        gateway.put_integration(
            restApiId=api_id, resourceId=resource_id, httpMethod="OPTIONS",
            type="MOCK", requestTemplates={"application/json": '{"statusCode":200}'},
        )
        headers = {
            "method.response.header.Access-Control-Allow-Origin": "'*'",
            "method.response.header.Access-Control-Allow-Headers": "'Content-Type,Authorization'",
            "method.response.header.Access-Control-Allow-Methods": "'GET,POST,OPTIONS'",
        }
        gateway.put_method_response(
            restApiId=api_id, resourceId=resource_id, httpMethod="OPTIONS",
            statusCode="200", responseParameters={key: True for key in headers},
        )
        gateway.put_integration_response(
            restApiId=api_id, resourceId=resource_id, httpMethod="OPTIONS",
            statusCode="200", responseParameters=headers,
        )
    gateway.create_deployment(restApiId=api_id, stageName="prod")
    state = {
        "mode": "community", "api_id": api_id,
        "api_url": PUBLIC + "/_aws/execute-api/" + api_id + "/prod",
        "app_url": PUBLIC + "/" + BUCKET + "/index.html",
        "services": ["API Gateway REST", "Lambda", "DynamoDB", "SQS", "SNS", "S3", "Step Functions", "EventBridge", "SES", "CloudWatch Logs", "IAM"],
        "substitutions": ["S3/static hosting replaces CloudFront", "Lambda/EventBridge relay replaces EventBridge Pipes", "SES v1 via Lambda replaces SES v2 SDK task"],
    }
    STATE.write_text(json.dumps(state, indent=2))
    print(json.dumps(state, indent=2), flush=True)


def upload():
    s3 = client("s3")
    already_exists(s3.create_bucket, Bucket=BUCKET)
    s3.put_bucket_website(Bucket=BUCKET, WebsiteConfiguration={"IndexDocument": {"Suffix": "index.html"}})
    s3.put_bucket_policy(Bucket=BUCKET, Policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Principal": "*", "Action": "s3:GetObject", "Resource": "arn:aws:s3:::" + BUCKET + "/*"}],
    }))
    build = ROOT / "frontend" / "build"
    for file in build.rglob("*"):
        if file.is_file():
            mime = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
            s3.upload_file(str(file), BUCKET, file.relative_to(build).as_posix(), ExtraArgs={"ContentType": mime})
    print("Frontend uploaded: " + json.loads(STATE.read_text())["app_url"], flush=True)


if __name__ == "__main__":
    {"deploy": deploy, "upload": upload}[sys.argv[1]]()
