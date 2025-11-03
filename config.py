import os
from pathlib import Path
from datetime import datetime

# === Configurazioni modello ===
TEMPERATURE = 0
HOST = "http://localhost:11434"
MODEL = "gemma2:9b"
SECONDARY_MODEL = "llama3.1:8b"

# === Percorsi e input ===
CARTELLA_DOCUMENTI = Path(r"C:\Your\Document\Path")
FILE_ARTICOLO = CARTELLA_DOCUMENTI / "DRAFT_H.txt"
FILE_SELEZIONATI = ["SOURCE_1.txt", "SOURCE_2.txt"]
NOME_ARTICOLO = "DRAFT_H"

# Verifica esistenza file
for nome_file in FILE_SELEZIONATI + [FILE_ARTICOLO.name]:
    path = CARTELLA_DOCUMENTI / nome_file
    if not path.exists():
        raise FileNotFoundError(f"❌ File mancante: {path}")

# === Output dinamico ===
timestamp = datetime.now().strftime("resultati_test_%Y-%m-%d_%H-%M-%S")
OUTPUT_DIR = CARTELLA_DOCUMENTI / timestamp
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

EXCEL_PATH = OUTPUT_DIR / f"{NOME_ARTICOLO}_rep_2.xlsx"

# === Variabili esportabili se serve ===
__all__ = [
    "TEMPERATURE", "HOST", "MODEL", "SECONDARY_MODEL",
    "CARTELLA_DOCUMENTI", "FILE_ARTICOLO", "FILE_SELEZIONATI",
    "OUTPUT_DIR", "EXCEL_PATH", "timestamp", "NOME_ARTICOLO"
]
