import os
import time
import json
from datetime import datetime
from typing import Dict, Any, Optional, List

import pyautogui
import keyring

from modules.comercial.dashboard.ui_helpers import (
    focus_window_by_title,
    save_full_screenshot,
    take_region_screenshot,
    multiscale_locate,
    click_image,
)

# OCR opcional
try:
    import pytesseract
    from pytesseract import Output as TesseractOutput
except Exception:
    pytesseract = None

BASE = os.path.dirname(__file__)
CFG_PATH = os.path.join(BASE, "config.json")
DASHBOARDS_CONFIG_PATH = os.path.join(BASE, "dashboards_config.json")


# =====================================================================
# LOG
# =====================================================================

def log(msg: str, logger=None):
    if logger and callable(logger):
        logger(msg)

    logs_dir = os.path.join(BASE, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    p = os.path.join(logs_dir, f"log_{datetime.now().strftime('%Y-%m-%d')}.txt")
    with open(p, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now()}] {msg}\n")
    print(msg)


# =====================================================================
# CONFIG / DASHBOARDS / CREDENCIAIS
# =====================================================================

def load_config() -> dict:
    if os.path.exists(CFG_PATH):
        with open(CFG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_dashboards_config() -> dict:
    if os.path.exists(DASHBOARDS_CONFIG_PATH):
        with open(DASHBOARDS_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_dashboard_config(dashboard_name: str) -> Optional[dict]:
    dashboards = load_dashboards_config()
    return dashboards.get("dashboards", {}).get(dashboard_name)


def get_credentials(cfg: dict) -> tuple[str, str]:
    SERVICE = "HubAutomacoes_SistemaBI"
    username = cfg.get("default_user")
    password = None

    if username:
        try:
            password = keyring.get_password(SERVICE, f"{username}_password")
        except Exception:
            password = None

    if not password:
        password = cfg.get("default_password")

    return username, password


# =====================================================================
# ABRIR APP
# =====================================================================

def open_app(cfg: dict) -> bool:
    exe = cfg.get("caminho_executavel")
    if not exe:
        log("Executável não configurado em config.json (campo 'caminho_executavel').")
        return False

    if not os.path.isabs(exe):
        exe = os.path.join(BASE, exe)

    if not os.path.exists(exe):
        log(f"Executável não encontrado: {exe}")
        return False

    try:
        try:
            os.startfile(exe)
        except Exception:
            import subprocess
            subprocess.Popen([exe], shell=False)
        log(f"Executável iniciado: {exe}")
        return True
    except Exception as e:
        log(f"Erro ao abrir executável: {e}")
        return False


# =====================================================================
# LOGIN (IGUAL AO TEU CÓDIGO ANTIGO)
# =====================================================================

def focus_login_window(cfg: dict, img_dir: str) -> bool:
    titles = ["Acesso", "Acesso - DELPHOS.BI", "Login", "DELPHOS.BI Principal"]
    for t in titles:
        if focus_window_by_title(t, timeout=2):
            log(f"Focado: {t}")
            return True

    login_full = os.path.join(img_dir, "login_full.png")
    if os.path.exists(login_full):
        if click_image(login_full, confidence=0.6, timeout=4):
            log("Clique em login_full.png (fallback) para focar")
            time.sleep(0.6)
            return True

    try:
        pyautogui.keyDown("alt")
        pyautogui.press("tab")
        pyautogui.keyUp("alt")
        time.sleep(1)
        pyautogui.keyDown("alt")
        pyautogui.press("tab")
        pyautogui.keyUp("alt")
        time.sleep(1)
        log("Fallback Alt+Tab enviado para focar login")
        return True
    except Exception as e:
        log(f"Alt+Tab falhou: {e}")

    return False


def do_login_keyboard(username: str, password: str, cfg: dict, img_dir: str) -> bool:
    if not focus_login_window(cfg, img_dir):
        log("Não conseguiu focar janela de login.")
        return False

    time.sleep(2)
    pyautogui.typewrite(username, interval=0.03)
    time.sleep(2)
    pyautogui.press("tab")
    time.sleep(2)
    pyautogui.typewrite(password, interval=0.03)
    time.sleep(2)
    pyautogui.press("enter")
    log("Credenciais digitadas via teclado (username/tab/password/enter)")
    time.sleep(3.0)

    dash_img = os.path.join(img_dir, "dashboard_full.png")
    if os.path.exists(dash_img):
        try:
            best = multiscale_locate(dash_img)
            if best and best.get("score", 0) >= 0.65:
                log("Dashboard detectado por imagem após login "
                    f"(score: {best['score']:.2f})")
                return True
        except Exception:
            pass

    log("Continuando fluxo mesmo sem confirmação visual do dashboard.")
    return True


# =====================================================================
# REGIÃO (regions.json OU CONFIG)
# =====================================================================

def load_regions_from_annotations(cfg: dict) -> Optional[List[int]]:
    annot_dir = os.path.join(BASE, cfg.get("images_annotated_path", "images_annotated"))
    jpath = os.path.join(annot_dir, "regions.json")

    if os.path.exists(jpath):
        try:
            with open(jpath, "r", encoding="utf-8") as f:
                js = json.load(f)
                for key in js:
                    if ("relatorio_area" in key or
                        "relatorio_full" in key or
                        "relatorio" in key.lower()):
                        return js[key]
                return next(iter(js.values()))
        except Exception as e:
            log(f"Erro lendo regions.json: {e}")

    return cfg.get("region_relatorio")


# =====================================================================
# LÓGICA ANTIGA ATÉ PLANILHAS (F11 + SETAS)
# =====================================================================

def navigate_to_planilhas_old(cfg: dict) -> bool:
    """
    Exatamente a parte antiga até chegar na tela de planilhas:

      - foca janela DELPHOS
      - F11
      - 17x seta para baixo
      - Enter

    Depois disso estamos com a tela de planilhas aberta
    (igual no keyboard_navigate_and_generate original).
    """
    focus_window_by_title(cfg.get("titulo_janela", "DELPHOS.BI Principal"), timeout=4)
    time.sleep(1)

    pyautogui.press("f11")
    log("Pressionado F11 (Parâmetros do Sistema) - aguardando carregamento")
    time.sleep(2.0)

    for i in range(17):
        pyautogui.press("down")
        time.sleep(0.08)
    time.sleep(0.12)

    pyautogui.press("enter")
    log("Navegado por 17 setas ↓ e pressionado Enter (tela de planilhas)")
    time.sleep(1.8)

    # NÃO aperto 'right' aqui. A partir daqui vamos usar a lógica nova
    # para localizar o dashboard na grade.
    return True


# =====================================================================
# NOVA LÓGICA: ACHAR DASHBOARD DENTRO DE PLANILHAS
# =====================================================================

def ocr_find_and_click(text: str, min_conf: int = 55) -> bool:
    if pytesseract is None:
        log("[OCR] pytesseract não disponível; ignorando OCR.")
        return False

    log(f"[OCR] procurando texto na tela: '{text}' (min_conf={min_conf})")

    screenshot = pyautogui.screenshot()
    if screenshot is None:
        log("[OCR] falha ao capturar screenshot.")
        return False

    try:
        data = pytesseract.image_to_data(
            screenshot,
            output_type=TesseractOutput.DICT,
            lang="por"
        )
    except Exception as e:
        log(f"[OCR] erro ao rodar pytesseract: {e}")
        return False

    target_low = text.lower()
    best_idx = None
    best_len = 0

    n_boxes = len(data["text"])
    for i in range(n_boxes):
        word = (data["text"][i] or "").strip()
        if not word:
            continue

        try:
            conf = float(data["conf"][i])
        except Exception:
            conf = 0.0

        if conf < min_conf:
            continue

        if target_low in word.lower():
            wl = len(word)
            if wl > best_len:
                best_len = wl
                best_idx = i

    if best_idx is None:
        log(f"[OCR] nenhum match relevante para '{text}' na tela.")
        return False

    x = data["left"][best_idx] + data["width"][best_idx] // 2
    y = data["top"][best_idx] + data["height"][best_idx] // 2

    pyautogui.moveTo(x, y, duration=0.2)
    pyautogui.click()
    log(f"[OCR] clique aproximado em '{text}' em ({x}, {y})")
    time.sleep(0.8)
    return True


def find_and_click_dashboard(dashboard_config: dict, img_dir: str) -> bool:
    """
    Dentro da tela de Planilhas:
      1) tenta achar pelo search_image com scroll
      2) se não achar, tenta OCR pelo search_text
    """
    search_text = dashboard_config.get("search_text")
    search_image = dashboard_config.get("search_image")

    # 1) por imagem
    if search_image:
        img_path = os.path.join(img_dir, search_image)
        log(f"[DASH] procurando dashboard via imagem: {img_path}")
        if os.path.exists(img_path):
            screen_width, screen_height = pyautogui.size()
            center_x = screen_width // 2
            center_y = int(screen_height * 0.6)

            max_attempts = 10
            for i in range(1, max_attempts + 1):
                log(f"[DASH] Tentativa {i}/{max_attempts} de localizar dashboard por imagem")
                try:
                    result = click_image(img_path, timeout=2, confidence=0.65)
                except Exception as e:
                    log(f"[DASH] Erro em click_image: {e}")
                    result = False

                if result:
                    log(f"[DASH] dashboard encontrado por imagem: {search_image}")
                    return True

                pyautogui.moveTo(center_x, center_y, duration=0.1)
                pyautogui.scroll(-500)
                log(f"[DASH] scroll realizado na área da grade em ({center_x}, {center_y})")
                time.sleep(0.8)
        else:
            log(f"[DASH] imagem não encontrada em disco: {img_path}")

    # 2) por texto (OCR)
    if search_text:
        log(f"[DASH] tentando localizar dashboard via OCR pelo texto: '{search_text}'")
        screen_width, screen_height = pyautogui.size()
        center_x = screen_width // 2
        center_y = int(screen_height * 0.6)

        max_attempts = 8
        for i in range(1, max_attempts + 1):
            log(f"[DASH/OCR] Tentativa {i}/{max_attempts}")
            if ocr_find_and_click(search_text, min_conf=55):
                log(f"[DASH/OCR] dashboard '{search_text}' selecionado via OCR")
                return True

            pyautogui.moveTo(center_x, center_y, duration=0.1)
            pyautogui.scroll(-500)
            log(f"[DASH/OCR] scroll realizado na área da grade em ({center_x}, {center_y})")
            time.sleep(0.8)

    log(f"[DASH] Não foi possível encontrar dashboard: {search_text}")
    return False


# =====================================================================
# EXECUTAR DASH SELECIONADO + PRINT (BASEADO NA TUA LÓGICA ANTIGA)
# =====================================================================

def execute_dashboard_and_capture(
    cfg: dict,
    img_dir: str,
    screenshot_dir: str,
    dashboard_name: str,
    dashboard_config: dict,
    periodicidade: str,
    dia: Optional[int],
    mes: Optional[int],
    ano: Optional[int],
) -> str:
    """
    Assume que a linha do dashboard já foi clicada na grade.
    Aqui reaproveita a lógica antiga:

      - RIGHT
      - botão executar (imagem ou tecla X)
      - ajuste simplificado de periodicidade
      - screenshot região / full
    """
    pyautogui.press("right")
    time.sleep(0.2)

    btn_exec = os.path.join(img_dir, "btn_executar_rel.png")
    if os.path.exists(btn_exec):
        try:
            clicked = click_image(btn_exec, timeout=3, confidence=0.66)
        except Exception as e:
            log(f"[EXEC] erro ao tentar click_image no botão executar: {e}")
            clicked = False

        if clicked:
            log("[EXEC] Clicado em btn_executar_rel.png para executar relatório")
        else:
            pyautogui.press("X")
            log("[EXEC] btn_executar_rel.png não encontrado - pressionado X como fallback")
    else:
        pyautogui.press("X")
        log("[EXEC] btn_executar_rel.png ausente - pressionado X para executar (fallback)")

    time.sleep(10.0)

    log(f"[EXEC] Ajustando periodicidade para '{periodicidade}' (fluxo keyboard antigo)")
    pyautogui.keyDown("alt")
    pyautogui.press("down")
    time.sleep(5)
    pyautogui.press("down")
    time.sleep(5)
    log("[EXEC] Mês selecionado (fluxo simplificado)")
    pyautogui.press("left")
    pyautogui.keyUp("alt")
    time.sleep(2.5)
    pyautogui.press("enter")
    log("[EXEC] Pressionado Enter para atualizar relatório (finalizar)")
    time.sleep(4.0)

    os.makedirs(screenshot_dir, exist_ok=True)

    region = dashboard_config.get("screenshot_region")
    if not region:
        region = load_regions_from_annotations(cfg)

    if not region:
        log("[EXEC] Nenhuma região definida; usando screenshot completo.")
        full = save_full_screenshot(
            screenshot_dir,
            name_prefix=f"dashboard_{dashboard_name}_full"
        )
        log("[EXEC] Full screenshot salvo em " + full)
        return full
    else:
        path = take_region_screenshot(
            region,
            screenshot_dir,
            name_prefix=f"Dashboard_{dashboard_name}"
        )
        log("[EXEC] Screenshot (região) salvo em " + path)
        return path


# =====================================================================
# WHATSAPP
# =====================================================================

def send_whatsapp_report(screenshot_path: str, numeros: list, mensagem: str):
    try:
        from modules.comercial.dashboard.whatsapp import send_whatsapp_via_clipboard
    except Exception as e:
        log(f"Módulo whatsapp não encontrado: {e}")
        return

    for num in numeros:
        try:
            result_path = (
                screenshot_path
                if os.path.isabs(screenshot_path)
                else os.path.join(BASE, screenshot_path)
            )
            ok = send_whatsapp_via_clipboard(
                num,
                result_path,
                caption=mensagem,
                wait_for_ready=8,
                focus_click_coord=None,
                logger=log,
            )
            log(f"Envio WhatsApp para {num} -> {ok}")
            time.sleep(1.2)
        except Exception as e:
            log(f"Erro envio WhatsApp para {num}: {e}")


# =====================================================================
# RUN PRINCIPAL (INTERFACE USADA PELO BACKEND)
# =====================================================================

def run(payload: Dict[str, Any] = None) -> Dict[str, Any]:
    log("=== INICIANDO AUTOMAÇÃO V2 (antiga até Planilhas, nova depois) ===")

    if payload is None:
        payload = {}

    cfg = load_config()
    dashboard_name = payload.get("dashboard_name")
    if not dashboard_name:
        err = "dashboard_name não informado"
        log(f"ERRO: {err}")
        return {
            "ok": False,
            "error": err,
            "message": "É necessário informar o nome do dashboard",
        }

    dashboard_config = get_dashboard_config(dashboard_name)
    if not dashboard_config:
        err = f"Dashboard '{dashboard_name}' não encontrado na configuração"
        log(f"ERRO: {err}")
        return {
            "ok": False,
            "error": "Dashboard não configurado",
            "message": err,
        }

    periodicidade = payload.get("periodicidade", "mensal")
    mes = payload.get("mes")
    ano = payload.get("ano")
    dia = payload.get("dia")

    img_dir = os.path.join(BASE, cfg.get("images_path", "images"))
    screenshot_dir = payload.get(
        "_workspace",
        cfg.get("destino_screenshots", "screenshots")
    )

    username, password = get_credentials(cfg)
    if not username or not password:
        msg = "Usuário/senha não configurados (config.json ou keyring)."
        log(msg)
        return {
            "ok": False,
            "error": "Credenciais não configuradas",
            "message": msg,
        }

    enviar_wh = payload.get("enviar_whatsapp", True)
    numeros_wh = payload.get("numeros_whatsapp", cfg.get("numeros_whatsapp", []))
    mensagem = payload.get(
        "mensagem",
        cfg.get(
            "mensagem_padrao",
            f"Relatório {dashboard_config.get('display_name', dashboard_name)}"
        ),
    )

    try:
        if cfg.get("caminho_executavel"):
            opened = open_app(cfg)
            if not opened:
                log("Falha ao abrir app; continuando se já estiver aberto manualmente.")

        time.sleep(cfg.get("timeout_open", 6))

        if not do_login_keyboard(username, password, cfg, img_dir):
            return {
                "ok": False,
                "error": "Falha no login",
                "message": "Não foi possível fazer login no sistema",
            }

        # 1) lógica ANTIGA até Planilhas
        if not navigate_to_planilhas_old(cfg):
            return {
                "ok": False,
                "error": "Falha na navegação (Planilhas)",
                "message": "Não foi possível chegar na tela de Planilhas",
            }

        # 2) lógica NOVA: localizar dashboard na grade
        if not find_and_click_dashboard(dashboard_config, img_dir):
            return {
                "ok": False,
                "error": "Falha na navegação",
                "message": f"Não foi possível localizar o dashboard '{dashboard_name}' na grade",
            }

        # 3) executar relatório + screenshot (baseado no teclado antigo)
        screenshot_path = execute_dashboard_and_capture(
            cfg,
            img_dir,
            screenshot_dir,
            dashboard_name,
            dashboard_config,
            periodicidade,
            dia,
            mes,
            ano,
        )

        if enviar_wh and numeros_wh:
            send_whatsapp_report(screenshot_path, numeros_wh, mensagem)

        log("=== AUTOMAÇÃO V2 CONCLUÍDA COM SUCESSO ===")

        return {
            "ok": True,
            "message": f"Dashboard {dashboard_config.get('display_name')} gerado com sucesso",
            "screenshot": screenshot_path,
            "dashboard": dashboard_name,
            "periodicidade": periodicidade,
            "whatsapp_enviado": enviar_wh,
        }

    except Exception as e:
        import traceback
        log(f"ERRO: {e}")
        log(traceback.format_exc())
        return {
            "ok": False,
            "error": str(e),
            "message": "Erro durante execução da automação",
        }


# =====================================================================
# MAIN PARA TESTE LOCAL
# =====================================================================

def main():
    result = run(
        {
            "dashboard_name": "comercial_2024_2025",
            "periodicidade": "mensal",
            "mes": 11,
            "ano": 2025,
        }
    )
    if not result.get("ok"):
        log(f"ERRO: {result.get('error')}")
    else:
        log(f"OK: {result.get('message')}")


if __name__ == "__main__":
    main()
