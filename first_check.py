import pandas as pd
import re
from ollama_utils import chat
from utils import delay


def first_check_articolo(articolo, documenti):
    articolo_corrente = articolo
    qa_records = []

    for nome_file, contenuto in documenti.items():
        prompt_qr = f"""## Your Role
You are a critical reviewer and domain expert. Your task is to evaluate whether a generated article faithfully answers questions based on trusted source documents. Your evaluation must be based only on verified facts from the source.

## Instructions

### Step 1: Generate Questions
- Read the source below.
- Generate **at least 5 specific and verifiable** question-answer pairs based only on that source.

Each pair must follow this exact format:
Domanda: ...
Risposta: ...

Use **Italian language**. Do not use titles or numbering. Each pair must be separated by a line break.

### Step 2: Compare Against the Article
You will later be asked to compare the article's answer to the source answer for each question. You must evaluate it as:

✅ CORRETTA — fully consistent with the source  
❌ ERRATA — incorrect or conflicting  
🚫 ASSENTE — the article does not contain an answer  

Keep your judgment strict. Assume the article cannot "improvise" information.

---

## Output format (Q&A generation)
Now generate 5 Italian Q&A pairs based **only** on the following source document. Follow the formatting instructions strictly.

### Source Document:
{contenuto}
"""
        q_res = chat(prompt_qr)
        print("🧾 Output del modello:\n", q_res)  # Debug temporaneo
        blocchi = [line.strip() for line in q_res.splitlines() if line.strip()]

        domanda = risposta = None
        for line in blocchi:
            if re.match(r"(?i)^domanda\s*:", line):
                domanda = line.split("Domanda:", 1)[-1].strip()
            elif line.lower().startswith("risposta"):
                risposta = line.split("Risposta:", 1)[-1].strip()
                if domanda and risposta:
                    risposta_articolo = chat(f"Domanda: {domanda}\n\nRispondi usando solo il contenuto dell'articolo seguente. ATTENZIONE: non fare assunzioni.\n\n{articolo_corrente}")

                    valutazione = chat(f"""
## Your Role
You are an expert evaluator. Your task is to compare two answers to the same question: one from a trusted source and one from an article.

## Instructions

- Assume the source answer is correct.
- If the article's answer **conveys the same meaning**, even through a **faithful citation**, consider it CORRETTA.
- Do not penalize if the article uses **direct quotes** instead of paraphrasing, as long as the meaning is preserved and clear.
- Penalize only if the article introduces **extra information**, **invents content**, or **fails to answer**.

### Step 2: Classify the Article's Answer
Label it as:
✅ CORRETTA — the article's answer is factually accurate and matches the source  
❌ ERRATA — the article includes incorrect or conflicting information  
🚫 ASSENTE — the article does not provide any real answer to the question

### Step 3: Output Format
Return the label on the **first line only**: ✅ / ❌ / 🚫  
Then briefly explain your judgment in **Italian**.

---

## Input
Domanda: {domanda}  
Risposta (Fonte): {risposta}  
Risposta (Articolo): {risposta_articolo}
""")

                    lines = valutazione.split("\n")
                    if not lines or len(lines) < 1:
                        giudizio = "⚠️ ERRORE"
                        spiegazione = "Valutazione malformata"
                    else:
                        giudizio = lines[0].strip()
                        spiegazione = " ".join(lines[1:]).strip()

                    print(f"[{giudizio}] {domanda[:60]}...")

                    qa_records.append({
                        "Domanda": domanda,
                        "Risposta (Fonti)": risposta,
                        "Risposta (Articolo)": risposta_articolo,
                        "Giudizio": giudizio,
                        "Spiegazione": spiegazione
                    })
                    domanda = risposta = None
                    delay()

    df = pd.DataFrame(qa_records)

    if df.empty or "Giudizio" not in df.columns:
        print("⚠️ Nessuna domanda/risposta valida generata nel first_check.")
        return df, pd.DataFrame(), [], articolo_corrente

    df_errate = df[df["Giudizio"].str.contains("❌")]
    df_assenti = df[df["Giudizio"].str.contains("🚫")]

    if df_assenti.empty:
        print("✅ Nessuna informazione assente rilevata per questo check.")
        correzioni_finali = df_errate
        selezionati_info = []
    else:
        print("\n🚫 Informazioni assenti potenzialmente utili:")
        for idx, row in df_assenti.iterrows():
            print(f"[{idx}] ➤ {row['Domanda']} → {row['Risposta (Fonti)']}")

        selezionati = input("👉 Inserisci i numeri delle informazioni da includere (separati da virgola), oppure premi Invio per ignorare: ").strip()
        selezionati_info = []

        if selezionati:
            try:
                indici = [int(i.strip()) for i in selezionati.split(',') if i.strip().isdigit()]
                df_selezionati = df_assenti.loc[indici]
                correzioni_finali = pd.concat([df_errate, df_selezionati])
                selezionati_info = [f"{row['Domanda']} → {row['Risposta (Fonti)']}" for _, row in df_selezionati.iterrows()]
            except Exception as e:
                print(f"⚠️ Errore nella selezione: {e}")
                correzioni_finali = df_errate
        else:
            correzioni_finali = df_errate

    for i, (_, row) in enumerate(correzioni_finali.iterrows()):
        prompt_iter = f"""
## Your Role
You are an editorial assistant and factual corrector. Your task is to revise an article by inserting or correcting a specific fact derived from a trusted source.

## Instructions

### Step 1: Read the article
- Understand its structure and tone
- Do not alter unrelated parts

### Step 2: Integrate the Information
- Insert or correct the information required to answer the question below
- Keep the article coherent and natural
- Do not add extra explanations or new content
- Write the final article entirely in **Italian**

### Input

Domanda: {row.Domanda}  
Risposta corretta (fonte): {row['Risposta (Fonti)']}

### Article to revise:
{articolo_corrente}

### Output
Return only the **updated article** with the integrated or corrected information, written in Italian.
"""
        articolo_corrente = chat(prompt_iter)
        delay()

    return df, correzioni_finali, selezionati_info, articolo_corrente