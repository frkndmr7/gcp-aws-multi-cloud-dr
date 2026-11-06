import logging
import secrets
import string
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from app.config import Settings
from app.models import CreateURL, URLRecord
from app.repositories.base import URLRepository
from app.repositories.memory import InMemoryRepository

logger = logging.getLogger(__name__)


def generate_code() -> str:
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))


def create_app(settings: Settings | None = None, repository: URLRepository | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    repo = repository if repository is not None else InMemoryRepository()
    app = FastAPI(title='URL Shortener', docs_url=None, redoc_url=None, openapi_url=None)

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
            if repo.create_if_absent(record):
                return {'code': record.id, 'short_path': f'/r/{record.id}'}
        raise HTTPException(status_code=503, detail='Unable to allocate a short code')

    @app.get('/r/{code}')
    def redirect(code: str) -> RedirectResponse:
        record = repo.get_by_id(code)
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

    return app


app = create_app()
