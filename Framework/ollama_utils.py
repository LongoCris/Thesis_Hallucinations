from ollama import Client
from config import HOST, MODEL, SECONDARY_MODEL, TEMPERATURE
import time
import logging

client = Client(host=HOST)

def chat(prompt, model=None, temperature=None):
    modello = model or MODEL
    temp = temperature if temperature is not None else TEMPERATURE

    try:
        res = client.chat(
            model=modello,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": temp}
        )
        time.sleep(1)
        return res['message']['content'].strip()
    except Exception as e:
        logging.error(f"❌ Errore nella chiamata al modello {modello}: {e}")
        return ""

def chat_secondary(prompt):
    return chat(prompt, model=SECONDARY_MODEL)
