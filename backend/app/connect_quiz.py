"""Connect/disconnect the existing local Quiz, retaining exact backups in the state volume."""

import io
import json
import os
import sys
import zipfile
from pathlib import Path
from urllib.parse import urlsplit

import boto3
import httpx
from botocore.config import Config

from app.catalog import FUNCTIONS

UPSTREAM = "http://sunhacks-quiz-lab-localstack-1:4566"
BACKUP = Path(os.environ.get("PITWALL_DATA_DIR", "/data")) / "quiz-backup"


def aws(service):
    return boto3.client(
        service,
        endpoint_url=UPSTREAM,
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
        config=Config(connect_timeout=3, read_timeout=45, retries={"max_attempts": 2}),
    )


def pack(original, wrapper):
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(original)) as source, zipfile.ZipFile(output, "w") as dest:
        files = {
            item.filename: source.read(item) for item in source.infolist() if not item.is_dir()
        }
        files["pitwall_entry.py"] = wrapper
        for name, data in files.items():
            entry = zipfile.ZipInfo(name)
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            dest.writestr(entry, data)
    return output.getvalue()


def wait(client, name):
    client.get_waiter("function_updated_v2").wait(
        FunctionName=name, WaiterConfig={"Delay": 1, "MaxAttempts": 90}
    )


def connect():
    BACKUP.mkdir(parents=True, exist_ok=True)
    lambdas = aws("lambda")
    wrapper = Path(__file__).with_name("runtime.py").read_bytes()
    for name in FUNCTIONS:
        result = lambdas.get_function(FunctionName=name)
        config = result["Configuration"]
        location = urlsplit(result["Code"]["Location"])
        with httpx.Client(trust_env=False, timeout=30) as client:
            response = client.get(UPSTREAM + location.path + "?" + location.query)
            response.raise_for_status()
        original = response.content
        backup = BACKUP / (name + ".json")
        if config["Handler"] == "handler.lambda_handler":
            backup.write_text(
                json.dumps(
                    {
                        "Handler": config["Handler"],
                        "Environment": config.get("Environment", {}).get("Variables", {}),
                    }
                )
            )
            (BACKUP / (name + ".zip")).write_bytes(original)
        elif config["Handler"] != "pitwall_entry.handle" or not backup.exists():
            raise RuntimeError("Unexpected handler or missing original backup for " + name)
        lambdas.update_function_code(FunctionName=name, ZipFile=pack(original, wrapper))
        wait(lambdas, name)
        environment = config.get("Environment", {}).get("Variables", {})
        environment["PITWALL_GATEWAY_URL"] = "http://pitwall-gateway:8000"
        lambdas.update_function_configuration(
            FunctionName=name,
            Handler="pitwall_entry.handle",
            Environment={"Variables": environment},
        )
        wait(lambdas, name)
        print("Connected " + name, flush=True)
    gateway = aws("apigateway")
    api = next(api for api in gateway.get_rest_apis()["items"] if api["name"] == "QuizAPI")
    s3 = aws("s3")
    bucket = "quiz-lab-webapp"
    objects = s3.list_objects_v2(Bucket=bucket, Prefix="static/js/").get("Contents", [])
    changed = 0
    for item in objects:
        key = item["Key"]
        if not key.endswith((".js", ".js.map")) or ".." in Path(key).parts:
            continue
        obj = s3.get_object(Bucket=bucket, Key=key)
        data = obj["Body"].read()
        updated = data.replace(
            b"http://localhost:4567/_aws/execute-api/", b"http://localhost:8000/_aws/execute-api/"
        )
        if data != updated:
            path = BACKUP / "objects" / key
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_bytes(data)
            s3.put_object(Bucket=bucket, Key=key, Body=updated, ContentType=obj["ContentType"])
            changed += 1
    connection = {
        "api_id": api["id"],
        "app_url": "http://localhost:8000/quiz-lab-webapp/index.html",
        "functions": FUNCTIONS,
        "frontend_patched": changed,
    }
    (BACKUP.parent / "connection.json").write_text(json.dumps(connection))
    print(json.dumps(connection, indent=2), flush=True)


def disconnect():
    lambdas = aws("lambda")
    for name in FUNCTIONS:
        file = BACKUP / (name + ".json")
        if not file.exists():
            continue
        original = json.loads(file.read_text())
        lambdas.update_function_code(
            FunctionName=name, ZipFile=(BACKUP / (name + ".zip")).read_bytes()
        )
        wait(lambdas, name)
        lambdas.update_function_configuration(
            FunctionName=name,
            Handler=original["Handler"],
            Environment={"Variables": original["Environment"]},
        )
        wait(lambdas, name)
    for path in (BACKUP / "objects").rglob("*"):
        if path.is_file():
            content_type = (
                "application/json" if path.name.endswith(".map") else "application/javascript"
            )
            aws("s3").put_object(
                Bucket="quiz-lab-webapp",
                Key=path.relative_to(BACKUP / "objects").as_posix(),
                Body=path.read_bytes(),
                ContentType=content_type,
            )
    (BACKUP.parent / "connection.json").unlink(missing_ok=True)
    print("Quiz restored to its original direct LocalStack connection.", flush=True)


if __name__ == "__main__":
    {"connect": connect, "disconnect": disconnect}[
        sys.argv[1] if len(sys.argv) > 1 else "connect"
    ]()
