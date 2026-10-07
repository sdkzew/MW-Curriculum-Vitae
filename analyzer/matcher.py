import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class MatchResult:
    score: int = 0
    matched_keywords: List[str] = field(default_factory=list)
    missing_keywords: List[str] = field(default_factory=list)
    feedback: str = ""


def _tokenize(text: str) -> set:
    normalized = text.lower()
    technology_tokens = {
        match.group(0).replace(" ", "")
        for match in re.finditer(r"(?<!\w)(?:c\+\+|c#|\.net|node(?:\.js|\s+js))(?!\w)", normalized)
    }
    words = re.findall(r'\b[a-zA-ZăîâșțĂÎÂȘȚ][a-zA-Z0-9ăîâșțĂÎÂȘȚ-]{2,}\b', normalized)
    stopwords = {
        "and", "the", "for", "with", "that", "this", "are", "you", "have",
        "will", "from", "our", "their", "your", "not", "all", "can", "but",
        "sau", "si", "cu", "de", "la", "in", "pe", "un", "cel", "ale",
    }
    return {word for word in words if word not in stopwords} | technology_tokens


def match_job(cv_text: str, job_text: str) -> MatchResult:
    if not job_text.strip():
        return MatchResult(score=0, feedback="Nu a fost furnizata o descriere de job.")

    cv_tokens = _tokenize(cv_text)
    job_tokens = _tokenize(job_text)

    if not job_tokens:
        return MatchResult(score=0, feedback="Descrierea jobului nu contine text relevant.")

    matched = cv_tokens & job_tokens
    missing = job_tokens - cv_tokens

    score = int((len(matched) / len(job_tokens)) * 100)
    score = min(score, 100)

    top_missing = sorted(missing, key=len, reverse=True)[:15]

    if score >= 75:
        feedback = "Potrivire excelenta! CV-ul tau acopera majoritatea cerintelor jobului."
    elif score >= 50:
        feedback = "Potrivire buna. Adauga cateva cuvinte cheie lipsa pentru a creste compatibilitatea."
    elif score >= 30:
        feedback = "Potrivire medie. CV-ul tau lipseste mai multe cuvinte cheie din descrierea jobului."
    else:
        feedback = "Potrivire slaba. Considera personalizarea CV-ului specific pentru acest job."

    return MatchResult(
        score=score,
        matched_keywords=sorted(matched)[:20],
        missing_keywords=top_missing,
        feedback=feedback,
    )
