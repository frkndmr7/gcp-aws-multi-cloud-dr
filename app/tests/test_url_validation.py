import pytest
from pydantic import ValidationError
from app.url_validation import validate_public_url
from fastapi.testclient import TestClient
from app.main import create_app


@pytest.mark.parametrize('url', ['https://example.com/path', 'http://8.8.8.8', 'https://[2606:4700:4700::1111]/'])
def test_public_urls(url: str) -> None:
    assert validate_public_url(url).scheme in ('http', 'https')


@pytest.mark.parametrize('url', ['', 'ftp://example.com', 'https://localhost.', 'http://a.localhost',
    'http://printer.local', 'http://intranet', 'http://127.0.0.1', 'http://127.1',
    'http://10.0.0.1', 'http://169.254.169.254', 'http://192.168.1.1',
    'http://[::1]', 'http://[fc00::1]', 'http://[fe80::1]', 'http://[::ffff:8.8.8.8]',
    'http://0.0.0.0', 'http://224.0.0.1', 'http://bad host', 'https://example.com/' + 'a' * 2049])
def test_non_public_or_invalid_urls(url: str) -> None:
    with pytest.raises((ValueError, ValidationError)):
        validate_public_url(url)
    assert TestClient(create_app()).post('/api/shorten', json={'original_url': url}).status_code == 422
