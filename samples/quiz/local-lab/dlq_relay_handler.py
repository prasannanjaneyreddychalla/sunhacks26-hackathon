"""Community compatibility: DLQ -> Lambda -> EventBridge -> SNS, replacing Pipes."""
import json

import boto3


def lambda_handler(event, context):
    entries = [
        {
            "Source": "sunhacks.quiz.dlq",
            "DetailType": "QuizSubmissionFailed",
            "Detail": json.dumps({"messageId": record["messageId"], "body": record["body"]}),
            "EventBusName": "QuizLabBus",
        }
        for record in event["Records"]
    ]
    result = boto3.client("events").put_events(Entries=entries)
    if result.get("FailedEntryCount"):
        raise RuntimeError("Some dead-letter notifications were not delivered")
    return {"forwarded": len(entries)}
