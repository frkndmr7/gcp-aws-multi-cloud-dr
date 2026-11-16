import importlib
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

import app.lambda_handler
import app.main
from app.config import Settings
from app.models import URLRecord


def event(method: str, path: str, body: dict | None = None) -> dict:
    return {
        'version': '2.0', 'routeKey': '$default', 'rawPath': path, 'rawQueryString': '',
        'headers': {'content-type': 'application/json'},
        'requestContext': {'http': {'method': method, 'path': path, 'sourceIp': '127.0.0.1'}},
        'body': json.dumps(body) if body else None, 'isBase64Encoded': False,
    }


def test_handler_standby_health_and_redirect(monkeypatch) -> None:
    repo = MagicMock()
    repo.get_by_id.return_value = URLRecord(id='abc', original_url='https://example.com/',
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc), origin_cloud='gcp')
    application = app.main.create_app(settings=Settings(provider='aws', role='secondary', writer_mode='standby'), repository=repo)
    monkeypatch.setattr('app.main.app', application)
    handler = importlib.reload(app.lambda_handler).handler
    assert handler(event('GET', '/health/live'), {})['statusCode'] == 200
    assert handler(event('GET', '/health/dr'), {})['statusCode'] == 503
    status = handler(event('GET', '/api/status'), {})
    assert json.loads(status['body']) == {'serving_provider': 'aws', 'role': 'secondary', 'writer_mode': 'standby'}
    redirect = handler(event('GET', '/r/abc'), {})
    assert redirect['statusCode'] == 307
    assert redirect['headers']['location'] == 'https://example.com/'
    assert handler(event('POST', '/api/shorten', {'original_url': 'https://example.com/'}), {})['statusCode'] == 503
    repo.create_if_absent.assert_not_called()
