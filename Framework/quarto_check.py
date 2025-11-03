from nltk.tokenize import sent_tokenize
from ollama_utils import chat, chat_secondary
from utils import delay
import os

def _is_yes(text: str) -> bool:
    t = (text or "").strip().casefold()
    t = t.lstrip(":-•*>#\"' \t")  # leva bullet/punteggiatura iniziale
    return t.startswith(("sì", "si", "yes"))

def crea_prompt_rimozione(frase, articolo):
    return f"""
## Your Role
You are an editorial reviser performing a factual cleanup. Your task is to remove a sentence from the article because it is not supported by any trusted source.

## Instructions

- Remove the sentence listed below
- Keep the article coherent and fluent
- Write in **Italian**
- Do not touch unrelated parts

## Sentence to remove:
"{frase}"

## Article:
{articolo}

## Output:
Return the article with the sentence removed.
"""

def quarto_check_articolo(articolo, documenti):
    risultati_tracciamento = []
    frasi = sent_tokenize(articolo)
    nuovo_articolo = articolo

    for frase in frasi:
        print(f"\n🔍 Analizzo frase: {frase}")

        prompt = f"""
## Your Role
You are a verification engine. Your task is to determine whether a given sentence from an article is supported by any of the documents below.

## Instructions
- For each source, answer in exactly this 3-line format:
  Fonte: <filename>
  Presente: Sì/No
  Citazione: <estratto testuale letterale, max 50 parole, oppure "N/D">

- Rules:
  • Put "Presente: Sì" only if the central meaning of the sentence is explicit in the text.
  • If you cannot provide a literal quote (≤ 50 words), use "Presente: No" and "Citazione: N/D".
  • Do not write paraphrases or summaries in "Citazione".

## Sentence:
"{frase}"

## Sources:
"""
        for nome_file, contenuto in documenti.items():
            prompt += f"\nFonte: {nome_file}\n{contenuto}\n"

        prompt += "\n## Output\nGive one block per source in the format above."

        risposta = chat(prompt)
        delay()

        # conserva la risposta grezza per l'export
        verifica_raw = risposta if risposta else "N/D"


        if not risposta or "Fonte:" not in risposta:
            print("⚠️ Formato non riconosciuto: procedo con rimozione meccanica.")
            # rimozione meccanica semplice
            if frase in nuovo_articolo:
                nuovo_articolo = nuovo_articolo.replace(frase, "").replace("  ", " ").strip()
            else:
                # fallback con LLM
                prompt_rimozione = crea_prompt_rimozione(frase, nuovo_articolo)
                nuovo_articolo = chat(prompt_rimozione)
                delay()

            risultati_tracciamento.append({
                "Frase": frase,
                "Verifica": verifica_raw,
                "Esito finale": "Rimossa"
            })
            continue


        # === Estrazione blocchi per-sorgente ===
        blocchi = risposta.split("Fonte:")[1:]
        for blocco in blocchi:
            print("🗂️ Blocco valutazione:\n", blocco.strip()[:200])

        # normalizza 'Presente' e raccogli citazioni
        citazioni_supportanti = []
        presenze_si = 0
        blocchi_supportanti = []

        for blocco in blocchi:
            lines = [l.strip() for l in blocco.strip().split("\n") if l.strip()]
            presente_line = next((l for l in lines if l.lower().startswith("presente:")), "")
            presente_val = presente_line.split(":",1)[1].strip() if ":" in presente_line else ""
            if _is_yes(presente_val):  # ✅ più robusto
                presenze_si += 1
                blocchi_supportanti.append(blocco)
                cit_line = next((l for l in lines if l.lower().startswith("citazione:")), "")
                cit = cit_line.split(":",1)[1].strip() if ":" in cit_line else "N/D"
                if cit and cit != "N/D":
                    citazioni_supportanti.append(cit)

        # if we have at least one "Presente: Sì" but zero quotes -> per-source retry with full source text
        if presenze_si > 0 and not citazioni_supportanti:
            for nome_file, contenuto in documenti.items():
                # only retry on sources that said "Sì" but lacked a quote
                if any(nome_file in b for b in blocchi_supportanti):
                    retry_prompt = f"""
## Your Role
Sei un estrattore di evidenze. Dal documento seguente, estrai una sola citazione **letterale**
(max 45 parole) che supporti la frase. Se non trovi un supporto chiaro, rispondi esattamente "N/D".

## Frase
{frase}

## Documento
{contenuto}

## Output
Solo la citazione (senza virgolette) oppure "N/D".
"""

                    estratto = (chat(retry_prompt) or "").strip().strip(' "\'')
                    delay()
                    if estratto and estratto.upper() != "N/D" and len(estratto.split()) >= 3:
                        # optional hard cap to 50 words
                        words = estratto.split()
                        if len(words) > 50:
                            estratto = " ".join(words[:50])
                        citazioni_supportanti.append(estratto)
                        break  # one good quote is enough





        # Dedup dopo eventuale retry
        citazioni_supportanti = list(dict.fromkeys(citazioni_supportanti))
        # Hard cap 50 parole per sicurezza
        citazioni_supportanti = [" ".join(c.split()[:50]) for c in citazioni_supportanti]


        # Estrai termini chiave molto semplici (puoi tenerlo inline o spostarlo in helper)
        def _terms(frase: str):
            import re
            stop = {"il","lo","la","i","gli","le","un","una","di","del","della","dei","degli","delle","e","o","a","da","in","con","su","per","tra","fra","che"}
            toks = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ’']+", frase)
            caps = [t for t in toks if t[:1].isupper() and len(t) > 2]
            body = [t.lower() for t in toks if len(t) > 3 and t.lower() not in stop]
            return list(dict.fromkeys(caps + body[:5]))  # nomi propri + pochi concetti

        chiave = _terms(frase)

        # Regola DECISIVA:
        # NON accettare più "presenze_si > 0" da solo.
        frase_valida = False

        # 1) Serve almeno UNA citazione breve per andare avanti
        if citazioni_supportanti:
            for cit in citazioni_supportanti:
                # 1a) Fast-path: la citazione contiene tutti i termini chiave → accetta
                if all(k.lower() in cit.lower() for k in chiave if k and len(k) > 2):
                    frase_valida = True
                    break

                # 1b) Altrimenti chiedi al secondario se la citazione copre il nucleo
                prompt_validazione = f"""
## Your Role
You are a strict fact-checker. Decide if the quote **fully** supports the sentence.

## Decision rule (ALL must be explicit in the quote):
- People/entities in the sentence
- Main action / claim
- Object/concept
- Any numbers, dates, or places mentioned in the sentence

If ANY of these is missing in the quote, reply "No".

Sentence: "{frase}"

Quote:
{cit}

## Output
Write exactly "Sì" or "No", then one short line of justification in Italian.
"""
                conferma = chat_secondary(prompt_validazione)
                print("🔎 Conferma secondario:", (conferma or "")[:120])
                delay()
                if (conferma or "").strip().casefold().startswith(("sì","si","yes","true","ok","supported","supportato","confermato","affermativo")):
                    frase_valida = True
                    break


        # ✅ 2) Se ancora non è valida → rimuovi
        if not frase_valida:
            if frase in nuovo_articolo:
                nuovo_articolo = nuovo_articolo.replace(frase, "").strip()
                nuovo_articolo = " ".join(nuovo_articolo.split())  # pulizia spazi
            else:
                prompt_rimozione = crea_prompt_rimozione(frase, nuovo_articolo)
                print(f"❌ Rimuovo frase via LLM: {frase}")
                nuovo_articolo = chat(prompt_rimozione)
                delay()




        esito_finale = "Mantenuta" if frase_valida else "Rimossa"

        # salva i blocchi completi (per compatibilità con l'export)
        verifica_finale = verifica_raw  # contiene i blocchi "Fonte/Presente/Citazione"

        risultati_tracciamento.append({
            "Frase": frase,
            "Verifica": verifica_finale,
            "Esito finale": esito_finale
        })


    return nuovo_articolo, risultati_tracciamento
