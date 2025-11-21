import os
import sys

# Adiciona a pasta "backend" no sys.path para o Python enxergar o pacote "modules"
CURRENT_DIR = os.path.dirname(__file__)
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))
sys.path.append(BACKEND_DIR)

from modules.comercial.dashboard.run_dashboard_v2 import run

payload = {
    "dashboard_name": "comercial_2024_2025",
    "periodicidade": "mensal",
    "mes": 11,
    "ano": 2025,
}

print("=== TESTE LOCAL ===")
print("Payload enviado:", payload)

resultado = run(payload)

print("\n=== RESULTADO ===")
print(resultado)
