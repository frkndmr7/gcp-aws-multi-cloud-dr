import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app
from app.repositories.memory import InMemoryRepository


def test_create_and_redirect() -> None:
    client = TestClient(create_app())
    created = client.post('/api/shorten', json={'original_url': 'https://example.com/test'})
    assert created.status_code == 201
    result = created.json()
    redirect = client.get(result['short_path'], follow_redirects=False)
    assert redirect.status_code == 307
    assert redirect.headers['location'] == 'https://example.com/test'


@pytest.mark.parametrize('url', ['', 'ftp://example.com', 'https://example.com/' + 'a' * 2049])
def test_invalid_url(url: str) -> None:
    assert TestClient(create_app()).post('/api/shorten', json={'original_url': url}).status_code == 422


def test_missing_code() -> None:
    assert TestClient(create_app()).get('/r/unknown').status_code == 404


@pytest.mark.parametrize('mode', ['standby', 'frozen'])
def test_write_modes(mode: str) -> None:
    client = TestClient(create_app(Settings(provider='aws', role='secondary', writer_mode=mode)))
    result = client.post('/api/shorten', json={'original_url': 'https://example.com'})
    assert result.status_code == 503
    assert result.headers['retry-after'] == '60'


def test_status_and_health() -> None:
    client = TestClient(create_app(Settings(provider='aws', role='secondary', writer_mode='standby')))
    result = client.get('/api/status')
    assert result.json() == {'serving_provider': 'aws', 'role': 'secondary', 'writer_mode': 'standby'}
    assert result.headers['cache-control'] == 'no-store'
    assert client.get('/health/live').status_code == 200
    assert client.get('/health/dr').status_code == 503
    assert TestClient(create_app(Settings(dr_ready=True))).get('/health/dr').status_code == 200


def test_collision_retries_without_overwriting(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import main
    codes = iter(['same', 'same', 'other'])
    monkeypatch.setattr(main, 'generate_code', lambda: next(codes))
    client = TestClient(create_app(repository=InMemoryRepository()))
    assert client.post('/api/shorten', json={'original_url': 'https://first.example/'}).json()['code'] == 'same'
    assert client.post('/api/shorten', json={'original_url': 'https://second.example/'}).json()['code'] == 'other'
    assert client.get('/r/same', follow_redirects=False).headers['location'] == 'https://first.example/'


def test_aws_default_is_standby(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('SERVING_PROVIDER', 'aws')
    monkeypatch.delenv('CLOUD_ROLE', raising=False)
    monkeypatch.delenv('WRITER_MODE', raising=False)
    assert Settings.from_env() == Settings(provider='aws', role='secondary', writer_mode='standby')
