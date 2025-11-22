import os
import sys

CURRENT_DIR = os.path.dirname(__file__)

BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from modules.comercial.dashboard.run_dashboard_v2 import run


def main():
    payload = {
        "dashboard_name": "comercial_2024_2025",
        "periodicidade": "mensal",
        "mes": 11,
        "ano": 2025,
        "enviar_whatsapp": False,
    }

    print("=== TESTE LOCAL ===")
    print("Payload enviado:", payload)

    resultado = run(payload)

    print("\n=== RESULTADO ===")
    print(resultado)


if __name__ == "__main__":
    main()
