"""Cliente de administración de reglas y objetos para Palo Alto PAN-OS.

Usa la REST API (JSON) para consultar reglas y crear objetos, y la XML
API para el commit (PAN-OS no expone un endpoint REST de commit).

Capacidades:
- list_rules():   listar reglas de seguridad.
- add_object():    agregar un objeto de dirección.
- commit():        confirmar (commit) los cambios pendientes.

Las credenciales SIEMPRE provienen de variables de entorno RUVIC_PANOS_*
(ver config.PanosConfig.from_env). Prohibido hardcodearlas.
"""

from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from typing import Any
from xml.sax.saxutils import escape as _xml_escape

import requests
import urllib3

from .config import PanosConfig
from .exceptions import PanosAuthError, PanosDataError, PanosNetworkError
from .logging_utils import get_logger

_REST_API_VERSION = "v10.1"
_COMMIT_POLL_INTERVAL = 3
_COMMIT_MAX_WAIT = 120


def _require_str(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise PanosDataError(f"{field} debe ser un string, no {type(value).__name__}.")
    return value


class PanosClient:
    """Cliente de administración de un firewall Palo Alto (PAN-OS).

    Args:
        config: configuración de conexión. Si se omite, se lee de las
            variables de entorno RUVIC_PANOS_* (comportamiento estándar
            en el runtime de la plataforma).

    Ejemplo:
        >>> client = PanosClient()  # lee RUVIC_PANOS_* del entorno
        >>> client.list_rules()
        [{'@name': 'allow-web', 'action': 'allow', ...}]
    """

    def __init__(self, config: PanosConfig | None = None) -> None:
        self.config = config or PanosConfig.from_env()
        self._logger = get_logger()
        self._session = requests.Session()
        self._session.verify = self.config.verify_ssl
        if not self.config.verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # ------------------------------------------------------------------ #
    # Conexión
    # ------------------------------------------------------------------ #

    def _rest_request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self.config.base_url}/restapi/{_REST_API_VERSION}{path}"
        headers = {"X-PAN-KEY": self.config.api_key, "Accept": "application/json"}
        try:
            response = self._session.request(
                method, url, headers=headers, timeout=self.config.connect_timeout, **kwargs
            )
        except requests.exceptions.RequestException as exc:
            raise PanosNetworkError(
                f"No se pudo alcanzar PAN-OS en {self.config.base_url!r}: {exc}"
            ) from exc

        if response.status_code in (401, 403):
            raise PanosAuthError(
                "API Key inválida o sin permiso suficiente para esta operación."
            )
        if response.status_code >= 400:
            raise PanosDataError(
                f"PAN-OS respondió {response.status_code}: {response.text[:300]}"
            )
        return response.json()

    def _xml_request(self, params: dict[str, str]) -> ET.Element:
        url = f"{self.config.base_url}/api/"
        params = {**params, "key": self.config.api_key}
        try:
            response = self._session.get(url, params=params, timeout=self.config.connect_timeout)
        except requests.exceptions.RequestException as exc:
            raise PanosNetworkError(
                f"No se pudo alcanzar PAN-OS en {self.config.base_url!r}: {exc}"
            ) from exc

        try:
            root = ET.fromstring(response.text)
        except ET.ParseError as exc:
            raise PanosDataError(f"Respuesta XML inválida de PAN-OS: {exc}") from exc

        status = root.attrib.get("status")
        if status == "error":
            code = root.attrib.get("code", "")
            msg_el = root.find(".//msg")
            message = msg_el.text if msg_el is not None else response.text[:300]
            if code in ("403", "16"):
                raise PanosAuthError(f"API Key inválida o sin permiso suficiente: {message}")
            raise PanosDataError(f"PAN-OS respondió error ({code}): {message}")
        return root

    def ping(self) -> bool:
        """Verifica la conexión consultando la info del sistema.

        Returns:
            True si la conexión funciona.

        Raises:
            PanosAuthError / PanosNetworkError / PanosDataError según el
            fallo.
        """
        self._xml_request({"type": "op", "cmd": "<show><system><info></info></system></show>"})
        self._logger.info("Ping exitoso a PAN-OS %s", self.config.base_url)
        return True

    # ------------------------------------------------------------------ #
    # Capacidad 1: listar reglas de seguridad
    # ------------------------------------------------------------------ #

    def list_rules(self) -> list[dict[str, Any]]:
        """Lista las reglas de seguridad del vsys configurado.

        Returns:
            Lista de dicts, una por regla (incluye @name, action, from,
            to, source, destination).

        Ejemplo:
            >>> client.list_rules()
            [{'@name': 'allow-web', 'action': 'allow', ...}]
        """
        data = self._rest_request(
            "GET",
            "/Policies/SecurityRules",
            params={"location": "vsys", "vsys": self.config.vsys},
        )
        entries = data.get("result", {}).get("entry", [])
        self._logger.info("Se listaron %d reglas de seguridad", len(entries))
        return entries

    # ------------------------------------------------------------------ #
    # Capacidad 2: agregar objeto de dirección
    # ------------------------------------------------------------------ #

    def add_object(self, name: str, ip: str, description: str = "") -> dict[str, Any]:
        """Agrega un objeto de dirección (address object).

        Args:
            name: nombre del objeto (único en el vsys).
            ip: dirección en formato IP, IP/CIDR o rango.
            description: descripción opcional.

        Returns:
            Dict con la respuesta de PAN-OS.

        Ejemplo:
            >>> client.add_object("servidor-web", "10.0.0.5/32")
            {'@name': 'servidor-web', ...}
        """
        name = _require_str(name, "name").strip()
        ip = _require_str(ip, "ip").strip()
        if not name or not ip:
            raise PanosDataError("name e ip no pueden estar vacíos.")
        body = {"entry": {"@name": name, "ip-netmask": ip, "description": description}}
        data = self._rest_request(
            "POST",
            "/Objects/Addresses",
            params={"location": "vsys", "vsys": self.config.vsys, "name": name},
            json=body,
        )
        self._logger.info('Objeto de dirección creado: "%s" (%s)', name, ip)
        return data.get("result", {})

    # ------------------------------------------------------------------ #
    # Capacidad 3: commit de cambios pendientes
    # ------------------------------------------------------------------ #

    def commit(self, description: str = "Commit desde Ruvic") -> dict[str, Any]:
        """Confirma (commit) los cambios de configuración pendientes.

        Args:
            description: descripción del commit (visible en el historial
                de PAN-OS).

        Returns:
            Dict con: job_id, status ("FIN"), result ("OK" o "FAIL").

        Ejemplo:
            >>> client.commit("Agregado objeto servidor-web")
            {'job_id': '123', 'status': 'FIN', 'result': 'OK'}
        """
        description = _require_str(description, "description")
        cmd = f"<commit><description>{_xml_escape(description)}</description></commit>"
        root = self._xml_request({"type": "commit", "cmd": cmd})
        job_el = root.find(".//job")
        if job_el is None:
            raise PanosDataError("PAN-OS no retornó un job_id para el commit.")
        job_id = job_el.text

        waited = 0
        while waited < _COMMIT_MAX_WAIT:
            status_root = self._xml_request(
                {"type": "op", "cmd": f"<show><jobs><id>{job_id}</id></jobs></show>"}
            )
            status = status_root.findtext(".//job/status") or ""
            if status == "FIN":
                result = status_root.findtext(".//job/result") or "UNKNOWN"
                self._logger.info("Commit %s finalizado: %s", job_id, result)
                return {"job_id": job_id, "status": status, "result": result}
            time.sleep(_COMMIT_POLL_INTERVAL)
            waited += _COMMIT_POLL_INTERVAL

        raise PanosDataError(f"El commit (job {job_id}) no terminó en {_COMMIT_MAX_WAIT}s.")
