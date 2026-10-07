import re
from typing import List


def generate_suggestions(cv_text: str, ats_score: int, match_score: int, missing_keywords: List[str]) -> List[dict]:
    suggestions = []
    lower = cv_text.lower()

    if ats_score < 50:
        suggestions.append({
            "priority": "high",
            "category": "ATS Compatibility",
            "text": "Scorul ATS este sub 50. Restructureaza CV-ul cu sectiuni clare: Experienta, Educatie, Skills, Rezumat.",
        })

    if "linkedin" not in lower:
        suggestions.append({
            "priority": "high",
            "category": "Contact",
            "text": "Adauga profilul tau LinkedIn pentru ca recrutorii sa poata verifica mai usor experienta profesionala.",
        })

    if "github" not in lower and "portfolio" not in lower:
        suggestions.append({
            "priority": "medium",
            "category": "Portfolio",
            "text": "Adauga un link catre GitHub sau portfolio personal pentru a demonstra abilitatile tehnice.",
        })

    numbers_found = re.findall(r'\b\d+[\+\%]?\b', cv_text)
    if len(numbers_found) < 3:
        suggestions.append({
            "priority": "high",
            "category": "Realizari Masurabile",
            "text": "Cuantifica realizarile cu cifre concrete. Ex: 'Am crescut vanzarile cu 25%' sau 'Am gestionat o echipa de 8 persoane'.",
        })

    if match_score < 60 and missing_keywords:
        top_kw = ", ".join(missing_keywords[:8])
        suggestions.append({
            "priority": "high",
            "category": "Cuvinte Cheie Job",
            "text": f"Integreaza natural aceste cuvinte cheie din descrierea jobului: {top_kw}.",
        })

    if len(cv_text.split()) < 250:
        suggestions.append({
            "priority": "medium",
            "category": "Continut",
            "text": "CV-ul este prea scurt. Extinde descrierile rolurilor cu responsabilitati si realizari concrete.",
        })

    if not re.search(r'(summary|rezumat|profil|profile|objective|obiectiv)', lower):
        suggestions.append({
            "priority": "medium",
            "category": "Rezumat Profesional",
            "text": "Adauga un rezumat profesional de 3-4 randuri la inceputul CV-ului care sa evidentieze expertiza ta.",
        })

    soft_skills = ["communication", "teamwork", "leadership", "problem", "comunicare", "echipa", "lider"]
    if not any(s in lower for s in soft_skills):
        suggestions.append({
            "priority": "low",
            "category": "Soft Skills",
            "text": "Mentioneaza 2-3 soft skills relevante (ex: comunicare, leadership, lucru in echipa).",
        })

    if not suggestions:
        suggestions.append({
            "priority": "low",
            "category": "General",
            "text": "CV-ul tau arata bine! Asigura-te ca verifici ortografia si ca formatarea este consistenta.",
        })

    priority_order = {"high": 0, "medium": 1, "low": 2}
    suggestions.sort(key=lambda x: priority_order[x["priority"]])
    return suggestions
