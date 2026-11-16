from datetime import datetime, timezone
from unittest.mock import MagicMock

import boto3
import pytest
from botocore.exceptions import ClientError
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.models import URLRecord
from app.repositories.dynamodb import DynamoDBRepository


@pytest.fixture
def record() -> URLRecord:
    return URLRecord(id='abc', original_url='https://example.com/',
                     created_at=datetime(2026, 1, 1, tzinfo=timezone.utc), origin_cloud='gcp')


def test_conditional_create_and_collision(record: URLRecord) -> None:
    table = MagicMock()
    repo = DynamoDBRepository(table)
    assert repo.create_if_absent(record)
    table.put_item.assert_called_once_with(Item=record.model_dump(mode='json'),
        ConditionExpression='attribute_not_exists(#id)', ExpressionAttributeNames={'#id': 'id'})
    table.put_item.side_effect = ClientError({'Error': {'Code': 'ConditionalCheckFailedException'}}, 'PutItem')
    assert not repo.create_if_absent(record)
    table.put_item.side_effect = ClientError({'Error': {'Code': 'AccessDeniedException'}}, 'PutItem')
    with pytest.raises(ClientError):
        repo.create_if_absent(record)


def test_read_and_missing_and_mismatched_id(record: URLRecord) -> None:
    table = MagicMock()
    table.get_item.return_value = {'Item': record.model_dump(mode='json')}
    repo = DynamoDBRepository(table)
    assert repo.get_by_id('abc') == record
    table.get_item.assert_called_with(Key={'id': 'abc'}, ConsistentRead=True)
    with pytest.raises(ValueError):
        repo.get_by_id('other')
    table.get_item.return_value = {}
    assert repo.get_by_id('missing') is None


def test_dynamodb_config_requires_region_and_table(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('SERVING_PROVIDER', 'aws')
    monkeypatch.setenv('REPOSITORY_BACKEND', 'dynamodb')
    monkeypatch.delenv('AWS_REGION', raising=False)
    monkeypatch.delenv('DYNAMODB_TABLE', raising=False)
    with pytest.raises(ValueError, match='AWS_REGION and DYNAMODB_TABLE'):
        Settings.from_env()
    monkeypatch.setenv('AWS_REGION', 'eu-west-1')
    monkeypatch.setenv('DYNAMODB_TABLE', 'example-urls')
    assert Settings.from_env().writer_mode == 'standby'


def test_lifecycle_and_standby_blocks_write(monkeypatch: pytest.MonkeyPatch) -> None:
    resource = MagicMock()
    monkeypatch.setattr(boto3, 'resource', MagicMock(return_value=resource))
    settings = Settings(provider='aws', role='secondary', writer_mode='standby',
                        repository_backend='dynamodb', aws_region='eu-west-1', dynamodb_table='example-urls')
    with TestClient(create_app(settings=settings)) as client:
        result = client.post('/api/shorten', json={'original_url': 'https://example.com/'})
        assert result.status_code == 503
        resource.Table.return_value.put_item.assert_not_called()
    boto3.resource.assert_called_once_with('dynamodb', region_name='eu-west-1')
    resource.meta.client.close.assert_called_once()
