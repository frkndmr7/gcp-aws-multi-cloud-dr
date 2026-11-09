from typing import Any
from google.api_core.exceptions import Conflict
from app.models import URLRecord


class FirestoreRepository:
    def __init__(self, client: Any) -> None:
        self._collection = client.collection('urls')

    def create_if_absent(self, record: URLRecord) -> bool:
        try:
            self._collection.document(record.id).create(record.model_dump(mode='python'))
        except Conflict:
            return False
        return True

    def get_by_id(self, code: str) -> URLRecord | None:
        snapshot = self._collection.document(code).get()
        if not snapshot.exists:
            return None
        record = URLRecord.model_validate(snapshot.to_dict())
        if record.id != code:
            raise ValueError('Firestore document ID does not match record ID')
        return record
