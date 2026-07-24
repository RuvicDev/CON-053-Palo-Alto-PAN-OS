"""Conector Ruvic de administración para Palo Alto PAN-OS."""

from .client import PanosClient
from .config import ENV_PREFIX, PanosConfig
from .exceptions import (
    PanosAuthError,
    PanosConnectorError,
    PanosDataError,
    PanosNetworkError,
)
from .logging_utils import setup_logging

__all__ = [
    "ENV_PREFIX",
    "PanosAuthError",
    "PanosClient",
    "PanosConfig",
    "PanosConnectorError",
    "PanosDataError",
    "PanosNetworkError",
    "setup_logging",
]

__version__ = "1.0.0"
