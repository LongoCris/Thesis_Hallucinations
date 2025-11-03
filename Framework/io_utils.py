import os
import json
from pathlib import Path

def carica_documenti(cartella, nomi_file):
    documenti = {}
    for nome_file in nomi_file:
        path = Path(cartella) / nome_file
        try:
            with path.open('r', encoding='utf-8') as f:
                if nome_file.lower().endswith(".json"):
                    raw_data = json.load(f)
                    contenuto_formattato = json.dumps(raw_data, indent=2, ensure_ascii=False)
                    documenti[nome_file] = contenuto_formattato
                    print(f"📄 Caricato (JSON): {nome_file}")
                else:
                    documenti[nome_file] = f.read()
                    print(f"📄 Caricato (TXT): {nome_file}")
        except Exception as e:
            print(f"❌ Errore nel caricamento di {nome_file}: {e}")
    return documenti

def carica_articolo(path):
    return Path(path).read_text(encoding="utf-8")

def salva_articolo_txt(path, articolo):
    path = Path(path)
    path.write_text(articolo, encoding="utf-8")
    print(f"💾 Articolo salvato in: {path}")
