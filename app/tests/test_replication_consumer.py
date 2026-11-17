import json
from copy import deepcopy
from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError
from functions.aws_replication.consumer import handle_batch, replicate, validate_message


@pytest.fixture
def item():
    return {"id": "abc123", "original_url": "https://example.com/", "origin_cloud": "gcp", "created_at": "2026-01-01T00:00:00Z", "version": 1}


def body(item):
    return json.dumps({"schema_version": 1, "event_id": "event-1", "record": item})


def conflict():
    return ClientError({"Error": {"Code": "ConditionalCheckFailedException", "Message": "conflict"}}, "PutItem")


def test_create_and_duplicate(item):
    table = Mock()
    replicate(table, validate_message(body(item)))
    assert table.put_item.call_args.kwargs["ConditionExpression"] == "attribute_not_exists(#id)"
    table.put_item.side_effect = conflict()
    table.get_item.return_value = {"Item": deepcopy(item)}
    replicate(table, item)
    assert table.get_item.call_args.kwargs["ConsistentRead"] is True


def test_conflict_is_not_overwritten(item):
    table = Mock()
    table.put_item.side_effect = conflict()
    table.get_item.return_value = {"Item": {**item, "original_url": "https://other.example/"}}
    with pytest.raises(ValueError):
        replicate(table, item)


def test_partial_batch_failure(item):
    table = Mock()
    result = handle_batch({"Records": [{"messageId": "ok", "body": body(item)}, {"messageId": "bad", "body": "{}"}]}, table)
    assert result == {"batchItemFailures": [{"itemIdentifier": "bad"}]}
    assert table.put_item.call_count == 1


def test_source_and_version_rejected(item):
    for change in ({"origin_cloud": "azure"}, {"version": 2}):
        with pytest.raises(ValueError):
            validate_message(body({**item, **change}))


def test_transient_failure_does_not_block_other_records(item):
    table = Mock()
    table.put_item.side_effect = [RuntimeError("temporary"), None]
    records = [{"messageId": "retry", "body": body(item)}, {"messageId": "ok", "body": body(item)}]
    assert handle_batch({"Records": records}, table) == {"batchItemFailures": [{"itemIdentifier": "retry"}]}


def test_handler_uses_configured_table(item, monkeypatch):
    from functions.aws_replication import consumer
    table = Mock()
    resource = Mock()
    resource.Table.return_value = table
    monkeypatch.setenv("DYNAMODB_TABLE", "test-table")
    monkeypatch.setattr(consumer.boto3, "resource", lambda name: resource)
    assert consumer.handler({"Records": [{"messageId": "ok", "body": body(item)}]}, None) == {"batchItemFailures": []}
    resource.Table.assert_called_once_with("test-table")
