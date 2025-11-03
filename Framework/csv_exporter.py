import csv
import os
from nltk.tokenize import sent_tokenize

def esporta_csv_personalizzato(path_output_csv, articolo_iniziale, articolo_finale, risultati_tracciamento):
    os.makedirs(os.path.dirname(path_output_csv), exist_ok=True)

    with open(path_output_csv, mode='w', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file)

        writer.writerow(["Tipo", "Frase/Articolo", "Fonte trovata", "Citazione", "Supporto"])

        # Articolo iniziale (suddiviso in frasi)
        writer.writerow(["--- Articolo Iniziale ---", "", "", "", ""])
        for frase in sent_tokenize(articolo_iniziale):
            writer.writerow(["Articolo Iniziale", frase, "", "", ""])

        # Articolo finale (suddiviso in frasi)
        writer.writerow(["--- Articolo Finale ---", "", "", "", ""])
        for frase in sent_tokenize(articolo_finale):
            writer.writerow(["Articolo Finale", frase, "", "", ""])

        # Quarto check - Tracciabilità
        writer.writerow(["--- Tracciabilità delle Fonti (Quarto Check) ---", "", "", "", ""])
        for item in risultati_tracciamento:
            frase = item.get("Frase", "")
            verifica = item.get("Verifica", "")
            blocchi = verifica.split("Fonte:")[1:]  # skip the first empty split
            supportata = False

            for blocco in blocchi:
                righe = [r.strip() for r in blocco.strip().splitlines() if r.strip()]
                if len(righe) >= 3:
                    nome_fonte = righe[0]
                    presente = righe[1].split(":", 1)[-1].strip()
                    citazione = righe[2].split(":", 1)[-1].strip()

                    if presente.lower() == "sì":
                        writer.writerow(["Frase", frase, nome_fonte, citazione, "Supportata"])
                        supportata = True
                        break  # fermati alla prima fonte valida

            if not supportata:
                writer.writerow(["Frase (NON SUPPORTATA)", frase, "N/D", "N/D", "Non supportata"])

    print(f"✅ CSV esportato in: {path_output_csv}")
