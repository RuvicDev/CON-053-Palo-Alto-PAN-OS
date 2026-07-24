"""Validación local del conector panos: ejercita las 3 capacidades.

Uso:
    python validate_local.py

Requiere las variables RUVIC_PANOS_* exportadas en el entorno, con una
API Key generada por una cuenta de administrador con los permisos del
README (rol custom: Read Only sobre Policies, Read-Write sobre
Objects → Addresses y permiso de Commit).

ADVERTENCIA: este script agrega un objeto de dirección real
("ruvic-test-object") y ejecuta un commit real en el firewall/Panorama
configurado. Ejecútalo solo contra un entorno de pruebas.
"""

from ruvic_panos_connector import PanosClient, setup_logging

setup_logging("INFO")
client = PanosClient()

print("== 1. Listar reglas de seguridad ==")
rules = client.list_rules()
for r in rules[:5]:
    print(f"  {r.get('@name')}: {r.get('action')}")

print("== 2. Agregar objeto de dirección ==")
result = client.add_object("ruvic-test-object", "203.0.113.10/32", description="Prueba Ruvic")
print(f"  {result}")

print("== 3. Commit de cambios ==")
commit_result = client.commit("Prueba de validación local Ruvic")
print(f"  job_id={commit_result.get('job_id')} result={commit_result.get('result')}")

print("\nTodo OK: list_rules, add_object y commit funcionan.")
