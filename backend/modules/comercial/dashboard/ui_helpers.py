import os, time, cv2, numpy as np
import pyautogui
from datetime import datetime

pyautogui.FAILSAFE = True

def _screenshot_bgr():
    scr = pyautogui.screenshot()
    arr = np.array(scr)
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

def multiscale_locate(template_path, screen=None, scales=None, method=cv2.TM_CCOEFF_NORMED):
    tpl = cv2.imread(template_path, cv2.IMREAD_UNCHANGED)
    if tpl is None:
        return None
    if screen is None:
        screen = _screenshot_bgr()
    if scales is None:
        scales = np.linspace(0.8, 1.25, 12)
    h0, w0 = tpl.shape[:2]
    best = {"score": -1.0, "loc": None, "w": 0, "h": 0, "scale": None}
    for s in scales:
        nw = int(w0 * s)
        nh = int(h0 * s)
        if nw < 8 or nh < 8 or nw > screen.shape[1] or nh > screen.shape[0]:
            continue
        try:
            tpl_r = cv2.resize(tpl, (nw, nh), interpolation=cv2.INTER_AREA)
            res = cv2.matchTemplate(screen, tpl_r, method)
            _, maxv, _, maxloc = cv2.minMaxLoc(res)
        except Exception:
            continue
        if maxv > best["score"]:
            best.update({"score": float(maxv), "loc": maxloc, "w": nw, "h": nh, "scale": float(s)})
    return best

def locate_image_on_screen(template_path, confidence=0.72, timeout=15, interval=0.6):
    start = time.time()
    while time.time() - start < timeout:
        screen = _screenshot_bgr()
        best = multiscale_locate(template_path, screen=screen)
        if best and best["score"] >= confidence:
            x,y = best["loc"]
            return (int(x + best["w"]/2), int(y + best["h"]/2))
        time.sleep(interval)
    return None

def click_image(template_path, confidence=0.72, timeout=12, interval=0.6, clicks=1, button='left'):
    pos = locate_image_on_screen(template_path, confidence=confidence, timeout=timeout, interval=interval)
    if not pos:
        return False
    x,y = pos
    pyautogui.moveTo(x, y, duration=0.25)
    pyautogui.click(clicks=clicks, button=button)
    time.sleep(0.2)
    return True

def focus_window_by_title(title, timeout=8):
    try:
        import pygetwindow as gw
    except Exception:
        return True
    start = time.time()
    while time.time() - start < timeout:
        wins = gw.getWindowsWithTitle(title)
        if wins:
            w = wins[0]
            try:
                w.activate()
            except Exception:
                try:
                    w.minimize(); time.sleep(0.15); w.restore()
                    w.activate()
                except Exception:
                    pass
            return True
        time.sleep(0.5)
    return False

def take_region_screenshot(region, dest_folder, name_prefix="relatorio"):
    os.makedirs(dest_folder, exist_ok=True)
    x,y,w,h = region
    img = pyautogui.screenshot(region=(x,y,w,h))
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path = os.path.join(dest_folder, f"{name_prefix}_{ts}.png")
    img.save(path)
    return path

def save_full_screenshot(dest_folder, name_prefix="full"):
    os.makedirs(dest_folder, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path = os.path.join(dest_folder, f"{name_prefix}_{ts}.png")
    pyautogui.screenshot(path)
    return path
