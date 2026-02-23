import pandas as pd
import re
import unicodedata
from rapidfuzz import process, fuzz

roster_path = "roster.csv"
roster = pd.read_csv(roster_path)

FIRST_COL = "First Name"
FIRST_THRESH = 60
LAST_COL = "Last Name"
LAST_THRESH = 60
WINDOW = 4

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

roster = pd.read_csv(roster_path)

students_blob = normalize(clean_attendance('image.txt'))
tokens = students_blob.split()

attended = []
match_score = []

for _, row in roster.iterrows():
    first = normalize(row.get(FIRST_COL, ""))
    last  = normalize(row.get(LAST_COL, ""))

    if not first or not last:
        attended.append(0)
        match_score.append(0.0)
        continue

    best = -1.0
    found = 0

    last_hits = process.extract(last, tokens, scorer=fuzz.ratio, score_cutoff=LAST_THRESH)
    for _, last_score, idx in last_hits:
        lo = max(0, idx - WINDOW)
        hi = min(len(tokens), idx + WINDOW + 1)
        neighborhood = tokens[lo:hi]

        first_hit = process.extractOne(first, neighborhood, scorer=fuzz.ratio)
        if not first_hit:
            continue

        _, first_score, _ = first_hit
        if first_score < FIRST_THRESH:
            continue

        combined = last_score + first_score
        if combined > best:
            best = combined
            found = 1

    attended.append(found)
    match_score.append(best if best > 0 else 0.0)

roster["Attended"] = attended
roster["MatchScore"] = match_score

out_path = "roster_new.csv"
roster.to_csv(out_path, index=False)

print("Wrote:", out_path)
print("Attended count:", int(roster["Attended"].sum()))
