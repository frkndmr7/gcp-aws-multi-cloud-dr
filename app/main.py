import logging
import secrets
import string
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from app.config import Settings
from app.models import CreateURL, URLRecord
from app.repositories.base import URLRepository
from app.repositories.memory import InMemoryRepository

logger = logging.getLogger(__name__)


def generate_code() -> str:
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))


def create_app(settings: Settings | None = None, repository: URLRepository | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        client = None
        if repository is not None:
            app.state.repository = repository
        elif settings.repository_backend == 'memory':
            app.state.repository = InMemoryRepository()
        else:
            from google.cloud import firestore
            from app.repositories.firestore import FirestoreRepository
            client = firestore.Client(database='(default)')
            app.state.repository = FirestoreRepository(client)
        try:
            yield
        finally:
            if client is not None:
                client.close()

    app = FastAPI(title='URL Shortener', docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    # Existing callers that do not enter lifespan retain memory behavior.
    if repository is not None:
        app.state.repository = repository
    elif settings.repository_backend == 'memory':
        app.state.repository = InMemoryRepository()

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception('Unexpected application error', exc_info=exc)
        return JSONResponse(status_code=500, content={'detail': 'Internal server error'})

    @app.post('/api/shorten', status_code=201)
    def shorten(payload: CreateURL) -> dict[str, str]:
        if settings.writer_mode != 'active':
            raise HTTPException(status_code=503, detail='Writes are unavailable', headers={'Retry-After': '60'})
        for _ in range(5):
            record = URLRecord(id=generate_code(), original_url=str(payload.original_url),
                               created_at=datetime.now(timezone.utc), origin_cloud=settings.provider)
            if app.state.repository.create_if_absent(record):
                return {'code': record.id, 'short_path': f'/r/{record.id}'}
        raise HTTPException(status_code=503, detail='Unable to allocate a short code')

    @app.get('/r/{code}')
    def redirect(code: str) -> RedirectResponse:
        record = app.state.repository.get_by_id(code)
        if record is None:
            raise HTTPException(status_code=404, detail='Short code not found')
        return RedirectResponse(record.original_url, status_code=307)

    @app.get('/api/status')
    def status(response: Response) -> dict[str, str]:
        response.headers['Cache-Control'] = 'no-store'
        return {'serving_provider': settings.provider, 'role': settings.role, 'writer_mode': settings.writer_mode}

    @app.get('/health/live')
    def live() -> dict[str, str]:
        return {'status': 'live'}

    @app.get('/health/dr')
    def dr(response: Response) -> dict[str, str]:
        response.headers['Cache-Control'] = 'no-store'
        if not settings.dr_ready:
            response.status_code = 503
        return {'status': 'ready' if settings.dr_ready else 'not_ready'}

    static_dir = Path(__file__).resolve().parent / 'static'
    if static_dir.is_dir():
        app.mount('/assets', StaticFiles(directory=static_dir / 'assets'), name='assets')

        @app.get('/', include_in_schema=False)
        def index() -> FileResponse:
            return FileResponse(static_dir / 'index.html')

    return app


app = create_app()
