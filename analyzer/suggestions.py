import re
from typing import List


def generate_suggestions(
    cv_text: str,
    ats_score: int,
    match_score: int,
    missing_keywords: List[str],
    language: str = "ro",
) -> List[dict]:
    suggestions = []
    lower = cv_text.lower()

    if ats_score < 50:
        suggestions.append({
            "priority": "high",
            "category": "Compatibilitate ATS" if language == "ro" else "ATS compatibility",
            "text": ("Scorul ATS este sub 50. Restructurează CV-ul cu secțiuni clare: Experiență, Educație, Competențe și Rezumat."
                     if language == "ro" else
                     "The ATS score is below 50. Restructure the CV with clear Experience, Education, Skills, and Summary sections."),
        })

    if "linkedin" not in lower:
        suggestions.append({
            "priority": "high",
            "category": "Contact",
            "text": ("Adaugă profilul LinkedIn pentru ca recrutorii să poată verifica mai ușor experiența profesională."
                     if language == "ro" else
                     "Add your LinkedIn profile so recruiters can review your professional background more easily."),
        })

    if "github" not in lower and "portfolio" not in lower:
        suggestions.append({
            "priority": "medium",
            "category": "Portofoliu" if language == "ro" else "Portfolio",
            "text": ("Adaugă un link către GitHub sau portofoliul personal pentru a demonstra competențele relevante."
                     if language == "ro" else
                     "Add a GitHub or personal portfolio link to demonstrate relevant skills."),
        })

    numbers_found = re.findall(r'\b\d+[\+\%]?\b', cv_text)
    if len(numbers_found) < 3:
        suggestions.append({
            "priority": "high",
            "category": "Realizări măsurabile" if language == "ro" else "Measurable achievements",
            "text": ("Cuantifică realizările cu cifre concrete. Ex.: „Am crescut vânzările cu 25%” sau „Am coordonat o echipă de 8 persoane”."
                     if language == "ro" else
                     "Quantify achievements with specific numbers, such as 'Increased sales by 25%' or 'Managed a team of 8'."),
        })

    if match_score < 60 and missing_keywords:
        top_kw = ", ".join(missing_keywords[:8])
        suggestions.append({
            "priority": "high",
            "category": "Cuvinte-cheie job" if language == "ro" else "Job keywords",
            "text": (f"Integrează natural aceste cuvinte-cheie din descrierea jobului: {top_kw}."
                     if language == "ro" else
                     f"Naturally include these keywords from the job description: {top_kw}."),
        })

    if len(cv_text.split()) < 250:
        suggestions.append({
            "priority": "medium",
            "category": "Conținut" if language == "ro" else "Content",
            "text": ("CV-ul este prea scurt. Extinde descrierile rolurilor cu responsabilități și realizări concrete."
                     if language == "ro" else
                     "The CV is too short. Expand role descriptions with specific responsibilities and achievements."),
        })

    if not re.search(r'(summary|rezumat|profil|profile|objective|obiectiv)', lower):
        suggestions.append({
            "priority": "medium",
            "category": "Rezumat profesional" if language == "ro" else "Professional summary",
            "text": ("Adaugă la începutul CV-ului un rezumat profesional de 3–4 rânduri care să evidențieze expertiza."
                     if language == "ro" else
                     "Add a 3–4 line professional summary at the start of the CV that highlights your expertise."),
        })

    soft_skills = ["communication", "teamwork", "leadership", "problem", "comunicare", "echipa", "lider"]
    if not any(s in lower for s in soft_skills):
        suggestions.append({
            "priority": "low",
            "category": "Soft Skills",
            "text": ("Menționează 2–3 abilități interpersonale relevante (ex.: comunicare, leadership, lucru în echipă)."
                     if language == "ro" else
                     "Mention 2–3 relevant soft skills, such as communication, leadership, or teamwork."),
        })

    if not suggestions:
        suggestions.append({
            "priority": "low",
            "category": "General",
            "text": ("CV-ul arată bine! Verifică ortografia și asigură-te că formatarea este consecventă."
                     if language == "ro" else
                     "Your CV looks good! Proofread it and make sure the formatting is consistent."),
        })

    priority_order = {"high": 0, "medium": 1, "low": 2}
    suggestions.sort(key=lambda x: priority_order[x["priority"]])
    return suggestions
