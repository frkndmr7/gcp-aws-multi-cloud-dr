from pathlib import Path
from fastapi.testclient import TestClient
from app.main import create_app


def test_static_ui_and_api_are_separate(monkeypatch, tmp_path: Path) -> None:
    import app.main as main
    fake_app = tmp_path / 'main.py'
    fake_app.touch()
    static = tmp_path / 'static'
    (static / 'assets').mkdir(parents=True)
    (static / 'index.html').write_text('<html>UI</html>')
    (static / 'assets' / 'test.js').write_text('ok')
    monkeypatch.setattr(main, '__file__', str(fake_app))
    with TestClient(create_app()) as client:
        assert 'UI' in client.get('/').text
        assert client.get('/assets/test.js').text == 'ok'
        assert client.get('/api/missing').status_code == 404
        assert client.get('/health/live').json() == {'status': 'live'}
