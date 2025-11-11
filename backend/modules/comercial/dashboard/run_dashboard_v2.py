"""
Automação de Dashboards DELPHOS.BI - Versão 2.0
Navegação por menu hierárquico com busca visual
"""
import os, time, json
import pyautogui, keyring
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from modules.comercial.dashboard.ui_helpers import (
    focus_window_by_title,
    save_full_screenshot,
    take_region_screenshot,
    multiscale_locate,
    click_image,
)

BASE = os.path.dirname(__file__)
CFG_PATH = os.path.join(BASE, "config.json")
DASHBOARDS_CONFIG_PATH = os.path.join(BASE, "dashboards_config.json")

def log(msg: str, logger=None):
    """Log com suporte a logger externo"""
    if logger and callable(logger):
        logger(msg)
    else:
        logs_dir = os.path.join(BASE, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        p = os.path.join(logs_dir, f"log_{datetime.now().strftime('%Y-%m-%d')}.txt")
        with open(p, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] {msg}\n")
    print(msg)

def load_config() -> dict:
    """Carrega configuração geral"""
    if os.path.exists(CFG_PATH):
        with open(CFG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def load_dashboards_config() -> dict:
    """Carrega configuração de dashboards"""
    if os.path.exists(DASHBOARDS_CONFIG_PATH):
        with open(DASHBOARDS_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def get_dashboard_config(dashboard_name: str) -> Optional[dict]:
    """Obtém configuração de um dashboard específico"""
    dashboards = load_dashboards_config()
    return dashboards.get("dashboards", {}).get(dashboard_name)

def get_credentials(cfg: dict) -> tuple:
    """Obtém credenciais do keyring ou config"""
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

def open_app(cfg: dict) -> bool:
    """Abre o executável do sistema"""
    exe = cfg.get("caminho_executavel")
    if not exe:
        log("Executável não configurado")
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

def focus_login_window(cfg: dict, img_dir: str) -> bool:
    """Foca a janela de login"""
    titles = ["Acesso", "Acesso - DELPHOS.BI", "Login", "DELPHOS.BI Principal"]
    for t in titles:
        if focus_window_by_title(t, timeout=2):
            log(f"Focado: {t}")
            return True
    
    login_full = os.path.join(img_dir, "login_full.png")
    if os.path.exists(login_full):
        if click_image(login_full, confidence=0.6, timeout=4):
            log("Clique em login_full.png para focar")
            time.sleep(0.6)
            return True
    
    try:
        pyautogui.keyDown('alt')
        pyautogui.press('tab')
        pyautogui.keyUp('alt')
        time.sleep(1)
        log("Fallback Alt+Tab enviado")
        return True
    except Exception as e:
        log(f"Alt+Tab falhou: {e}")
    
    return False

def do_login_keyboard(username: str, password: str, cfg: dict, img_dir: str) -> bool:
    """Realiza login via teclado"""
    if not focus_login_window(cfg, img_dir):
        log("Não conseguiu focar janela de login")
        return False
    
    time.sleep(2)
    pyautogui.typewrite(username, interval=0.03)
    time.sleep(2)
    pyautogui.press('tab')
    time.sleep(2)
    pyautogui.typewrite(password, interval=0.03)
    time.sleep(2)
    pyautogui.press('enter')
    log("Credenciais digitadas via teclado")
    time.sleep(3.0)
    
    # Verifica se login foi bem-sucedido
    dash_img = os.path.join(img_dir, "dashboard_full.png")
    if os.path.exists(dash_img):
        try:
            best = multiscale_locate(dash_img)
            if best and best.get("score", 0) >= 0.65:
                log(f"Dashboard detectado (score: {best['score']:.2f})")
                return True
        except Exception:
            pass
    
    log("Continuando sem confirmação visual")
    return True

def click_menu_item_by_image(item_name: str, img_dir: str, timeout: int = 5) -> bool:
    """Clica em item do menu usando imagem de referência"""
    img_path = os.path.join(img_dir, "menu_items", f"{item_name}.png")
    
    if not os.path.exists(img_path):
        log(f"Imagem não encontrada: {img_path}")
        return False
    
    try:
        result = click_image(img_path, timeout=timeout, confidence=0.7)
        if result:
            log(f"Clicado em menu: {item_name}")
            time.sleep(0.5)
            return True
    except Exception as e:
        log(f"Erro ao clicar em {item_name}: {e}")
    
    return False

def click_menu_item_by_coords(x: int, y: int, item_name: str) -> bool:
    """Clica em item do menu usando coordenadas"""
    try:
        pyautogui.click(x, y)
        log(f"Clicado em menu: {item_name} ({x}, {y})")
        time.sleep(0.5)
        return True
    except Exception as e:
        log(f"Erro ao clicar em {item_name}: {e}")
        return False

def find_and_click_dashboard(dashboard_config: dict, img_dir: str) -> bool:
    """Procura e clica no dashboard específico"""
    search_text = dashboard_config.get("search_text")
    search_image = dashboard_config.get("search_image")
    
    # Método 1: Por imagem de referência
    if search_image:
        img_path = os.path.join(img_dir, "dashboards", search_image)
        if os.path.exists(img_path):
            try:
                result = click_image(img_path, timeout=5, confidence=0.75)
                if result:
                    log(f"Dashboard encontrado por imagem: {search_image}")
                    return True
            except Exception as e:
                log(f"Erro ao buscar por imagem: {e}")
    
    # Método 2: Por coordenadas (se configurado)
    if "click_coords" in dashboard_config:
        coords = dashboard_config["click_coords"]
        try:
            pyautogui.click(coords["x"], coords["y"])
            log(f"Dashboard clicado por coordenadas: ({coords['x']}, {coords['y']})")
            return True
        except Exception as e:
            log(f"Erro ao clicar por coordenadas: {e}")
    
    # Método 3: OCR (futuro)
    # TODO: Implementar busca por OCR
    
    log(f"Não foi possível encontrar dashboard: {search_text}")
    return False

def navigate_to_dashboard(dashboard_name: str, cfg: dict, img_dir: str) -> bool:
    """Navega até o dashboard especificado"""
    dashboard_config = get_dashboard_config(dashboard_name)
    
    if not dashboard_config:
        log(f"Dashboard '{dashboard_name}' não encontrado na configuração")
        return False
    
    # Foca janela principal
    focus_window_by_title(cfg.get("titulo_janela", "DELPHOS.BI Principal"), timeout=4)
    time.sleep(1)
    
    # Navega pelo menu hierárquico
    menu_path = dashboard_config.get("menu_path", [])
    
    log(f"Navegando pelo menu: {' → '.join(menu_path)}")
    
    for i, menu_item in enumerate(menu_path):
        # Tenta clicar por imagem primeiro
        if not click_menu_item_by_image(menu_item, img_dir):
            # Fallback: coordenadas fixas (se configurado)
            coords = dashboard_config.get(f"menu_coords_{i}")
            if coords:
                click_menu_item_by_coords(coords["x"], coords["y"], menu_item)
            else:
                log(f"Não foi possível clicar em: {menu_item}")
                return False
        
        time.sleep(0.8)
    
    # Clica no dashboard específico
    if not find_and_click_dashboard(dashboard_config, img_dir):
        return False
    
    log(f"Dashboard '{dashboard_config.get('display_name')}' selecionado")
    time.sleep(2.0)
    
    return True

def configure_period(periodicidade: str, dia: Optional[int] = None, 
                    mes: Optional[int] = None, ano: Optional[int] = None,
                    dashboard_config: dict = None) -> bool:
    """Configura período do dashboard (se aplicável)"""
    if not dashboard_config or not dashboard_config.get("has_period_selector"):
        log("Dashboard não possui seletor de período")
        return True
    
    # TODO: Implementar lógica de seleção de período
    # Isso depende de como cada dashboard específico funciona
    log(f"Configuração de período: {periodicidade} - {mes}/{ano}")
    
    return True

def capture_screenshot(region: Optional[List[int]], screenshot_dir: str, 
                      dashboard_name: str) -> str:
    """Captura screenshot da região do dashboard"""
    os.makedirs(screenshot_dir, exist_ok=True)
    
    if not region or len(region) != 4:
        # Fallback: screenshot completo
        full = save_full_screenshot(screenshot_dir, name_prefix=f"dashboard_{dashboard_name}_full")
        log(f"Screenshot completo salvo: {full}")
        return full
    else:
        path = take_region_screenshot(
            region, 
            screenshot_dir, 
            name_prefix=f"Dashboard_{dashboard_name}"
        )
        log(f"Screenshot (região) salvo: {path}")
        return path

def send_whatsapp_report(screenshot_path: str, numeros: list, mensagem: str):
    """Envia relatório via WhatsApp"""
    try:
        from modules.comercial.dashboard.whatsapp import send_whatsapp_via_clipboard
    except Exception as e:
        log(f"Módulo whatsapp não encontrado: {e}")
        return
    
    for num in numeros:
        try:
            ok = send_whatsapp_via_clipboard(
                num, 
                screenshot_path, 
                caption=mensagem, 
                wait_for_ready=8, 
                focus_click_coord=None,
                logger=log
            )
            log(f"Envio WhatsApp para {num} -> {ok}")
            time.sleep(1.2)
        except Exception as e:
            log(f"Erro envio WhatsApp para {num}: {e}")

def run(payload: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Função principal parametrizada - Versão 2.0
    
    Args:
        payload: Dicionário com parâmetros da execução
            - dashboard_name: str (obrigatório) - Nome/ID do dashboard
            - periodicidade: str (opcional) - "diario", "mensal" ou "anual"
            - mes: int (opcional) - Mês (1-12)
            - ano: int (opcional) - Ano
            - dia: int (opcional) - Dia (1-31)
            - screenshot_region: list (opcional) - [x, y, width, height]
            - enviar_whatsapp: bool (opcional) - Se deve enviar via WhatsApp
            - numeros_whatsapp: list (opcional) - Lista de números
            - mensagem: str (opcional) - Mensagem para WhatsApp
    
    Returns:
        Dict com resultado da execução
    """
    log("=== INICIANDO AUTOMAÇÃO V2 (Navegação por Menu) ===")
    
    if not payload:
        payload = {}
    
    # Carrega configurações
    cfg = load_config()
    
    # Parâmetros obrigatórios
    dashboard_name = payload.get("dashboard_name")
    if not dashboard_name:
        return {
            "ok": False,
            "error": "dashboard_name não informado",
            "message": "É necessário informar o nome do dashboard"
        }
    
    # Obtém configuração do dashboard
    dashboard_config = get_dashboard_config(dashboard_name)
    if not dashboard_config:
        return {
            "ok": False,
            "error": "Dashboard não configurado",
            "message": f"Dashboard '{dashboard_name}' não encontrado na configuração"
        }
    
    # Parâmetros opcionais
    periodicidade = payload.get("periodicidade", "mensal")
    mes = payload.get("mes")
    ano = payload.get("ano")
    dia = payload.get("dia")
    
    # Região de screenshot (usa padrão do dashboard se não informado)
    regiao = payload.get("screenshot_region")
    if not regiao:
        regiao = dashboard_config.get("screenshot_region")
    
    enviar_wh = payload.get("enviar_whatsapp", True)
    numeros_wh = payload.get("numeros_whatsapp", cfg.get("numeros_whatsapp", []))
    mensagem = payload.get("mensagem", f"Relatório {dashboard_config.get('display_name', dashboard_name)}")
    
    # Diretórios
    img_dir = os.path.join(BASE, cfg.get("images_path", "images"))
    screenshot_dir = payload.get("_workspace", cfg.get("destino_screenshots", "screenshots"))
    
    # Obtém credenciais
    username, password = get_credentials(cfg)
    if not username or not password:
        return {
            "ok": False,
            "error": "Credenciais não configuradas",
            "message": "Configure usuário/senha em config.json ou keyring"
        }
    
    try:
        # 1. Abre aplicativo (se configurado)
        if cfg.get("caminho_executavel"):
            opened = open_app(cfg)
            if not opened:
                log("Falha ao abrir app; continuando se já estiver aberto")
        
        time.sleep(cfg.get("timeout_open", 6))
        
        # 2. Login
        ok = do_login_keyboard(username, password, cfg, img_dir)
        if not ok:
            return {
                "ok": False,
                "error": "Falha no login",
                "message": "Não foi possível fazer login no sistema"
            }
        
        # 3. Navega até dashboard
        ok = navigate_to_dashboard(dashboard_name, cfg, img_dir)
        if not ok:
            return {
                "ok": False,
                "error": "Falha na navegação",
                "message": f"Não foi possível navegar até o dashboard '{dashboard_name}'"
            }
        
        # 4. Configura período (se aplicável)
        configure_period(periodicidade, dia, mes, ano, dashboard_config)
        
        # 5. Aguarda carregamento completo
        time.sleep(5.0)
        
        # 6. Captura screenshot
        screenshot_path = capture_screenshot(regiao, screenshot_dir, dashboard_name)
        
        # 7. Envia WhatsApp (se solicitado)
        if enviar_wh and numeros_wh:
            send_whatsapp_report(screenshot_path, numeros_wh, mensagem)
        
        log("=== AUTOMAÇÃO V2 CONCLUÍDA COM SUCESSO ===")
        
        return {
            "ok": True,
            "message": f"Dashboard {dashboard_config.get('display_name')} gerado com sucesso",
            "screenshot": screenshot_path,
            "dashboard": dashboard_name,
            "periodicidade": periodicidade,
            "whatsapp_enviado": enviar_wh
        }
        
    except Exception as e:
        log(f"ERRO: {e}")
        import traceback
        log(traceback.format_exc())
        return {
            "ok": False,
            "error": str(e),
            "message": "Erro durante execução da automação"
        }

# Compatibilidade com versão antiga
def main():
    """Wrapper para compatibilidade com execução direta"""
    result = run()
    if not result.get("ok"):
        log(f"ERRO: {result.get('error')}")
    return result

if __name__ == "__main__":
    main()
