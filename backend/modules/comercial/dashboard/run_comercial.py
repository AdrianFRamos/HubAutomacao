import os, time, json
import pyautogui, keyring
from datetime import datetime
from modules.comercial.dashboard.ui_helpers import (focus_window_by_title,save_full_screenshot,take_region_screenshot,multiscale_locate,click_image,)

BASE = os.path.dirname(__file__)
CFG_PATH = os.path.join(BASE, "config.json")

def log(msg):
    logs_dir = os.path.join(BASE, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    p = os.path.join(logs_dir, f"log_{datetime.now().strftime('%Y-%m-%d')}.txt")
    with open(p, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now()}] {msg}\n")
    print(msg)

def open_app():
    exe = cfg.get("caminho_executavel")
    if not exe:
        log("Executável não configurado em config.json (campo 'caminho_executavel' vazio).")
        return False
    if not os.path.isabs(exe):
        exe = os.path.join(os.path.dirname(__file__), exe)
    if not os.path.exists(exe):
        log("Executável não encontrado: " + str(exe))
        return False
    try:
        try:
            os.startfile(exe)
        except Exception:
            import subprocess
            subprocess.Popen([exe], shell=False)
        log("Executável iniciado: " + exe)
        return True
    except Exception as e:
        log("Erro ao abrir executável: " + str(e))
        return False

with open(CFG_PATH, "r", encoding="utf-8") as f:
    cfg = json.load(f)

IMG_DIR = os.path.join(BASE, cfg.get("images_path","images"))
ANNOT_DIR = os.path.join(BASE, cfg.get("images_annotated_path","images_annotated"))
SCREENSHOT_DIR = os.path.join(BASE, cfg.get("destino_screenshots","screenshots"))
LOGS_DIR = os.path.join(BASE, cfg.get("pasta_logs","logs"))
os.makedirs(SCREENSHOT_DIR, exist_ok=True); os.makedirs(LOGS_DIR, exist_ok=True)
SERVICE = "HubAutomacoes_SistemaBI"
SYSTEM_USER = cfg.get("default_user")
password = None
if SYSTEM_USER:
    try:
        password = keyring.get_password(SERVICE, f"{SYSTEM_USER}_password")
    except Exception:
        password = None
if not password:
    password = cfg.get("default_password")

def load_regions_from_annotations():
    jpath = os.path.join(ANNOT_DIR, "regions.json")
    if os.path.exists(jpath):
        try:
            with open(jpath,"r",encoding="utf-8") as f:
                js = json.load(f)
                for key in js:
                    if "relatorio_area" in key or "relatorio_full" in key or "relatorio" in key.lower():
                        return js[key]
                return next(iter(js.values()))
        except Exception as e:
            log("Erro lendo regions.json: " + str(e))
    return cfg.get("region_relatorio")

def focus_login_window():
    titles = ["Acesso", "Acesso - DELPHOS.BI", "Login", "DELPHOS.BI Principal"]
    for t in titles:
        if focus_window_by_title(t, timeout=2):
            log(f"Focado: {t}")
            return True
    login_full = os.path.join(IMG_DIR, "login_full.png")
    if os.path.exists(login_full):
        if click_image(login_full, confidence=0.6, timeout=4):
            log("Clique em login_full.png (fallback) para focar")
            time.sleep(0.6)
            return True
    try:
        pyautogui.keyDown('alt'); pyautogui.press('tab'); pyautogui.keyUp('alt')
        time.sleep(1)
        pyautogui.keyDown('alt');pyautogui.press('tab');pyautogui.keyUp('alt')
        time.sleep(1)
        log("Fallback Alt+Tab enviado")
        return True
    except Exception as e:
        log("Alt+Tab falhou: " + str(e))
    return False

def do_login_keyboard(username, pwd):
    if not focus_login_window():
        log("Não conseguiu focar janela de login.")
        return False
    time.sleep(2)
    pyautogui.typewrite(username, interval=0.03)
    time.sleep(2)
    pyautogui.press('tab')
    time.sleep(2)
    pyautogui.typewrite(pwd, interval=0.03)
    time.sleep(2)
    pyautogui.press('enter')
    log("Credenciais digitadas via teclado (username/tab/password/enter)")
    time.sleep(3.0)
    dash_img = os.path.join(IMG_DIR, "dashboard_full.png")
    if os.path.exists(dash_img):
        pos = None
        try:
            best = multiscale_locate(dash_img)
            if best and best.get("score",0) >= 0.65:
                log("Dashboard detectado por imagem após login (score: {:.2f})".format(best["score"]))
                return True
        except Exception:
            pass
    log("Continuando fluxo mesmo sem confirmação visual do dashboard (verifique).")
    return True

