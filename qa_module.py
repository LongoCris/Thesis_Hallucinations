import pandas as pd
from nltk.tokenize import sent_tokenize
from ollama_utils import chat
from utils import delay
import os


def genera_qa_valuta_e_correggi(articolo, documenti):
    articolo_corrente = articolo
    qa_records = []

    # Filtra i documenti, escludendo i file .json
    documenti_filtrati = {nome: contenuto for nome, contenuto in documenti.items() if not nome.lower().endswith('.json')}

    if not documenti_filtrati:
        print("⚠️ Tutti i documenti sono file JSON. Salto la fase di QA.")
        return pd.DataFrame(), pd.DataFrame(), [], articolo_corrente

    for nome_file, contenuto in documenti_filtrati.items():
        frasi_documento = sent_tokenize(contenuto)
        for frase in frasi_documento:
            domanda = chat(f"""
## Your Role
You are a question generation expert. Your task is to write a specific, verifiable question that matches the meaning of a single sentence.

## Instructions
- Write one question that tests the factual content of the sentence
- The question must be answerable using only the sentence
- Use **Italian** for the question
- Keep it short and precise

## Sentence:
{frase}
""")

            risposta = chat(f"""
## Your Role
You are a factual assistant. Your task is to answer the question using only the sentence provided.

## Instructions
- Do not assume or infer beyond what is stated
- Answer in **Italian**
- Be concise

## Sentence:
{frase}

## Question:
{domanda}
""")

            risposta_articolo = chat(f"""
## Your Role
You are an assistant extracting answers from a draft article.

## Instructions
- Answer the question using only the content of the article
- If the answer is not present, say clearly that it is missing
- Do not assume or invent
- Answer in **Italian**

## Question:
{domanda}

## Article:
{articolo_corrente}
""")


            valutazione = chat(f"""
## Your Role
You are an expert evaluator. Your task is to compare two answers to the same question: one from a trusted source and one from an article.

## Instructions

### Step 1: Compare Carefully
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

## Task
Question: {domanda}  
Source Answer: {risposta}  
Article Answer: {risposta_articolo}
""")

            delay()

            valutazione_lines = valutazione.strip().split("\n")
            if not valutazione_lines or len(valutazione_lines) < 1:
                giudizio = "⚠️ ERRORE"
                spiegazione = "Valutazione malformata"
            else:
                giudizio = valutazione_lines[0].strip()
                print(f"[{giudizio}] {domanda[:60]}...")
                spiegazione = " ".join(valutazione_lines[1:]).strip() if len(valutazione_lines) > 1 else "(nessuna spiegazione fornita)"


            qa_records.append({
                "Domanda": domanda.strip(),
                "Risposta (Fonti)": risposta.strip(),
                "Risposta (Articolo)": risposta_articolo.strip(),
                "Giudizio": giudizio,
                "Spiegazione": spiegazione
            })



    df = pd.DataFrame(qa_records)
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

## Example

Domanda: Dove si trova la sede centrale dell’azienda?  
Risposta corretta: A Torino.  

Articolo prima:  
"L'azienda ha sede a Milano ed è specializzata nella produzione di valvole."  

Articolo corretto:  
"L'azienda ha sede a Torino ed è specializzata nella produzione di valvole."

### Input

Domanda: {row['Domanda']}
Risposta corretta (fonte): {row['Risposta (Fonti)']}

### Article to revise:
{articolo_corrente}

### Output
Return only the **updated article** with the integrated or corrected information, written in Italian.
"""
        articolo_corrente = chat(prompt_iter)
        delay()

    return df, correzioni_finali, selezionati_info, articolo_corrente
