# removal_metrics.py
from nltk.tokenize import sent_tokenize
from difflib import SequenceMatcher
import math
import re

def _norm(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s

def _sim(a: str, b: str) -> float:
    # Similarità robusta: media di SequenceMatcher e Jaccard su token
    a_n, b_n = _norm(a), _norm(b)
    sm = SequenceMatcher(None, a_n, b_n).ratio()
    a_set, b_set = set(a_n.split()), set(b_n.split())
    jac = len(a_set & b_set) / (len(a_set | b_set) + 1e-9)
    return 0.5 * (sm + jac)

def map_questions_to_spans(article_before: str,
                           questions: list[str],
                           top_k: int = 2,
                           min_sim: float = 0.40):
    """
    Mappa ogni domanda alle frasi candidate dell'articolo pre-Third check (articolo_qa).
    Ritorna: dict { domanda: [ (idx_frase, frase, score), ... ] } (sorted per score)
    """
    sentences = sent_tokenize(article_before)
    out = {}
    for q in questions or []:
        scores = []
        for i, s in enumerate(sentences):
            score = _sim(q, s)
            if score >= min_sim:
                scores.append((i, s, score))
        scores.sort(key=lambda x: x[2], reverse=True)
        out[q] = scores[:top_k]
    return out, sentences

def span_removed_or_rewritten(candidate_spans: list[tuple],
                              article_after: str,
                              keep_threshold: float = 0.60,
                              rewrite_threshold: float = 0.45):
    """
    Valuta se lo span candidato è:
      - RIMOSSO   se nessuna frase nel finale ha sim >= rewrite_threshold
      - RISCRITTO se max-sim finale < keep_threshold ma >= rewrite_threshold
      - TENUTO    se max-sim finale >= keep_threshold
    Ritorna uno tra {"removed", "rewritten", "kept"} e il massimo score.
    """
    after_sents = sent_tokenize(article_after)
    max_sim = 0.0
    for _, text, _ in candidate_spans:
        for s2 in after_sents:
            max_sim = max(max_sim, _sim(text, s2))
    if max_sim < rewrite_threshold:
        return "removed", max_sim
    if max_sim < keep_threshold:
        return "rewritten", max_sim
    return "kept", max_sim

def compute_removal_success_rate(unsupported_questions: list[str],
                                 article_before: str,
                                 article_after: str,
                                 top_k: int = 2,
                                 min_sim: float = 0.40,
                                 keep_threshold: float = 0.60,
                                 rewrite_threshold: float = 0.45):
    """
    Calcola la Removal Success Rate vera e produce un dettaglio per domanda:
      - "removed" / "rewritten" / "kept"
      - max_sim finale
      - spans candidati
    """
    mapping, before_sents = map_questions_to_spans(article_before, unsupported_questions,
                                                   top_k=top_k, min_sim=min_sim)
    details = []
    removed_or_rewritten = 0

    for q in unsupported_questions or []:
        spans = mapping.get(q, [])
        if not spans:
            # Se non troviamo neanche un candidato: consideriamola già “rimossa”
            details.append({"question": q, "status": "removed", "max_sim": 0.0, "spans": []})
            removed_or_rewritten += 1
            continue

        status, m = span_removed_or_rewritten(spans, article_after,
                                              keep_threshold=keep_threshold,
                                              rewrite_threshold=rewrite_threshold)
        if status in ("removed", "rewritten"):
            removed_or_rewritten += 1

        details.append({
            "question": q,
            "status": status,
            "max_sim": round(m, 4),
            "spans": [{"idx": i, "text": t, "score": round(sc, 4)} for (i, t, sc) in spans]
        })

    total = len(unsupported_questions or [])
    rsr = (removed_or_rewritten / total) if total else 0.0
    return rsr, details
