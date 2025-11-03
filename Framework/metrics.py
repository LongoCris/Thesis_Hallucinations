import csv
from nltk.tokenize import sent_tokenize
from difflib import SequenceMatcher

def compute_metrics(articolo_iniziale, articolo_finale,
                    df_first, df_qa,
                    selezionati_info_first, selezionati_info,
                    risultati_tracciamento,
                    domande_verificate,
                    unsupported_questions=None,
                    removal_success_rate=None):

    # === 1) TRACEABILITY ===
    tot_quarto = len(risultati_tracciamento)
    kept = sum(1 for r in risultati_tracciamento if r.get("Esito finale", "").lower() == "mantenuta")
    with_quotes = sum(
        1 for r in risultati_tracciamento
        if r.get("Esito finale", "").lower() == "mantenuta" and r.get("Verifica", "N/D") != "N/D"
    )
    ssr = kept / tot_quarto if tot_quarto else 0.0
    ac = with_quotes / kept if kept else 0.0
    ssr_strict = with_quotes / tot_quarto if tot_quarto else 0.0

    # === 2) QA ACCURACY & FIXES ===
    def _acc(df):
        if getattr(df, "empty", True):
            return 0.0
        if "Giudizio" not in df.columns:
            return 0.0
        denom = len(df)
        if denom == 0:
            return 0.0
        return df["Giudizio"].astype(str).str.contains("✅").sum() / denom

    acc_first = _acc(df_first)
    acc_second = _acc(df_qa)

    def _not_correct_count(df):
        if getattr(df, "empty", True) or "Giudizio" not in df.columns:
            return 0
        total = len(df)
        correct = df["Giudizio"].astype(str).str.contains("✅").sum()
        return int(total - correct)

    fix_count = _not_correct_count(df_first) + _not_correct_count(df_qa)

    ig_first = len(selezionati_info_first or [])
    ig_second = len(selezionati_info or [])

    # === 3) HALLUCINATIONS ===
    tot_q_hallu = len(domande_verificate or [])
    if unsupported_questions is not None:
        ucrr = (len(unsupported_questions) / tot_q_hallu) if tot_q_hallu else 0.0
    else:
        ucrr = None

    # === 4) PRESERVATION & EDITS ===
    n_init = len(sent_tokenize(articolo_iniziale or ""))
    n_final = len(sent_tokenize(articolo_finale or ""))
    rr = (n_final / n_init) if n_init else 0.0
    nes = SequenceMatcher(None, articolo_iniziale or "", articolo_finale or "").ratio()

    # === 5) OVER-REMOVAL & ERRONEOUS REMOVALS (post-hoc, no re-run) ===
    removed = max(0, n_init - n_final)

    # 5.1 Support-to-Removal Ratios
    if removed > 0:
        srr = kept / removed
        srr_strict = with_quotes / removed if with_quotes is not None else 0.0
        srr_norm = kept / (kept + removed)
        srr_strict_norm = (with_quotes / (with_quotes + removed)) if (with_quotes + removed) > 0 else 0.0
    else:
        srr = "N/D"
        srr_strict = "N/D"
        srr_norm = 1.0
        srr_strict_norm = 1.0

    # 5.2 Erroneous Removal Rate (estimated)
    uq = len(unsupported_questions or [])
    rsr_val = removal_success_rate if isinstance(removal_success_rate, (int, float)) else 0.0
    expected_removed = rsr_val * uq
    excess_removed = max(0.0, removed - expected_removed)
    err_rate = (excess_removed / removed) if removed > 0 else "N/D"

    # === RETURN STRUCTURE ===
    return {
        # --- Traceability ---
        "SentenceSupportRate": ssr,
        "AttributionCoverage": ac,
        "StrictSupportRate": ssr_strict,

        # --- QA performance ---
        "QA_Accuracy_First": acc_first,
        "QA_Accuracy_Second": acc_second,
        "Fixes_Applied_Count": int(fix_count),
        "InfoGain_First": int(ig_first),
        "InfoGain_Second": int(ig_second),

        # --- Hallucination detection ---
        "Hallucination_UCRR": ucrr,
        "RemovalSuccessRate": removal_success_rate if removal_success_rate is not None else "N/D",

        # --- Preservation ---
        "RetentionRate": rr,
        "NormalizedEditSimilarity": nes,
        "InitSentences": int(n_init),
        "FinalSentences": int(n_final),
        "ThirdCheck_Questions": int(tot_q_hallu),

        # --- Over-removal analysis ---
        "RemovedSentences": int(removed),
        "SupportToRemovalRatio": srr,
        "SupportToRemovalRatio_Strict": srr_strict,
        "SupportToRemovalRatio_Norm": srr_norm,
        "SupportToRemovalRatio_Strict_Norm": srr_strict_norm,
        "ExpectedRemoved_FromUnsupported": round(expected_removed, 4),
        "ExcessRemoved_Estimate": round(excess_removed, 4),
        "ErroneousRemovalRate_Est": err_rate,
    }


def save_metrics_csv(metrics_dict, path_csv):
    """Salva tutte le metriche in un CSV leggibile."""
    with open(path_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Metric", "Value"])
        for k, v in metrics_dict.items():
            w.writerow([k, v if v is not None else "N/D"])
    print(f"✅ Metrics salvate in: {path_csv}")
