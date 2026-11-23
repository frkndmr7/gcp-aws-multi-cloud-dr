from unittest.mock import MagicMock
from datetime import datetime, timezone
import pytest
from boto3.dynamodb.types import TypeSerializer
from google.api_core.exceptions import Conflict
from functions.failback_identity.handler import process, process_batch

S = TypeSerializer()
def record(origin='aws', seq='1', **changes):
    data = dict(id='abc123', original_url='https://example.com/', origin_cloud=origin, created_at='2026-01-01T00:00:00Z', version=1)
    data.update(changes)
    return {'eventName':'INSERT', 'dynamodb': {'SequenceNumber':seq, 'NewImage': {k:S.serialize(v) for k,v in data.items()}}}

def setup_client():
    client = MagicMock()
    return client, client.collection.return_value.document.return_value

def test_create_and_skip():
    c, ref = setup_client()
    assert process(record(), c) == 'created'
    ref.create.assert_called_once()
    ref.reset_mock()
    assert process(record('gcp'), c) == 'skipped'
    ref.create.assert_not_called()

def test_duplicate_and_conflict():
    c, ref = setup_client()
    ref.create.side_effect = Conflict('exists')
    ref.get.return_value.exists = True
    ref.get.return_value.to_dict.return_value = dict(id='abc123', original_url='https://example.com/', origin_cloud='aws', created_at=datetime(2026,1,1,tzinfo=timezone.utc), version=1)
    assert process(record(), c) == 'duplicate'
    ref.get.return_value.to_dict.return_value['original_url'] = 'https://other.example/'
    with pytest.raises(ValueError): process(record(), c)
    assert ref.create.call_count == 2

def test_invalid_and_partial_failure():
    c, ref = setup_client()
    bad = record('invalid', seq='2')
    assert process_batch({'Records':[record(seq='1'), bad, record('gcp',seq='3')]}, c) == {'batchItemFailures':[{'itemIdentifier':'2'}]}
    missing = record(); del missing['dynamodb']['NewImage']['origin_cloud']
    with pytest.raises(ValueError): process(missing, c)
    ref.create.side_effect = RuntimeError('temporary')
    assert process_batch({'Records':[record()]}, c) == {'batchItemFailures':[{'itemIdentifier':'1'}]}

def test_unexpected_event():
    c, _ = setup_client(); r=record(); r['eventName']='MODIFY'
    with pytest.raises(ValueError): process(r, c)

def test_wif_error_retries_whole_batch(monkeypatch):
    import functions.failback_identity.handler as module
    def fail(*args, **kwargs):
        raise ValueError('credential detail must not be logged')
    monkeypatch.setattr(module, 'verify_aws_identity', fail)
    monkeypatch.setattr(module.boto3, 'client', lambda *a, **k: object())
    with pytest.raises(RuntimeError, match='Failback batch failed') as error:
        module.handler({'Records': [record()]}, None)
    assert error.value.__cause__ is None
