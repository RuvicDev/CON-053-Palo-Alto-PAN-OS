"""Excepciones propias del conector PAN-OS.

Separan los tres tipos de fallo que el usuario debe distinguir:
autenticación, red/servidor y datos. Nunca exponemos excepciones
crípticas del cliente HTTP subyacente.
"""


class PanosConnectorError(Exception):
    """Error base del conector."""


class PanosAuthError(PanosConnectorError):
    """Credenciales inválidas o permisos insuficientes."""


class PanosNetworkError(PanosConnectorError):
    """No se pudo alcanzar el firewall/Panorama (red/timeout)."""


class PanosDataError(PanosConnectorError):
    """La operación es válida pero la regla/objeto es inválido."""
