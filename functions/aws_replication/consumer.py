"""Create-only SQS replication. Failed records are retried individually."""
import json
import logging
import os
import re
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def validate_message(body: str) -> dict[str, Any]:
    event = json.loads(body)
    if not isinstance(event, dict) or set(event) != {"schema_version", "event_id", "record"}:
        raise ValueError("Invalid envelope")
    if type(event["schema_version"]) is not int or event["schema_version"] != 1:
        raise ValueError("Unsupported schema")
    if not isinstance(event["event_id"], str) or not 1 <= len(event["event_id"]) <= 256:
        raise ValueError("Invalid event ID")
    item = event["record"]
    if not isinstance(item, dict) or set(item) != {"id", "original_url", "origin_cloud", "created_at", "version"}:
        raise ValueError("Invalid record")
    if not isinstance(item["id"], str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", item["id"]):
        raise ValueError("Invalid ID")
    if not isinstance(item["original_url"], str) or not item["original_url"].startswith(("https://", "http://")) or len(item["original_url"]) > 2048:
        raise ValueError("Invalid URL")
    parsed = urlsplit(item["original_url"])
    if not parsed.hostname or parsed.username is not None or parsed.password is not None or any(c.isspace() for c in item["original_url"]):
        raise ValueError("Invalid URL")
    _ = parsed.port  # Invalid ports must fail validation.
    if item["origin_cloud"] != "gcp" or type(item["version"]) is not int or item["version"] != 1:
        raise ValueError("Invalid source or version")
    if not isinstance(item["created_at"], str) or datetime.fromisoformat(item["created_at"].replace("Z", "+00:00")).utcoffset() is None:
        raise ValueError("Invalid timestamp")
    return item


def replicate(table: Any, item: dict[str, Any]) -> None:
    try:
        table.put_item(Item=item, ConditionExpression="attribute_not_exists(#id)", ExpressionAttributeNames={"#id": "id"})
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "ConditionalCheckFailedException":
            raise
        existing = table.get_item(Key={"id": item["id"]}, ConsistentRead=True).get("Item")
        if existing != item:
            raise ValueError("Conflicting existing record") from exc


def handle_batch(event: dict[str, Any], table: Any) -> dict[str, Any]:
    failures = []
    for message in event["Records"]:
        try:
            replicate(table, validate_message(message["body"]))
        except Exception:
            logger.warning("Replication failed; message will retry or enter DLQ")
            failures.append({"itemIdentifier": message["messageId"]})
    return {"batchItemFailures": failures}


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    table = boto3.resource("dynamodb").Table(os.environ["DYNAMODB_TABLE"])
    return handle_batch(event, table)
