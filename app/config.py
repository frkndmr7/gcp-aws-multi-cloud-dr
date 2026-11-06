import os
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Settings:
    provider: Literal['gcp', 'aws'] = 'gcp'
    role: Literal['primary', 'secondary'] = 'primary'
    writer_mode: Literal['active', 'standby', 'frozen'] = 'active'
    dr_ready: bool = False

    def __post_init__(self) -> None:
        if self.provider not in ('gcp', 'aws') or self.role not in ('primary', 'secondary'):
            raise ValueError('Invalid provider or role')
        if self.writer_mode not in ('active', 'standby', 'frozen'):
            raise ValueError('Invalid writer mode')

    @classmethod
    def from_env(cls) -> 'Settings':
        provider = os.getenv('SERVING_PROVIDER', 'gcp')
        role = os.getenv('CLOUD_ROLE', 'primary' if provider == 'gcp' else 'secondary')
        mode = os.getenv('WRITER_MODE', 'active' if provider == 'gcp' else 'standby')
        ready = os.getenv('DR_READY', 'false').lower()
        if ready not in ('true', 'false'):
            raise ValueError('DR_READY must be true or false')
        return cls(provider=provider, role=role, writer_mode=mode, dr_ready=ready == 'true')
