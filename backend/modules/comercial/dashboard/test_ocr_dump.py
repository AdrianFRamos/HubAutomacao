import pyautogui
import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

print("Tire um screenshot da tela atual (Planilhas) e lendo com OCR...")

screenshot = pyautogui.screenshot()
img = screenshot.convert("RGB")

text = pytesseract.image_to_string(img, lang="por")
print("=== TEXTO OCR LIDO ===")
print(text)
print("=== FIM ===")
