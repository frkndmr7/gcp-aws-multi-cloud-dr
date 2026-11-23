from unittest.mock import MagicMock

import boto3
import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app


def test_lookup_is_point_read_and_has_no_payload() -> None:
    api = TestClient(create_app())
    created = api.post('/api/shorten', json={'original_url': 'https://example.com/'})
    code = created.json()['code']
    assert created.json()['serving_provider'] == 'gcp'
    response = api.get(f'/api/urls/{code}')
    assert response.json() == {'exists': True, 'origin_cloud': 'gcp'}
    assert response.headers['cache-control'] == 'no-store'
    assert api.get('/api/urls/NotFound').status_code == 404
    assert api.get('/api/urls/invalid-').status_code == 404
    assert api.get(f'/r/{code}', follow_redirects=False).status_code == 307


def test_firestore_lookup_uses_one_document(monkeypatch: pytest.MonkeyPatch) -> None:
    from google.cloud import firestore
    client = MagicMock()
    doc = client.collection.return_value.document.return_value
    doc.get.return_value.exists = False
    monkeypatch.setattr(firestore, 'Client', MagicMock(return_value=client))
    with TestClient(create_app(Settings(repository_backend='firestore'))) as api:
        assert api.get('/api/urls/Abcd1234').status_code == 404
    client.collection.assert_called_once_with('urls')
    client.collection.return_value.document.assert_called_once_with('Abcd1234')
    doc.get.assert_called_once()


def test_dynamodb_lookup_uses_consistent_point_read(monkeypatch: pytest.MonkeyPatch) -> None:
    resource = MagicMock()
    table = resource.Table.return_value
    table.get_item.return_value = {}
    monkeypatch.setattr(boto3, 'resource', MagicMock(return_value=resource))
    settings = Settings(provider='aws', role='secondary', writer_mode='standby', repository_backend='dynamodb', aws_region='eu-west-1', dynamodb_table='test')
    with TestClient(create_app(settings)) as api:
        assert api.get('/api/urls/Abcd1234').status_code == 404
    table.get_item.assert_called_once_with(Key={'id': 'Abcd1234'}, ConsistentRead=True)
