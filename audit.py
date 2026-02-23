import pandas as pd
import re
import unicodedata
from rapidfuzz import process, fuzz

roster_path = "roster_new.csv"
roster = pd.read_csv(roster_path)

FIRST_COL = "First Name"
LAST_COL  = "Last Name"

AUDIT_FIRST_CUTOFF = 35
AUDIT_LAST_CUTOFF  = 35
AUDIT_TOPN_ANCHOR  = 8
AUDIT_TOPN_NEAR    = 5
AUDIT_WINDOW = 8

def clean_attendance(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        raw_text = f.read()
    raw_text = re.sub(r'CNIT.*', '', raw_text)
    raw_text = re.sub(r'\d+', '', raw_text)
    raw_text = re.sub(r'[^A-Za-zÀ-ÖØ-öø-ÿ\s\'()]', '', raw_text)
    raw_text = re.sub(r'\b(?:Am|un|JAN|Date|Z)\b', '', raw_text, flags=re.IGNORECASE)
    raw_text = re.sub(r'\s+', ' ', raw_text).strip()
    return raw_text

def normalize(text):
    text = str(text)
    text = text.replace("(", " ").replace(")", " ")
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-z\s']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def best_name_score(name_norm, candidates):
    if not name_norm:
        return (None, 0.0)
    hit = process.extractOne(name_norm, candidates, scorer=fuzz.ratio)
    if not hit:
        return (None, 0.0)
    cand, score, _ = hit
    return (cand, float(score))

def best_last_score(last_norm, candidates):
    if not last_norm:
        return (None, 0.0)

    parts = last_norm.split()
    parts = [p for p in parts if p]

    best_cand, best_score = None, 0.0

    for p in parts:
        cand, score = best_name_score(p, candidates)
        if score > best_score:
            best_cand, best_score = cand, score

    if len(parts) >= 2:
        for i in range(len(parts) - 1):
            bigram = parts[i] + " " + parts[i+1]
            cand, score = best_name_score(bigram, [" ".join(candidates[j:j+2]) for j in range(max(0, len(candidates)-1))] or [])
            if score > best_score:
                best_cand, best_score = cand, score

    return (best_cand, best_score)

students_blob = normalize(clean_attendance("image3.txt"))
tokens = students_blob.split()

if "Attended" not in roster.columns:
    roster["Attended"] = 0

audit_rows = []
missing = roster[roster["Attended"] == 0].copy()

for idx, row in missing.iterrows():
    first = normalize(row.get(FIRST_COL, ""))
    last  = normalize(row.get(LAST_COL, ""))

    if not first and not last:
        continue

    last_parts = last.split()

    anchor_last_hits = []
    for lp in last_parts:
        if lp:
            anchor_last_hits.extend(process.extract(lp, tokens, scorer=fuzz.ratio, score_cutoff=AUDIT_LAST_CUTOFF, limit=AUDIT_TOPN_ANCHOR))

    anchor_last_hits.sort(key=lambda x: x[1], reverse=True)
    seen_anchor_idx = set()

    for cand_last, last_score, token_i in anchor_last_hits:
        if token_i in seen_anchor_idx:
            continue
        seen_anchor_idx.add(token_i)

        lo = max(0, token_i - AUDIT_WINDOW)
        hi = min(len(tokens), token_i + AUDIT_WINDOW + 1)
        neighborhood = tokens[lo:hi]

        cand_first, first_score = best_name_score(first, neighborhood)
        if first_score >= AUDIT_FIRST_CUTOFF:
            audit_rows.append({
                "RosterIndex": idx,
                "RosterFirst": row.get(FIRST_COL, ""),
                "RosterLast": row.get(LAST_COL, ""),
                "Direction": "LAST->FIRST",
                "CandFirstToken": cand_first,
                "FirstScore": first_score,
                "CandLastToken": cand_last,
                "LastScore": float(last_score),
                "Combined": float(last_score) + float(first_score),
                "Context": " ".join(neighborhood)
            })

    anchor_first_hits = process.extract(first, tokens, scorer=fuzz.ratio, score_cutoff=AUDIT_FIRST_CUTOFF, limit=AUDIT_TOPN_ANCHOR) if first else []
    anchor_first_hits.sort(key=lambda x: x[1], reverse=True)

    for cand_first, first_score, token_i in anchor_first_hits:
        lo = max(0, token_i - AUDIT_WINDOW)
        hi = min(len(tokens), token_i + AUDIT_WINDOW + 1)
        neighborhood = tokens[lo:hi]

        cand_last, last_score = best_last_score(last, neighborhood)
        if last_score >= AUDIT_LAST_CUTOFF:
            audit_rows.append({
                "RosterIndex": idx,
                "RosterFirst": row.get(FIRST_COL, ""),
                "RosterLast": row.get(LAST_COL, ""),
                "Direction": "FIRST->LAST",
                "CandFirstToken": cand_first,
                "FirstScore": float(first_score),
                "CandLastToken": cand_last,
                "LastScore": float(last_score),
                "Combined": float(first_score) + float(last_score),
                "Context": " ".join(neighborhood)
            })

audit_df = pd.DataFrame(audit_rows)

if audit_df.empty:
    print("No candidates found for missing students.")
else:
    audit_df = audit_df.sort_values(
        by=["RosterIndex", "Combined", "LastScore", "FirstScore"],
        ascending=[True, False, False, False]
    )
    best_df = audit_df.groupby("RosterIndex").head(1).reset_index(drop=True)

    for _, r in best_df.iterrows():
        cand_first = r["CandFirstToken"] if pd.notna(r["CandFirstToken"]) else ""
        cand_last  = r["CandLastToken"] if pd.notna(r["CandLastToken"]) else ""
        print(
            f"[{int(r['RosterIndex'])}] "
            f"{r['RosterFirst']} {r['RosterLast']} "
            f"-> '{(str(cand_first) + ' ' + str(cand_last)).strip()}' "
            f"(Combined={r['Combined']:.1f}, Direction={r['Direction']})"
        )

    best_df.to_csv("missing_attendance_best_matches.csv", index=False)
    print("Wrote: missing_attendance_best_matches.csv")
