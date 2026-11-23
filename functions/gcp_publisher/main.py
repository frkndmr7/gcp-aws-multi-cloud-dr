"""Firestore Eventarc create events to SQS, with no static AWS credentials."""
import hashlib
import json
import os
import re
from datetime import timezone
from urllib.parse import urlsplit

import boto3
import google.auth.transport.requests
import google.oauth2.id_token
from fastapi import FastAPI, HTTPException, Request
from google.events.cloud import firestore

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
EVENT_TYPE = "google.cloud.firestore.document.v1.created"


def transform(headers, payload: bytes, project_id: str):
    event_id = headers.get("ce-id", "")
    source = headers.get("ce-source", "")
    if headers.get("ce-type") != EVENT_TYPE or not event_id or not source:
        raise ValueError("Invalid CloudEvent headers")
    event = firestore.DocumentEventData()
    event._pb.ParseFromString(payload)
    doc = event.value
    if not event._pb.HasField("value") or event._pb.HasField("old_value"):
        raise ValueError("Expected a create event")
    prefix = f"projects/{project_id}/databases/(default)/documents/urls/"
    if not doc.name.startswith(prefix) or "/" in doc.name[len(prefix):]:
        raise ValueError("Unexpected document path")
    fields = doc.fields
    code = fields["id"].string_value
    origin = fields["origin_cloud"].string_value
    if not code or code != doc.name[len(prefix):] or origin not in ("gcp", "aws") or fields["version"].integer_value != 1:
        raise ValueError("Unexpected record")
    created = fields["created_at"].timestamp_value
    if created.tzinfo is None:
        raise ValueError("Timestamp missing timezone")
    if origin == "aws":
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", code):
            raise ValueError("Invalid AWS record ID")
        if source != f"//firestore.googleapis.com/projects/{project_id}/databases/(default)":
            raise ValueError("Unexpected CloudEvent source")
        required_types = {"id": "string_value", "original_url": "string_value", "origin_cloud": "string_value", "version": "integer_value", "created_at": "timestamp_value"}
        if any(name not in fields or fields[name]._pb.WhichOneof("value_type") != kind for name, kind in required_types.items()):
            raise ValueError("Invalid AWS record fields")
        url = fields["original_url"].string_value
        parsed = urlsplit(url)
        if not url or len(url) > 2048 or parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username is not None or parsed.password is not None or any(c.isspace() for c in url):
            raise ValueError("Invalid AWS record URL")
        _ = parsed.port
    record = {"id": code, "original_url": fields["original_url"].string_value, "origin_cloud": origin, "created_at": created.astimezone(timezone.utc).isoformat(), "version": 1}
    stable_id = hashlib.sha256((source + "\0" + event_id).encode()).hexdigest()
    return {"schema_version": 1, "event_id": stable_id, "record": record}


def make_sqs_client(role_arn: str, audience: str, region: str):
    token = google.oauth2.id_token.fetch_id_token(google.auth.transport.requests.Request(), audience)
    sts = boto3.client("sts", region_name=region)
    credentials = sts.assume_role_with_web_identity(RoleArn=role_arn, RoleSessionName="gcp-publisher", WebIdentityToken=token)["Credentials"]
    return boto3.client("sqs", region_name=region, aws_access_key_id=credentials["AccessKeyId"], aws_secret_access_key=credentials["SecretAccessKey"], aws_session_token=credentials["SessionToken"])


def publish(event, client, queue_url):
    client.send_message(QueueUrl=queue_url, MessageBody=json.dumps(event, separators=(",", ":")))


def log_success(action: str, event: dict, cloud_event_id: str) -> None:
    try:
        print(json.dumps({"severity": "INFO", "action": action, "document_id": event["record"]["id"], "origin_cloud": event["record"]["origin_cloud"], "cloud_event_id_sha256": hashlib.sha256(cloud_event_id.encode()).hexdigest()}), flush=True)
    except Exception:
        # Logging must not turn a completed send into a retry.
        pass


@app.post("/")
async def receive(request: Request):
    if os.environ.get("PUBLISHER_ENABLED", "false") != "true":
        raise HTTPException(status_code=503, detail="Publisher disabled")
    try:
        if request.headers.get("content-type", "").split(";", 1)[0] != "application/protobuf":
            raise ValueError("Expected protobuf")
        event = transform(request.headers, await request.body(), os.environ["GCP_PROJECT_ID"])
        if event["record"]["origin_cloud"] == "aws":
            log_success("skip_replication", event, request.headers["ce-id"])
            return {"status": "ignored"}
        client = make_sqs_client(os.environ["AWS_ROLE_ARN"], os.environ["AWS_TOKEN_AUDIENCE"], os.environ["AWS_REGION"])
        publish(event, client, os.environ["SQS_QUEUE_URL"])
        log_success("sent_to_sqs", event, request.headers["ce-id"])
    except Exception:
        # Do not acknowledge failure; Eventarc may retry. Avoid payload/token logs.
        raise HTTPException(status_code=503, detail="Event delivery failed") from None
    return {"status": "accepted"}
