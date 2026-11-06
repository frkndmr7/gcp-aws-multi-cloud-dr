from datetime import datetime
from typing import Literal
from pydantic import BaseModel, HttpUrl, field_validator
from app.url_validation import validate_public_url


class CreateURL(BaseModel):
    original_url: HttpUrl

    @field_validator('original_url', mode='before')
    @classmethod
    def check_length(cls, value: object) -> object:
        return validate_public_url(value)


class URLRecord(BaseModel):
    id: str
    original_url: str
    created_at: datetime
    origin_cloud: Literal['gcp', 'aws']
    version: int = 1
