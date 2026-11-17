"""Firestore Eventarc create events to SQS, with no static AWS credentials."""
import hashlib
import json
import os
from datetime import timezone

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
    if not code or code != doc.name[len(prefix):] or fields["origin_cloud"].string_value != "gcp" or fields["version"].integer_value != 1:
        raise ValueError("Unexpected record")
    created = fields["created_at"].timestamp_value
    if created.tzinfo is None:
        raise ValueError("Timestamp missing timezone")
    record = {"id": code, "original_url": fields["original_url"].string_value, "origin_cloud": "gcp", "created_at": created.astimezone(timezone.utc).isoformat(), "version": 1}
    stable_id = hashlib.sha256((source + "\0" + event_id).encode()).hexdigest()
    return {"schema_version": 1, "event_id": stable_id, "record": record}


def make_sqs_client(role_arn: str, audience: str, region: str):
    token = google.oauth2.id_token.fetch_id_token(google.auth.transport.requests.Request(), audience)
    sts = boto3.client("sts", region_name=region)
    credentials = sts.assume_role_with_web_identity(RoleArn=role_arn, RoleSessionName="gcp-publisher", WebIdentityToken=token)["Credentials"]
    return boto3.client("sqs", region_name=region, aws_access_key_id=credentials["AccessKeyId"], aws_secret_access_key=credentials["SecretAccessKey"], aws_session_token=credentials["SessionToken"])


def publish(event, client, queue_url):
    client.send_message(QueueUrl=queue_url, MessageBody=json.dumps(event, separators=(",", ":")))


@app.post("/")
async def receive(request: Request):
    if os.environ.get("PUBLISHER_ENABLED", "false") != "true":
        raise HTTPException(status_code=503, detail="Publisher disabled")
    try:
        if request.headers.get("content-type", "").split(";", 1)[0] != "application/protobuf":
            raise ValueError("Expected protobuf")
        event = transform(request.headers, await request.body(), os.environ["GCP_PROJECT_ID"])
        client = make_sqs_client(os.environ["AWS_ROLE_ARN"], os.environ["AWS_TOKEN_AUDIENCE"], os.environ["AWS_REGION"])
        publish(event, client, os.environ["SQS_QUEUE_URL"])
    except Exception:
        # Do not acknowledge failure; Eventarc may retry. Avoid payload/token logs.
        raise HTTPException(status_code=503, detail="Event delivery failed") from None
    return {"status": "accepted"}
