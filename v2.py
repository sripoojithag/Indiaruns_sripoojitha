
import gzip, json, csv
from datetime import datetime

CANDIDATES_FILE = r"d:\resume\data\candidates.jsonl"
OUTPUT_FILE = "submission.csv"

JD_KEYWORDS = [
    "retrieval","ranking","recommendation","search",
    "embeddings","vector database","milvus","faiss",
    "pinecone","weaviate","elasticsearch","evaluation"
]

def open_candidates_file(path):
    return gzip.open(path, "rt") if path.endswith(".gz") else open(path, "r", encoding="utf-8")

def years_score(years):
    if 5 <= years <= 9: return 1.0
    elif years < 5: return years / 5.0
    else: return max(0.5, 9.0 / years)

def skill_score(skills):
    target = {"Python","Milvus","FAISS","Pinecone","Embeddings","Retrieval","Ranking"}
    prof_map = {"beginner":0.25,"intermediate":0.5,"advanced":0.75,"expert":1.0}
    score = 0
    for s in skills:
        if s["name"].lower() in [t.lower() for t in target]:
            score += prof_map.get(s["proficiency"],0) * (1 + s["endorsements"]/50) * (1 + s.get("duration_months",0)/24)
    return min(score, 5.0)

def career_history_score(history):
    text = " ".join([h["description"].lower() for h in history])
    matches = sum(1 for kw in JD_KEYWORDS if kw in text)
    return min(matches, 5)

def behavior_score(signals):
    score = 0
    last_active = datetime.strptime(signals["last_active_date"], "%Y-%m-%d")
    days_since_active = (datetime.now() - last_active).days
    if days_since_active < 90: score += 1
    if signals["recruiter_response_rate"] >= 0.5: score += 1
    if signals["interview_completion_rate"] >= 0.7: score += 1
    if signals["notice_period_days"] <= 60: score += 1
    if signals["github_activity_score"] > 0: score += 1
    return score

def signal_multiplier(signals):
    mult = 1.0
    if signals["recruiter_response_rate"] < 0.2: mult *= 0.5
    if signals["interview_completion_rate"] > 0.8: mult *= 1.2
    if signals["notice_period_days"] > 90: mult *= 0.7
    return mult

def trap_penalty(candidate):
    for s in candidate["skills"]:
        if s["proficiency"] == "expert" and s.get("duration_months",0) == 0:
            return -2
    if candidate["profile"]["current_title"].lower() in ["marketing manager","operations manager","customer support"]:
        return -1
    return 0

def reasoning(candidate, final_score):
    prof = candidate["profile"]
    signals = candidate["redrob_signals"]
    return (f"{prof['current_title']} with {prof['years_of_experience']} yrs; "
            f"career history shows {prof['headline']}; "
            f"recent activity {signals['last_active_date']}, response rate {signals['recruiter_response_rate']:.2f}.")

def candidate_id_num(cid):
    try:
        return int(cid.split("_")[1])
    except Exception:
        return float("inf")

def main():
    candidates = []
    with open_candidates_file(CANDIDATES_FILE) as f:
        for line in f:
            if line.strip():
                candidates.append(json.loads(line))

    print(f"Loaded {len(candidates)} candidates")

    scored = []
    for cand in candidates:
        prof_score = years_score(cand["profile"]["years_of_experience"]) + skill_score(cand["skills"]) + career_history_score(cand["career_history"])
        beh_score = behavior_score(cand["redrob_signals"])
        penalty = trap_penalty(cand)
        mult = signal_multiplier(cand["redrob_signals"])
        final_score = (prof_score*0.5 + beh_score*0.3 + penalty*0.2) * mult
        final_score = round(final_score, 4)
        scored.append((cand["candidate_id"], final_score, cand))

    # Sort full list
    scored.sort(key=lambda x: (-x[1], candidate_id_num(x[0])))

    # Find cutoff score at rank 100
    cutoff_score = scored[99][1]

    # Include all candidates tied at cutoff
    top_candidates = [s for s in scored if s[1] >= cutoff_score]

    # Re‑sort to enforce tie‑breaks
    top_candidates.sort(key=lambda x: (-x[1], candidate_id_num(x[0])))

    # Take first 100 after tie‑safe sort
    top100 = top_candidates[:100]

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["candidate_id","rank","score","reasoning"])
        for rank, (cid, score, cand) in enumerate(top100, start=1):
            writer.writerow([cid, rank, f"{score:.4f}", reasoning(cand, score)])

if __name__ == "__main__":
    main()
