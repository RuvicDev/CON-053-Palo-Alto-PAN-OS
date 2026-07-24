"""Configuración del conector leída desde variables de entorno.

Convención de la plataforma: cada campo del formulario de configuración
llega como variable de entorno {ENV_PREFIX}{CAMPO} en mayúsculas.
Para este conector el prefijo es RUVIC_PANOS_.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

ENV_PREFIX = "RUVIC_PANOS_"

_TRUE_VALUES = {"1", "true", "yes", "on"}


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in _TRUE_VALUES


@dataclass(frozen=True)
class PanosConfig:
    """Parámetros de conexión a un firewall/Panorama Palo Alto (PAN-OS)."""

    base_url: str
    api_key: str
    vsys: str
    verify_ssl: bool
    connect_timeout: int = 15

    @classmethod
    def from_env(cls) -> "PanosConfig":
        """Construye la configuración desde las variables RUVIC_PANOS_*.

        Raises:
            ValueError: si falta alguna variable obligatoria.

        Ejemplo:
            >>> config = PanosConfig.from_env()
            >>> config.base_url
            'https://firewall.empresa.com'
        """
        missing = [
            f"{ENV_PREFIX}{name}"
            for name in ("BASE_URL", "API_KEY")
            if not os.environ.get(f"{ENV_PREFIX}{name}")
        ]
        if missing:
            raise ValueError(
                "Faltan variables de entorno del conector panos: "
                + ", ".join(missing)
                + ". Configura el conector en Settings → Conectores."
            )
        return cls(
            base_url=os.environ[f"{ENV_PREFIX}BASE_URL"].rstrip("/"),
            api_key=os.environ[f"{ENV_PREFIX}API_KEY"],
            vsys=os.environ.get(f"{ENV_PREFIX}VSYS", "vsys1"),
            verify_ssl=_as_bool(os.environ.get(f"{ENV_PREFIX}VERIFY_SSL"), True),
            connect_timeout=int(os.environ.get(f"{ENV_PREFIX}CONNECT_TIMEOUT", "15")),
        )
