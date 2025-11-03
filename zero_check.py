from ollama_utils import chat
from config import OUTPUT_DIR
from nltk.tokenize import sent_tokenize
from utils import delay
import os

def correggi_articolo_con_fonti(articolo, documenti):
    # === Caso 1: una sola fonte ===
    if len(documenti) == 1:
        articolo_corretto = articolo

        for nome_file, contenuto in documenti.items():
            print(f"\n📝 Correzione con la fonte: {nome_file}")

            prompt = f"""
## Your Role
You are a professional fact-checker and editorial corrector. Your task is to review a generated article against a trusted source document. You must revise or remove any hallucinated, inaccurate, or misleading content not supported by the source. Maintain a clear, natural tone and write in fluent **Italian**.

## Instructions

### Step 1: Analyze the Source
- Treat the source document as the absolute truth
- Identify: named entities, dates, numbers, events, outcomes, causal relationships

### Step 2: Review the Article
- Compare article claims to the source
- Detect:
  - Contradictions
  - Invented information (hallucinations)
  - Misinterpretations

### Step 3: Correct the Article
- Remove or rewrite problematic sentences
- Keep logical flow, coherence, and tone
- Do **not** add new content

### Output
Return only the fully revised article text in **Italian**, without comments or explanations.

## Few-shot Examples

### Example 1
**Source**: "Oetem è stata fondata nel 1983 a Torino."  
**Article**: "Oetem è nata nel 1985 a Milano."  
**Correction**: "Oetem è stata fondata nel 1983 a Torino."

### Example 2
**Source**: "Nel 2022, l’azienda ha registrato un utile netto di 12 milioni di euro."  
**Article**: "Nel 2022 ha avuto gravi perdite."  
**Correction**: "Nel 2022, l’azienda ha registrato un utile netto di 12 milioni di euro."

---

## Task
Now apply the same process to the article below. Use only the following source as reference.  
Write the corrected article in **Italian** and return only the final text.

### Source Document:
{contenuto}

### Generated Article:
{articolo_corretto}
"""

            nuovo_articolo = chat(prompt)

            if nuovo_articolo != articolo_corretto:
                print(f"✅ Modifiche applicate da: {nome_file}")
                intermedio_path = os.path.join(OUTPUT_DIR, f"articolo_corretto_da_{nome_file}.txt")
                with open(intermedio_path, "w", encoding="utf-8") as f:
                    f.write(nuovo_articolo)
            else:
                print(f"⚠️ Nessuna modifica rilevata da: {nome_file}")

            articolo_corretto = nuovo_articolo

        return articolo_corretto

    # === Caso 2: più fonti ===
    else:
        print("\n🔎 Zero-check avanzato con più fonti: validazione frase per frase...")
        frasi = sent_tokenize(articolo)
        nuovo_articolo = articolo

        for frase in frasi:
            print(f"\n🔍 Analizzo frase: {frase}")
            supportata = False

            for nome_file, contenuto in documenti.items():
                prompt = f"""
## Your Role
You are a validator. Check if the following sentence is supported by the document below.

## Instructions
- If the sentence is clearly supported, reply: "Sì"
- If not, reply: "No"
- Answer in Italian, just one word: Sì / No

## Sentence:
{frase}

## Source:
{contenuto}
"""
                risposta = chat(prompt).strip().lower()
                delay()
                if risposta.startswith("sì"):
                    print(f"✅ Supportata da: {nome_file}")
                    supportata = True
                    break
                else:
                    print(f"❌ Non supportata da: {nome_file}")

            if not supportata:
                print(f"🚫 Frase rimossa: {frase}")
                prompt_rimozione = f"""
## Your Role
You are an editorial reviser. Remove the sentence below from the article.

## Sentence to remove:
"{frase}"

## Article:
{nuovo_articolo}

## Output:
Return the article with the sentence removed.
"""
                nuovo_articolo = chat(prompt_rimozione)
                delay()
                
        log_path = os.path.join(OUTPUT_DIR, "frasi_rimosse_zero_check.txt")
        with open(log_path, "w", encoding="utf-8") as f:
            for frase in frasi:
                if frase not in nuovo_articolo:
                    f.write(frase.strip() + "\n\n")
        print(f"📄 Frasi rimosse salvate in: {log_path}")

        return nuovo_articolo
