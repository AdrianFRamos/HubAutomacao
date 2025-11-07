import os, time, io, webbrowser
from PIL import Image
import pyautogui
import win32clipboard
import win32con

def _image_to_clipboard(image_path):
    if not os.path.exists(image_path):
        raise FileNotFoundError(image_path)
    img = Image.open(image_path)
    output = io.BytesIO()
    img.convert("RGB").save(output, "BMP")
    data = output.getvalue()[14:] 
    output.close()

    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_DIB, data)
    finally:
        win32clipboard.CloseClipboard()

def send_whatsapp_via_clipboard(phone, image_path, caption=None,wait_for_ready=8, focus_click_coord=None,logger=print):
    try:
        if not os.path.exists(image_path):
            logger(f"[whcb] Arquivo não encontrado: {image_path}")
            return False
        url = f"https://web.whatsapp.com/send?phone={phone}&text="
        webbrowser.open_new_tab(url)
        logger(f"[whcb] Abrindo {url}")
        waited = 0.0
        interval = 0.5
        time.sleep(1.0)
        while waited < wait_for_ready:
            time.sleep(interval)
            waited += interval
        logger(f"[whcb] Esperou {waited:.1f}s para carregar a página")
        try:
            _image_to_clipboard(image_path)
        except Exception as e:
            logger(f"[whcb] Falha copiar imagem para clipboard: {e}")
            return False
        time.sleep(0.25)
        if focus_click_coord:
            try:
                pyautogui.click(focus_click_coord[0], focus_click_coord[1])
                time.sleep(0.15)
            except Exception as e:
                logger(f"[whcb] Falha click focus coord: {e}")
        else:
            w, h = pyautogui.size()
            pyautogui.click(w // 2, h - 120)
            time.sleep(0.12)
        try:
            pyautogui.hotkey('ctrl', 'v')
        except Exception as e:
            logger(f"[whcb] Falha ao executar Ctrl+V: {e}")
            return False
        if caption:
            time.sleep(0.9)
            try:
                pyautogui.typewrite(str(caption), interval=0.02)
            except Exception:
                pass
        time.sleep(1.2)
        try:
            pyautogui.press('enter')
        except Exception as e:
            logger(f"[whcb] Falha ao pressionar Enter: {e}")
            return False
        logger("[whcb] Enter pressionado - tentativa de envio concluída.")
        return True
    except Exception as e:
        logger(f"[whcb] Erro inesperado: {e}")
        return False
