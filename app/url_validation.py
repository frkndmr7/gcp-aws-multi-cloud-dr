from ipaddress import ip_address
from pydantic import HttpUrl, TypeAdapter

_url_adapter = TypeAdapter(HttpUrl)


def validate_public_url(value: object) -> HttpUrl:
    """Validate URL syntax and literal hosts without making DNS or HTTP requests."""
    if not isinstance(value, str) or not value or len(value) > 2048:
        raise ValueError('URL must be a non-empty string of at most 2048 characters')
    url = _url_adapter.validate_python(value)
    host = (url.host or '').strip('[]').lower().rstrip('.')
    if not host or host == 'localhost' or host.endswith(('.localhost', '.local', '.internal')):
        raise ValueError('Local hostnames are not allowed')
    try:
        address = ip_address(host)
    except ValueError:
        if '.' not in host or all(part.isdecimal() or part.startswith('0x') for part in host.split('.')):
            raise ValueError('A public hostname is required')
    else:
        if not address.is_global or address.is_multicast or getattr(address, 'ipv4_mapped', None):
            raise ValueError('A public IP address is required')
    return url
