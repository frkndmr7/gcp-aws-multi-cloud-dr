"""Operator reconciliation: dry-run by default, conditional single-record repair only."""
from __future__ import annotations

import argparse
import os
import json
import re
import sys
from typing import Any

import boto3
from google.api_core.exceptions import Conflict
from google.cloud import firestore

from functions.failback_identity.handler import normalize

CATEGORIES = ("missing", "matched", "conflict", "error")


def safe_id(value: Any, index: int) -> str:
    if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
        return value
    return f"<invalid-record-{index}>"


def classify(item: dict[str, Any], collection: Any, apply: bool) -> str:
    record = normalize(item)
    if record["origin_cloud"] != "aws":
        raise ValueError("Not an AWS-origin record")
    ref = collection.document(record["id"])
    snapshot = ref.get()
    if snapshot.exists:
        return "matched" if normalize(snapshot.to_dict()) == record else "conflict"
    if not apply:
        return "missing"
    try:
        ref.create(record)
        return "created"
    except Conflict:
        # Another writer won the create race. Never overwrite it.
        snapshot = ref.get()
        if not snapshot.exists:
            raise RuntimeError("Create race could not be verified") from None
        return "matched" if normalize(snapshot.to_dict()) == record else "conflict"


def reconcile(table: Any, collection: Any, *, item_id: str | None = None,
              apply: bool = False, page_size: int = 25, max_items: int | None = None) -> dict[str, Any]:
    if apply and not item_id:
        raise ValueError("Apply requires exactly one ID")
    if item_id and not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", item_id):
        raise ValueError("Invalid ID")
    if page_size < 1 or page_size > 100 or (max_items is not None and max_items < 1):
        raise ValueError("Invalid read limit")
    report: dict[str, Any] = {"mode": "apply" if apply else "dry-run", "scanned": 0,
                              "aws_origin": 0, "gcp_skipped": 0, "complete": True,
                              "ids": {key: [] for key in (*CATEGORIES, "created")}}

    def record_item(item: dict[str, Any]) -> None:
        report["scanned"] += 1
        label = safe_id(item.get("id"), report["scanned"])
        try:
            origin = item.get("origin_cloud")
            if origin == "gcp":
                normalize(item)
                report["gcp_skipped"] += 1
                return
            if origin == "aws":
                report["aws_origin"] += 1
            else:
                raise ValueError("Invalid origin")
            report["ids"][classify(item, collection, apply)].append(label)
        except Exception:
            # SDK exceptions may contain credentials, endpoints, or document data.
            report["ids"]["error"].append(label)

    try:
        if item_id:
            item = table.get_item(Key={"id": item_id}, ConsistentRead=True).get("Item")
            if item is None or item.get("id") != item_id:
                report["ids"]["error"].append(item_id)
            else:
                record_item(item)
        else:
            key = None
            while True:
                limit = page_size if max_items is None else min(page_size, max_items - report["scanned"])
                args: dict[str, Any] = {"Limit": limit, "ConsistentRead": True}
                if key:
                    args["ExclusiveStartKey"] = key
                response = table.scan(**args)
                for item in response.get("Items", []):
                    record_item(item)
                key = response.get("LastEvaluatedKey")
                if not key:
                    break
                if max_items is not None and report["scanned"] >= max_items:
                    report["complete"] = False
                    break
    except Exception:
        report["complete"] = False
        report["ids"]["error"].append("<read-failed>")
    report["counts"] = {key: len(values) for key, values in report["ids"].items()}
    report["status"] = ("error" if report["counts"]["error"] or report["counts"]["conflict"] or not report["complete"]
                        else "needs_reconciliation" if report["counts"]["missing"] else "ok")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="conditionally create one missing AWS-origin record")
    parser.add_argument("--id", help="point-read a single record; required with --apply")
    parser.add_argument("--profile", default=None)
    parser.add_argument("--page-size", type=int, default=25)
    parser.add_argument("--max-items", type=int, help="stop after this many scanned items; incomplete runs exit nonzero")
    for option in ("aws-account-id", "aws-region", "table-name", "gcp-project-id"):
        parser.add_argument("--" + option, default=os.environ.get("MCDR_" + option.upper().replace("-", "_")))
    args = parser.parse_args(argv)
    for option in ("aws_account_id", "aws_region", "table_name", "gcp_project_id"):
        value = getattr(args, option)
        if not value or re.search("REPLACE|PLACEHOLDER|CHANGEME", value, re.I):
            parser.error("Supply --" + option.replace("_", "-"))
    if args.apply and not args.id:
        parser.error("--apply requires --id")
    if args.id and not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", args.id):
        parser.error("invalid --id")
    if not 1 <= args.page_size <= 100 or (args.max_items is not None and args.max_items < 1):
        parser.error("invalid read limit")
    client = None
    try:
        session = boto3.Session(profile_name=args.profile, region_name=args.aws_region)
        if session.client("sts").get_caller_identity().get("Account") != args.aws_account_id:
            raise ValueError("Unexpected AWS account")
        table = session.resource("dynamodb").Table(args.table_name)
        # Local operator uses ADC; the Lambda execution role is not assumed here.
        client = firestore.Client(project=args.gcp_project_id, database="(default)")
        report = reconcile(table, client.collection("urls"), item_id=args.id, apply=args.apply,
                           page_size=args.page_size, max_items=args.max_items)
        print(json.dumps(report, sort_keys=True))
        return 1 if report["status"] == "error" else 0
    except Exception:
        print(json.dumps({"status": "error", "message": "Identity or read failed"}), file=sys.stderr)
        return 1
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())
