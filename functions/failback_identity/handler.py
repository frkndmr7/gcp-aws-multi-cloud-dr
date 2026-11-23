"""DynamoDB Streams to Firestore; failures are retried without exposing payloads."""
import logging
import re
from datetime import datetime, timezone
from ipaddress import ip_address
from urllib.parse import urlsplit

import boto3
import google.auth.aws
from boto3.dynamodb.types import TypeDeserializer
from google.api_core.exceptions import Conflict
from google.cloud import firestore

from functions.failback_identity import probe as identity_probe
from functions.failback_identity.probe import required_env, credential_config, verify_aws_identity

log = logging.getLogger(__name__)
_deserialize = TypeDeserializer()


class RecordConflict(ValueError):
    pass


def normalize(item):
    if set(item) != {"id", "original_url", "origin_cloud", "created_at", "version"}:
        raise ValueError("Invalid fields")
    code, origin, url = item["id"], item["origin_cloud"], item["original_url"]
    if not isinstance(code, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", code):
        raise ValueError("Invalid id")
    if origin not in ("aws", "gcp"):
        raise ValueError("Invalid origin")
    if isinstance(item["version"], bool) or item["version"] != 1:
        raise ValueError("Invalid version")
    if not isinstance(url, str) or not url or len(url) > 2048 or any(c.isspace() for c in url):
        raise ValueError("Invalid URL")
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username is not None or parsed.password is not None:
        raise ValueError("Invalid URL")
    _ = parsed.port
    host = parsed.hostname.lower().rstrip(".")
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise ValueError("Invalid URL host")
    try:
        address = ip_address(host)
    except ValueError:
        if "." not in host or all(part.isdecimal() or part.startswith("0x") for part in host.split(".")):
            raise ValueError("Invalid URL host")
    else:
        if not address.is_global or address.is_multicast or getattr(address, "ipv4_mapped", None):
            raise ValueError("Invalid URL host")
    created = item["created_at"]
    if isinstance(created, str):
        created = datetime.fromisoformat(created.replace("Z", "+00:00"))
    if not isinstance(created, datetime) or created.tzinfo is None or created.utcoffset() is None:
        raise ValueError("Invalid timestamp")
    return {"id": code, "original_url": url, "origin_cloud": origin, "created_at": created.astimezone(timezone.utc), "version": 1}


def process(record, client):
    if record.get("eventName") != "INSERT":
        raise ValueError("Unexpected stream event")
    image = record["dynamodb"]["NewImage"]
    item = normalize({key: _deserialize.deserialize(value) for key, value in image.items()})
    if item["origin_cloud"] == "gcp":
        return "skipped"
    ref = client.collection("urls").document(item["id"])
    try:
        ref.create(item)
        return "created"
    except Conflict:
        snapshot = ref.get()
        if snapshot.exists and normalize(snapshot.to_dict()) == item:
            return "duplicate"
        raise RecordConflict("Firestore conflict") from None


def process_batch(event, client):
    failures = []
    for record in event["Records"]:
        sequence = record["dynamodb"]["SequenceNumber"]
        try:
            process(record, client)
        except RecordConflict:
            log.error("Failback conflict sequence=%s", sequence)
            failures.append({"itemIdentifier": sequence})
        except Exception:
            log.error("Failback record failed sequence=%s", sequence)
            failures.append({"itemIdentifier": sequence})
    return {"batchItemFailures": failures}


def handler(event, context):
    try:
        if isinstance(event, dict) and "action" in event:
            identity_probe.validate_probe_request(event)
            return identity_probe.handler(event, context)
        if not isinstance(event, dict) or not isinstance(event.get("Records"), list):
            raise ValueError("Invalid Streams event")
        verify_aws_identity(boto3.client("sts"))
        credentials = google.auth.aws.Credentials.from_info(credential_config(), scopes=["https://www.googleapis.com/auth/datastore"])
        client = firestore.Client(project=required_env("MCDR_GCP_PROJECT_ID"), database="(default)", credentials=credentials)
        try:
            return process_batch(event, client)
        finally:
            client.close()
    except Exception:
        raise RuntimeError("Failback batch failed") from None
