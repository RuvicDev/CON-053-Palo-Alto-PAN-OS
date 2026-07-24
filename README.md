# Conector Palo Alto PAN-OS (CON-053)

Conector Ruvic de administración para firewalls Palo Alto PAN-OS.
Combina la REST API (JSON) para consultar reglas y crear objetos, y la
XML API para confirmar (commit) cambios pendientes. Permite listar
reglas de seguridad, agregar un objeto de dirección, y hacer commit.

## Instalación

```bash
pip install git+https://github.com/Dgirto/Palo-Alto-PAN-OS.git#subdirectory=lib
```

Python 3.10+. Dependencias: `requests>=2.31,<3.0`, `urllib3>=2.0,<3.0`.

## Permisos requeridos en PAN-OS

Crea un rol de administrador personalizado (`Device → Admin Roles →
Add`) con acceso mínimo:

- **Read Only** sobre `Policies` (necesario para `list_rules`).
- **Read-Write** únicamente sobre `Objects → Addresses` (necesario para
  `add_object`).
- Permiso de **Commit** (necesario para `commit`).

Crea una cuenta de administrador asociada a ese rol y genera su API Key:

```bash
curl -k "https://firewall.empresa.com/api/?type=keygen&user=ruvic_admin&password=CAMBIA_ESTA_CONTRASEÑA"
```

No uses el rol `Superuser` ni una cuenta con acceso de escritura sobre
`Network`, `Device Setup` o `Policies`.

## Variables de entorno (`RUVIC_PANOS_*`)

| Variable | Obligatoria | Descripción |
|----------|-------------|-------------|
| `RUVIC_PANOS_BASE_URL` | Sí | URL base del firewall/Panorama |
| `RUVIC_PANOS_API_KEY` | Sí | API Key generada con `type=keygen` |
| `RUVIC_PANOS_VSYS` | No (default `vsys1`) | VSYS a administrar |
| `RUVIC_PANOS_VERIFY_SSL` | No (default `true`) | Verificar certificado TLS |
| `RUVIC_PANOS_CONNECT_TIMEOUT` | No (default `15`) | Timeout de conexión en segundos |

## Pruebas locales

Con un firewall PAN-OS real o una VM de evaluación (no hay imagen
Docker oficial pública; usa una instancia de laboratorio existente):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ./lib

export RUVIC_PANOS_BASE_URL=https://fw-lab.empresa.com
export RUVIC_PANOS_API_KEY=tu-api-key
export RUVIC_PANOS_VERIFY_SSL=false  # solo si el cert es autofirmado en el lab

python test_connection.py
python validate_local.py
```

Prueba también los casos de error (API Key inválida, objeto duplicado,
commit sin cambios pendientes) y verifica que los mensajes sean claros.

## Notas de integración

- `list_rules` es de solo lectura; `add_object` modifica la
  configuración **candidata** (no toma efecto hasta el commit);
  `commit` aplica los cambios a la configuración activa del firewall —
  afecta tráfico real de producción.
- El commit es asíncrono en PAN-OS: el conector inicia el job, sondea
  su estado cada 3 segundos (hasta 120s en total) vía la XML API, y
  retorna el resultado final (`OK` o `FAIL`).
- El conector combina dos APIs de PAN-OS: la REST API (`/restapi/...`,
  JSON) para reglas/objetos, y la XML API clásica (`/api/`) para el
  commit, ya que PAN-OS no expone un endpoint REST equivalente.
- No crea, modifica ni elimina reglas de seguridad — solo objetos de
  dirección y el commit de cambios ya presentes en la configuración
  candidata.
