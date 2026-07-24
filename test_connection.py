"""Prueba de conexión estándar del conector panos.

Firma estándar Ruvic: def test_connection() -> tuple[bool, str]
- Lee la configuración EXCLUSIVAMENTE de las env vars RUVIC_PANOS_*.
- Nunca lanza excepciones; retorna (ok, mensaje).

Ejecutable también como script para pruebas locales:
    python test_connection.py
"""

from __future__ import annotations


def test_connection() -> tuple[bool, str]:
    """Conecta al firewall/Panorama PAN-OS y valida la API Key usando las
    env vars RUVIC_PANOS_*."""
    try:
        from ruvic_panos_connector import (
            PanosAuthError,
            PanosClient,
            PanosDataError,
            PanosNetworkError,
        )
    except ImportError:
        return (
            False,
            "La librería ruvic-panos-connector no está instalada. "
            "Instala con: pip install git+https://github.com/Dgirto/"
            "Palo-Alto-PAN-OS.git#subdirectory=lib",
        )

    try:
        client = PanosClient()  # valida que existan las env vars
    except ValueError as exc:
        return False, str(exc)

    try:
        client.ping()
    except PanosAuthError as exc:
        return False, f"Autenticación fallida: {exc}"
    except PanosNetworkError as exc:
        return False, f"Error de red: {exc}"
    except PanosDataError as exc:
        return False, f"Error de datos: {exc}"
    except Exception as exc:  # red de seguridad: jamás propagar
        return False, f"Error inesperado: {exc}"

    return (
        True,
        f"Conexión exitosa a PAN-OS ({client.config.base_url}, vsys={client.config.vsys!r})",
    )


if __name__ == "__main__":
    ok, message = test_connection()
    print(f"{'OK' if ok else 'FALLO'}: {message}")
    raise SystemExit(0 if ok else 1)
