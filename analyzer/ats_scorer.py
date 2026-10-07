import re
from dataclasses import dataclass, field
from typing import List

SECTION_KEYWORDS = {
    "contact": ["email", "phone", "telefon", "linkedin", "github", "adresa", "address"],
    "experience": ["experience", "experienta", "experiență", "work history", "employment", "job", "position", "rol"],
    "education": ["education", "educatie", "educație", "university", "universitate", "degree", "diploma", "licenta", "licență", "master", "bachelor"],
    "skills": ["skills", "competente", "competențe", "abilități", "abilitati", "technologies", "tehnologii", "tools"],
    "summary": ["summary", "rezumat", "profile", "profil", "objective", "obiectiv", "about me"],
    "projects": ["projects", "proiecte", "portfolio"],
    "certifications": ["certifications", "certificari", "certificări", "courses", "cursuri"],
}

POWER_WORDS = [
    "developed", "implemented", "managed", "led", "created", "designed", "improved",
    "increased", "decreased", "reduced", "built", "launched", "delivered", "achieved",
    "optimized", "automated", "coordinated", "analyzed", "established", "transformed",
    "dezvoltat", "implementat", "gestionat", "condus", "creat", "proiectat", "îmbunătățit",
    "crescut", "redus", "construit", "lansat", "livrat", "realizat", "optimizat",
]

QUANTIFIERS_RE = re.compile(r'\b\d+[\+\%]?\s*([\w]+)?\b')
EMAIL_RE = re.compile(r'[\w.\-]+@[\w.\-]+\.[a-z]{2,}', re.IGNORECASE)
PHONE_RE = re.compile(r'(\+?\d[\d\s\-\(\)]{7,15}\d)')


def _contains_term(text: str, term: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text, re.IGNORECASE) is not None


@dataclass
class ATSResult:
    score: int = 0
    max_score: int = 100
    breakdown: dict = field(default_factory=dict)
    feedback: List[str] = field(default_factory=list)
    found_sections: List[str] = field(default_factory=list)
    missing_sections: List[str] = field(default_factory=list)


def score_cv(text: str, language: str = "ro") -> ATSResult:
    result = ATSResult()
    lower = text.lower()

    # 1. Contact info (20pts)
    contact_score = 0
    if EMAIL_RE.search(text):
        contact_score += 10
    if PHONE_RE.search(text):
        contact_score += 5
    if "linkedin" in lower:
        contact_score += 5
    result.breakdown["Contact Info"] = (contact_score, 20)
    result.score += contact_score
    if contact_score < 15:
        result.feedback.append(
            "Adaugă emailul, telefonul și profilul LinkedIn în secțiunea de contact."
            if language == "ro"
            else "Add your email, phone number, and LinkedIn profile to the contact section."
        )

    # 2. Sections present (30pts)
    section_score = 0
    for section, keywords in SECTION_KEYWORDS.items():
        found = any(_contains_term(lower, keyword) for keyword in keywords)
        if found:
            result.found_sections.append(section)
        else:
            result.missing_sections.append(section)
    section_score = round(len(result.found_sections) / len(SECTION_KEYWORDS) * 30)
    result.breakdown["Sections"] = (section_score, 30)
    result.score += section_score
    if result.missing_sections:
        result.feedback.append(
            (f"Secțiuni lipsă sau nerecunoscute: {', '.join(result.missing_sections)}. "
             "Asigură-te că titlurile secțiunilor sunt clare.")
            if language == "ro"
            else (f"Missing or unrecognized sections: {', '.join(result.missing_sections)}. "
                  "Make sure section headings are clear.")
        )

    # 3. Power words (15pts)
    found_power = [word for word in POWER_WORDS if _contains_term(lower, word)]
    power_score = min(len(found_power) * 2, 15)
    result.breakdown["Action Verbs"] = (power_score, 15)
    result.score += power_score
    if power_score < 8:
        result.feedback.append(
            "Folosește mai multe verbe de acțiune (ex.: dezvoltat, implementat, coordonat, îmbunătățit)."
            if language == "ro"
            else "Use more action verbs (for example: developed, implemented, managed, improved)."
        )

    # 4. Quantifiable achievements (15pts)
    numbers = QUANTIFIERS_RE.findall(text)
    quant_score = min(len(numbers) * 3, 15)
    result.breakdown["Quantified Achievements"] = (quant_score, 15)
    result.score += quant_score
    if quant_score < 6:
        result.feedback.append(
            "Adaugă realizări măsurate cu cifre (ex.: „30% creștere a vânzărilor”, „echipă de 5 persoane”)."
            if language == "ro"
            else "Add measurable achievements (for example: '30% sales growth' or 'team of 5 people')."
        )

    # 5. Length/word count (10pts)
    words = text.split()
    if 300 <= len(words) <= 800:
        length_score = 10
    elif 200 <= len(words) < 300 or 800 < len(words) <= 1000:
        length_score = 6
    else:
        length_score = 2
    result.breakdown["Length"] = (length_score, 10)
    result.score += length_score
    if len(words) < 300:
        result.feedback.append(
            f"CV-ul are doar {len(words)} cuvinte. Extinde descrierile experienței (ideal 300–800 de cuvinte)."
            if language == "ro"
            else f"The CV has only {len(words)} words. Expand the experience descriptions (ideally 300–800 words)."
        )
    elif len(words) > 1000:
        result.feedback.append(
            f"CV-ul are {len(words)} cuvinte — este prea lung. Rezumă-l la 1–2 pagini."
            if language == "ro"
            else f"The CV has {len(words)} words — it is too long. Condense it to 1–2 pages."
        )

    # 6. Formatting signals (10pts)
    fmt_score = 0
    if len(text) > 0 and "\n" in text:
        fmt_score += 5
    if not re.search(r'(table|tabel)', lower):
        fmt_score += 5
    result.breakdown["Formatting"] = (fmt_score, 10)
    result.score += fmt_score

    result.score = min(result.score, 100)
    return result
