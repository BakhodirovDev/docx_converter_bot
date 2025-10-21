import os
from docx import Document
import json

def ensure_dir(path: str):
    if not os.path.exists(path):
        os.makedirs(path)

def validate_docx(filename: str) -> bool:
    return filename.lower().endswith(".docx")

def convert_docx_to_txt(docx_path: str, txt_path: str):
    doc = Document(docx_path)
    with open(txt_path, "w", encoding="utf-8") as f:
        for para in doc.paragraphs:
            f.write(para.text + "\n")
    return txt_path

def get_text(lang: str, key: str) -> str:
    try:
        # Fayl manzilini to‘liq aniqlash
        base_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_dir, "locale", f"{lang}.json")

        # Agar fayl yo‘q bo‘lsa — default "uz.json" dan o‘qisin
        if not os.path.exists(file_path):
            file_path = os.path.join(base_dir, "locale", "uz.json")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # So‘ralgan kalit bo‘lmasa, kalitni o‘zini qaytaradi
        return data.get(key, key)

    except Exception as e:
        print(f"⚠️ get_text() error: {e}")
        return key