from nltk.tokenize import sent_tokenize
from ollama_utils import chat
from utils import delay

def verifica_hallucinations(articolo, documenti):
    hallucinated_info = []
    domande_hallucination = []

    frasi_articolo = sent_tokenize(articolo)
    for frase in frasi_articolo:
        print(f"🔍 Frase: {frase}")
        domanda = chat(f"""
## Your Role
You are a question-generation expert. Your task is to create one precise and fact-based question derived from a single sentence.

## Instructions
- Use only the sentence to form your question
- Make it specific and verifiable
- Do not assume context
- Write the question in **Italian**

## Sentence:
{frase}
""")
        print(f"❓ Domanda generata: {domanda}")

        domande_hallucination.append(domanda)

        presente_in_almeno_una_fonte = False
        for nome_file, contenuto in documenti.items():
            risposta_check = chat(f"""
## Your Role
You are an evidence-checking assistant. Your task is to answer a question **using only** the content of the document provided.

## Instructions
- If the document provides a clear answer, write it in **Italian**
- If there is **no answer**, reply with exactly: "NON PRESENTE"
- Do not assume or infer anything not explicitly stated

## Question:
{domanda}

## Document:
{contenuto}
""")
            if not risposta_check:
                print(f"⚠️ Nessuna risposta dalla fonte {nome_file}.")
                continue

            print(f"🗂️ Fonte: {nome_file} → Risposta: {risposta_check.strip()[:60]}")

            if "NON PRESENTE" not in risposta_check.upper():
                presente_in_almeno_una_fonte = True
                break

        if not presente_in_almeno_una_fonte:
            hallucinated_info.append(domanda)

    if hallucinated_info:
        prompt_rimozione = f"""
## Your Role
You are a content auditor. Your task is to remove or rewrite invented statements from an article based on unsupported questions.

## Instructions
- The questions listed below could not be answered by any trusted source
- Identify and revise/remove the corresponding parts of the article
- Maintain logical flow and natural language
- Write the revised article in **Italian**

## Example

Domanda: Quando è stata fondata l’azienda?  
Nessuna fonte ha fornito risposta → frase considerata inventata.

Articolo prima:  
"Oetem è stata fondata nel 1995 a Brescia."  

Articolo corretto:  
(Frase rimossa)

## Unsupported Questions:
{chr(10).join('- ' + d for d in hallucinated_info)}

## Article to revise:
{articolo}

## Output
Return only the final revised article, written in Italian.
"""

        articolo = chat(prompt_rimozione)

    if hallucinated_info:
        print(f"⚠️ {len(hallucinated_info)} domande non supportate da nessuna fonte:")
        for d in hallucinated_info:
            print(f" - {d}")

    return articolo, domande_hallucination, hallucinated_info
