from ollama_utils import chat
from utils import delay

def verifica_hallucinations_con_domande_generate(articolo, documenti):
    prompt_check_hallucinations = f"""
## Your Role
You are a question extraction expert. Your task is to read an article and extract a list of specific, verifiable questions — one per factual claim — based solely on the article content.

## Instructions

- Write only questions that reflect explicit factual statements in the article
- Focus on who/what/when/where/why/how
- Ignore vague, opinion-based or stylistic content
- Write all questions in **Italian**
- Use this format:
Domanda: ...

## Article:
{articolo}
"""

    res_domande_articolo = chat(prompt_check_hallucinations)
    print("❓ Domande generate dall'articolo:")
    domande_hallucination = []
    for line in res_domande_articolo.splitlines():
        if "Domanda:" in line:
            domanda = line.split("Domanda:", 1)[-1].strip()
            print(" -", domanda)
            domande_hallucination.append(domanda)


    hallucinated_info = []
    for domanda in domande_hallucination:
        presente_in_almeno_una_fonte = False
        for nome_file, contenuto in documenti.items():
            prompt_check_fonte = f"""
## Your Role
You are a source validator. Your task is to answer the question below using only the content of this document.

## Instructions

- If the answer is found in the document, write it in **Italian**
- If there is no explicit answer, reply exactly with: "NON PRESENTE"
- Do not invent, infer or assume

## Question:
{domanda}

## Document:
{contenuto}
"""

            risposta_text = chat(prompt_check_fonte)
            if not risposta_text:
                print(f"⚠️ Nessuna risposta dalla fonte {nome_file}")
                continue

            print(f"🗂️ Fonte: {nome_file} → Risposta: {risposta_text.strip()[:60]}")

            if "NON PRESENTE" not in risposta_text.upper():
                presente_in_almeno_una_fonte = True
                break
            delay()
        if not presente_in_almeno_una_fonte:
            hallucinated_info.append(domanda)

    if hallucinated_info:
        prompt_rimozione = f"""
## Your Role
You are an editorial cleaner. Your task is to remove or rewrite hallucinated statements from the article below.

## Instructions

- The following questions could not be answered by any source
- Remove or rephrase the corresponding factual claims
- Ensure the final article is fluent, coherent and **written in Italian**

## Example

Unsupported Question: Qual è il numero di dipendenti dell’azienda?

Articolo prima:  
"L'azienda conta circa 800 dipendenti."

Articolo corretto:  
(Frase rimossa o riformulata per evitare il numero non verificato)

## Unsupported Questions:
{chr(10).join('- ' + d for d in hallucinated_info)}

## Original Article:
{articolo}

## Output
Return only the final revised article.
"""
        articolo = chat(prompt_rimozione)

    if hallucinated_info:
        print(f"⚠️ {len(hallucinated_info)} domande non supportate da nessuna fonte:")
        for d in hallucinated_info:
            print(f" - {d}")

    return articolo, domande_hallucination, hallucinated_info


