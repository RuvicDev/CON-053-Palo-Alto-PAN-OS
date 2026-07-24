---
name: panos
description: >
  Usa la librería ruvic_panos_connector para administrar un firewall
  Palo Alto PAN-OS - listar reglas de seguridad (list_rules), agregar
  un objeto de dirección (add_object), y confirmar (commit) los cambios
  de configuración pendientes (commit). Úsala cuando el usuario pida
  revisar reglas de firewall, agregar una IP/subred, o aplicar cambios
  de configuración en PAN-OS.
triggers:
- palo alto
- pan-os
- panos
- firewall palo alto
---

# Conector Palo Alto PAN-OS (ruvic_panos_connector)

Librería Python de administración para Palo Alto PAN-OS. Está **preinstalada en el runtime** cuando el conector está configurado (si no, instálala con `pip install git+https://github.com/Dgirto/Palo-Alto-PAN-OS.git#subdirectory=lib`).

## Regla crítica de credenciales

El código generado **NUNCA hardcodea credenciales**. Siempre se leen de variables de entorno, disponibles cuando el conector `panos` está configurado:

| Variable | Contenido |
|----------|-----------|
| `RUVIC_PANOS_BASE_URL` | URL base del firewall/Panorama |
| `RUVIC_PANOS_API_KEY` | API Key |
| `RUVIC_PANOS_VSYS` | (opcional) VSYS, default `vsys1` |
| `RUVIC_PANOS_VERIFY_SSL` | (opcional) `true`/`false`, default `true` |
| `RUVIC_PANOS_CONNECT_TIMEOUT` | (opcional) timeout en segundos |

Si estas variables NO existen, el conector no está configurado: no generes código que lo use; indica al usuario que lo configure en **Settings → Conectores**.

## Este conector escribe (objetos y commit)

`add_object` crea un objeto real en la configuración candidata, y `commit` la aplica a la configuración activa del firewall — un commit afecta tráfico real de producción. Confirma con el usuario antes de hacer commit si no fue pedido explícitamente.

## Conexión (siempre igual)

```python
from ruvic_panos_connector import PanosClient

client = PanosClient()  # lee RUVIC_PANOS_* del entorno automáticamente
```

## Capacidad 1 — Listar reglas de seguridad

```python
rules = client.list_rules()
for r in rules:
    print(f"{r.get('@name')}: {r.get('action')}")
```

## Capacidad 2 — Agregar un objeto de dirección

```python
client.add_object("servidor-web", "10.0.0.5/32", description="Servidor web interno")
```

Este cambio queda en la configuración **candidata**; no toma efecto hasta que se haga `commit`.

## Capacidad 3 — Confirmar (commit) los cambios

```python
result = client.commit("Agregado objeto servidor-web")
print(result)  # {'job_id': '123', 'status': 'FIN', 'result': 'OK'}
```

El commit puede tardar hasta 2 minutos; el método espera (polling) hasta que el job termine antes de retornar.

## Manejo de errores

```python
from ruvic_panos_connector import (
    PanosAuthError, PanosDataError, PanosNetworkError,
)

try:
    result = client.commit()
except PanosAuthError:
    print("API Key inválida o sin permiso suficiente")
except PanosNetworkError:
    print("No se pudo alcanzar el firewall — reintenta en unos segundos")
except PanosDataError as e:
    print(f"Error de datos: {e}")
```

## Buenas prácticas al generar código

1. Lee credenciales SOLO de las variables `RUVIC_PANOS_*` (el constructor de `PanosClient` ya lo hace).
2. Nunca imprimas `RUVIC_PANOS_API_KEY` en logs ni en la salida.
3. `commit` aplica cambios a la configuración activa: nunca lo llames automáticamente después de `add_object` sin que el usuario lo confirme explícitamente.
4. El conector NO crea ni modifica reglas de seguridad — solo las consulta. Si el usuario pide crear/modificar una regla, indícale que esta capacidad no está disponible.
5. Verifica el `result` del commit (`"OK"` o `"FAIL"`) antes de informar éxito al usuario.
