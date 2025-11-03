from config import CARTELLA_DOCUMENTI, FILE_SELEZIONATI, FILE_ARTICOLO, EXCEL_PATH, OUTPUT_DIR
from io_utils import carica_documenti, carica_articolo, salva_articolo_txt
from zero_check import correggi_articolo_con_fonti
from first_check import first_check_articolo
from qa_module import genera_qa_valuta_e_correggi
from hallucination_checker import verifica_hallucinations
from hallucination_check_alt import verifica_hallucinations_con_domande_generate
from quarto_check import quarto_check_articolo
from excel_exporter import esporta_excel
from csv_exporter import esporta_csv_personalizzato
from change_tracker import traccia_modifiche_excel, build_tracciamento_catene
from metrics import compute_metrics, save_metrics_csv
from removal_metrics import compute_removal_success_rate

import os


def main():
    print("📥 Caricamento documenti...")
    documenti = carica_documenti(CARTELLA_DOCUMENTI, FILE_SELEZIONATI)
    articolo_iniziale = carica_articolo(FILE_ARTICOLO)

    if not articolo_iniziale.strip():
        print("❌ Articolo vuoto. Interrompo l'esecuzione.")
        return
    if not documenti:
        print("❌ Nessuna fonte caricata. Interrompo l'esecuzione.")
        return

    versioni_articolo = [articolo_iniziale]

    print("🔍 STEP 1 — Zero-check iniziale in corso...")
    articolo_zero = correggi_articolo_con_fonti(articolo_iniziale, documenti)
    versioni_articolo.append(articolo_zero)

    print("🔎 STEP 2 — First check concettuale (domande/risposte su concetti principali)...")
    df_first, correzioni_first, selezionati_info_first, articolo_first = first_check_articolo(articolo_zero, documenti)
    versioni_articolo.append(articolo_first)

    print("🧪 STEP 3 — Second check Generazione QA frase per frase e correzione iterativa...")
    df_qa, correzioni_df, selezionati_info, articolo_qa = genera_qa_valuta_e_correggi(articolo_first, documenti)
    versioni_articolo.append(articolo_qa)

    print("🧠 STEP 4 — Third check Verifica di possibili hallucinations...")
    while True:
        scelta = input("👉 Vuoi usare il metodo CLASSICO frase per frase (1) o OTTIMIZZATO per affermazioni (2)? ").strip()
        if scelta in ("1", "2"):
            break
        print("❌ Inserisci solo '1' o '2'.")

    if scelta == "2":
        articolo_hallucinated, domande_verificate, unsupported_questions = \
            verifica_hallucinations_con_domande_generate(articolo_qa, documenti)
    else:
        articolo_hallucinated, domande_verificate, unsupported_questions = \
            verifica_hallucinations(articolo_qa, documenti)
    versioni_articolo.append(articolo_hallucinated)

    print("ThirdCheck: #questions =", len(domande_verificate),
      " #unsupported =", len(unsupported_questions or []))

    print("📌 STEP 5 — Fourth check Verifica finale della tracciabilità delle fonti per ogni frase...")
    articolo_finale, risultati_tracciamento = quarto_check_articolo(articolo_hallucinated, documenti)

    # Calcolo Removal Success Rate: mappiamo le unsupported su articolo_qa e confrontiamo col finale
    rsr, rsr_details = compute_removal_success_rate(
        unsupported_questions=unsupported_questions,
        article_before=articolo_qa,     # PRIMA del Third check
        article_after=articolo_finale,  # DOPO tutta la pipeline
        top_k=2,
        min_sim=0.40,
        keep_threshold=0.60,
        rewrite_threshold=0.45
    )
    print(f"🧹 Removal Success Rate: {rsr:.2%}")

    versioni_articolo.append(articolo_finale)

    print("📤 STEP 6 — Esportazione Excel e CSV...")
    esporta_excel(
        articolo_finale,
        articolo_zero,
        df_qa,
        correzioni_df,
        selezionati_info,
        domande_verificate,
        documenti,
        df_first,
        correzioni_first,
        selezionati_info_first,
        metodo_hallucination="ottimizzato" if scelta == "2" else "classico",
        tracciamento_fonti=risultati_tracciamento
    )

    print("📤 Esportazione CSV personalizzato...")
    csv_path = os.path.join(OUTPUT_DIR, "T_Art_report_finale.csv")
    esporta_csv_personalizzato(csv_path, articolo_iniziale, articolo_finale, risultati_tracciamento)

    metrics = compute_metrics(
        articolo_iniziale, articolo_finale,
        df_first, df_qa,
        selezionati_info_first, selezionati_info,
        risultati_tracciamento,
        domande_verificate,
        unsupported_questions=unsupported_questions,
        removal_success_rate=rsr
    )
    
    save_metrics_csv(metrics, os.path.join(OUTPUT_DIR, "metrics.csv"))

    print("📥 STEP 7 — Tracking dettagliato delle modifiche...")
    catena = build_tracciamento_catene(versioni_articolo)
    path_xlsx_tracker = os.path.join(OUTPUT_DIR, "tracciamento_modifiche.xlsx")
    traccia_modifiche_excel(articolo_iniziale, articolo_finale, catena, path_xlsx_tracker)

    txt_path = os.path.join(OUTPUT_DIR, "articolo_finale.txt")
    salva_articolo_txt(txt_path, articolo_finale)

    print(f"\n✅ Articolo finale salvato in: {txt_path}")
    print(f"📊 Report Excel salvato in: {EXCEL_PATH}")
    print(f"📑 Tracciamento modifiche salvato in: {path_xlsx_tracker}")
    print(f"📄 Report CSV salvato in: {csv_path}")
    print("📈 METRICS:", metrics)



if __name__ == "__main__":
    main()
