import time
import random

def delay(min_sec=2, max_sec=4, verbose=False):
    sec = random.uniform(min_sec, max_sec)
    if verbose:
        print(f"⏳ Attesa di {sec:.2f} secondi prima della prossima richiesta...")
    time.sleep(sec)