"""Integration checks for the free-mode adapters, using only the local emulator."""
import json
import time
import uuid

import boto3
from botocore.config import Config

ENDPOINT = "http://localhost:4566"
CONFIG = Config(connect_timeout=5, read_timeout=15, retries={"max_attempts": 2})


def client(service):
    return boto3.client(service, endpoint_url=ENDPOINT, region_name="us-east-1", config=CONFIG)


def test_dlq_eventbridge_sns_relay():
    sqs, sns = client("sqs"), client("sns")
    probe = uuid.uuid4().hex
    observer = sqs.create_queue(QueueName="QuizLabObserver-" + probe)["QueueUrl"]
    observer_arn = sqs.get_queue_attributes(QueueUrl=observer, AttributeNames=["QueueArn"])["Attributes"]["QueueArn"]
    topic = "arn:aws:sns:us-east-1:000000000000:DLQAlarmTopic"
    subscription = None
    try:
        sqs.set_queue_attributes(QueueUrl=observer, Attributes={"Policy": json.dumps({
            "Version": "2012-10-17", "Statement": [{
                "Effect": "Allow", "Principal": {"Service": "sns.amazonaws.com"},
                "Action": "sqs:SendMessage", "Resource": observer_arn,
                "Condition": {"ArnEquals": {"aws:SourceArn": topic}},
            }],
        })})
        subscription = sns.subscribe(
            TopicArn=topic, Protocol="sqs", Endpoint=observer_arn,
            Attributes={"RawMessageDelivery": "true"},
        )["SubscriptionArn"]
        dlq = sqs.get_queue_url(QueueName="QuizSubmissionDLQ")["QueueUrl"]
        sqs.send_message(QueueUrl=dlq, MessageBody=json.dumps({"probe": probe}))
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            messages = sqs.receive_message(QueueUrl=observer, WaitTimeSeconds=5).get("Messages", [])
            for message in messages:
                event = json.loads(message["Body"])
                if json.loads(event["detail"]["body"]).get("probe") == probe:
                    assert event["source"] == "sunhacks.quiz.dlq"
                    assert event["detail-type"] == "QuizSubmissionFailed"
                    return
        raise AssertionError("DLQ -> Lambda -> EventBridge -> SNS event was not delivered")
    finally:
        if subscription:
            sns.unsubscribe(SubscriptionArn=subscription)
        sqs.delete_queue(QueueUrl=observer)


def test_sns_sqs_retry_writer():
    quiz_id = "compatibility-probe-" + uuid.uuid4().hex
    ddb = client("dynamodb")
    item = {"QuizID": quiz_id, "Title": "Compatibility probe", "Questions": [], "Visibility": "Private"}
    try:
        client("sns").publish(
            TopicArn="arn:aws:sns:us-east-1:000000000000:QuizzesWriteFailures",
            Message=json.dumps({"TableName": "Quizzes", "Item": item}),
        )
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            stored = ddb.get_item(TableName="Quizzes", Key={"QuizID": {"S": quiz_id}}, ConsistentRead=True).get("Item")
            if stored:
                assert stored["Title"]["S"] == item["Title"]
                return
            time.sleep(1)
        raise AssertionError("SNS -> SQS -> retry Lambda did not store the probe quiz")
    finally:
        ddb.delete_item(TableName="Quizzes", Key={"QuizID": {"S": quiz_id}})