def keyboard_navigate_and_generate():
    focus_window_by_title(cfg.get("titulo_janela","DELPHOS.BI Principal"), timeout=4)
    time.sleep(1)
    pyautogui.press('f11')
    log("Pressionado F11 (Parametros do Sistema) - aguardando carregamento")
    time.sleep(2.0)
    for i in range(17):
        pyautogui.press('down')
        time.sleep(0.08)
    time.sleep(0.12)
    pyautogui.press('enter')  
    log("Navegado por 17 setas ↓ e pressionado Enter para selecionar a planilha")
    time.sleep(1.8)
    pyautogui.press('right')
    time.sleep(0.2)
    btn_exec = os.path.join(IMG_DIR, "btn_executar_rel.png")
    if os.path.exists(btn_exec):
        clicked = click_image(btn_exec, timeout=3, confidence=0.66)
        if clicked:
            log("Clicado em btn_executar_rel.png (X) para executar relatório")
        else:
            pyautogui.press('X')
            log("btn_executar_rel.png não encontrado - pressionado Enter como fallback")
    else:
        pyautogui.press('X')
        log("btn_executar_rel.png ausente - pressionado Enter para executar (fallback)")
    time.sleep(10.0) 
    log("Periodicidade ajustada para 'Mensal' ")
    pyautogui.keyDown('alt')
    pyautogui.press('down')
    time.sleep(5)
    pyautogui.press('down')
    time.sleep(5)
    log("Mês selecionado")
    pyautogui.press('left')
    pyautogui.keyUp('alt')
    time.sleep(2.5)
    pyautogui.press('enter')
    log("Pressionado Enter para atualizar relatório (finalizar)")
    time.sleep(4.0)
    region = load_regions_from_annotations()
    if not region:
        log("region_relatorio não configurado. Rode helper_pick_region.py se quiser capturar area especifica.")
        full = save_full_screenshot(SCREENSHOT_DIR, name_prefix="relatorio_full_fallback")
        log("Full screenshot salvo em " + full)
        return full
    else:
        path = take_region_screenshot(region, SCREENSHOT_DIR, name_prefix="Relatorio_Comercial")
        log("Screenshot (região) salvo em " + path)
        return path

def main():
    log("=== INICIANDO ROTINA (keyboard-first) ===")
    username = SYSTEM_USER or cfg.get("default_user")
    pwd = password or cfg.get("default_password")
    if not username or not pwd:
        log("Usuário/senha não configurados. Coloque config.json ou keyring.")
        return
    if cfg.get("caminho_executavel"):
        opened = open_app()
        if not opened:
            log("Falha ao abrir app; continue se o app já estiver aberto manualmente.")
    time.sleep(cfg.get("timeout_open", 6))
    ok = do_login_keyboard(username, pwd)
    if not ok:
        log("Falha no login (keyboard). Abortando.")
        return
    result = keyboard_navigate_and_generate()
    if result:
        try:
            from modules.comercial.dashboard.whatsapp import send_whatsapp_via_clipboard
        except Exception as e:
            log("Módulo whatsapp_clipboard não encontrado: " + str(e))
            send_wh_cb = None
        else:
            send_wh_cb = send_whatsapp_via_clipboard
        mensagem = cfg.get("mensagem_padrao", "Relatório automático - Comercial")
        numeros = cfg.get("numeros_whatsapp", [])
        if send_wh_cb:
            for num in numeros:
                try:
                    result_path = result if os.path.isabs(result) else os.path.join(os.path.dirname(__file__), result)
                    ok = send_wh_cb(num, result_path, caption=mensagem, wait_for_ready=8, focus_click_coord=None,
                                    logger=log)
                    log(f"Envio WhatsApp (clipboard) para {num} -> {ok}")
                    time.sleep(1.2)
                except Exception as e:
                    log(f"Erro envio WhatsApp para {num} (clipboard): {e}")
        else:
            log("Envio WhatsApp ignorado: whatsapp_clipboard não disponível.")
    log("=== ROTINA (keyboard-first) FINALIZADA ===")

if __name__ == "__main__":
    main()
