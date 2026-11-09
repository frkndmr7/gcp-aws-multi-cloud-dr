from datetime import datetime, timezone
from unittest.mock import MagicMock
import pytest
from google.api_core.exceptions import AlreadyExists, ServiceUnavailable
from app.models import URLRecord
from app.repositories.firestore import FirestoreRepository
from app.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


def test_create_collision_and_read() -> None:
    client = MagicMock()
    doc = client.collection.return_value.document.return_value
    repo = FirestoreRepository(client)
    record = URLRecord(id='abc', original_url='https://example.com/', created_at=datetime.now(timezone.utc), origin_cloud='gcp')
    assert repo.create_if_absent(record)
    doc.create.assert_called_once_with(record.model_dump(mode='python'))
    doc.create.side_effect = AlreadyExists('exists')
    assert not repo.create_if_absent(record)
    doc.get.return_value.exists = True
    doc.get.return_value.to_dict.return_value = record.model_dump(mode='python')
    assert repo.get_by_id('abc') == record
    doc.get.return_value.exists = False
    assert repo.get_by_id('missing') is None
    doc.create.side_effect = ServiceUnavailable('down')
    with pytest.raises(ServiceUnavailable):
        repo.create_if_absent(record)


def test_firestore_selected_and_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    from google.cloud import firestore
    client = MagicMock()
    factory = MagicMock(return_value=client)
    monkeypatch.setattr(firestore, 'Client', factory)
    client.collection.return_value.document.return_value.get.return_value.exists = False
    with TestClient(create_app(Settings(repository_backend='firestore'))) as api:
        assert api.get('/r/missing').status_code == 404
    factory.assert_called_once_with(database='(default)')
    client.close.assert_called_once()
