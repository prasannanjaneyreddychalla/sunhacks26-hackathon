"""Community compatibility: Step Functions invokes Lambda, which uses SES v1."""
from html import escape

import boto3


def lambda_handler(event, context):
    result = boto3.client("ses").send_email(
        Source="sender@example.com",
        Destination={"ToAddresses": [event["Email"]]},
        Message={
            "Subject": {"Data": "Your Quiz Results", "Charset": "UTF-8"},
            "Body": {
                "Text": {
                    "Data": "Hello " + str(event["Username"]) + ". Your Score: " + str(event["Score"]) + ".",
                    "Charset": "UTF-8",
                },
                "Html": {
                    "Data": (
                        "<html><body><h2>Hello "
                        + escape(str(event["Username"]))
                        + "</h2><p>Your Score: "
                        + str(event["Score"])
                        + ".</p></body></html>"
                    ),
                    "Charset": "UTF-8",
                }
            },
        },
    )
    return {"MessageId": result["MessageId"]}
