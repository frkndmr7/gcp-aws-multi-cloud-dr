import os
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Settings:
    provider: Literal['gcp', 'aws'] = 'gcp'
    role: Literal['primary', 'secondary'] = 'primary'
    writer_mode: Literal['active', 'standby', 'frozen'] = 'active'
    dr_ready: bool = False
    repository_backend: Literal['memory', 'firestore', 'dynamodb'] = 'memory'
    aws_region: str = ''
    dynamodb_table: str = ''

    def __post_init__(self) -> None:
        if self.provider not in ('gcp', 'aws') or self.role not in ('primary', 'secondary'):
            raise ValueError('Invalid provider or role')
        if self.writer_mode not in ('active', 'standby', 'frozen'):
            raise ValueError('Invalid writer mode')
        if self.repository_backend not in ('memory', 'firestore', 'dynamodb'):
            raise ValueError('Invalid repository backend')
        if self.repository_backend == 'dynamodb' and (not self.aws_region.strip() or not self.dynamodb_table.strip()):
            raise ValueError('AWS_REGION and DYNAMODB_TABLE are required for DynamoDB')

    @classmethod
    def from_env(cls) -> 'Settings':
        provider = os.getenv('SERVING_PROVIDER', 'gcp')
        role = os.getenv('CLOUD_ROLE', 'primary' if provider == 'gcp' else 'secondary')
        mode = os.getenv('WRITER_MODE', 'active' if provider == 'gcp' else 'standby')
        ready = os.getenv('DR_READY', 'false').lower()
        if ready not in ('true', 'false'):
            raise ValueError('DR_READY must be true or false')
        return cls(provider=provider, role=role, writer_mode=mode, dr_ready=ready == 'true',
                   repository_backend=os.getenv('REPOSITORY_BACKEND', 'memory'),
                   aws_region=os.getenv('AWS_REGION', ''), dynamodb_table=os.getenv('DYNAMODB_TABLE', ''))
