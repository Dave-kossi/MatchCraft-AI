import time
import random
import pandas as pd
from jobspy import scrape_jobs

# ==========================================
# 1. PARAMÈTRES DE RECHERCHE CIBLÉS
# ==========================================
SEARCH_TERMS = [
    # Français — Stage
    "Stage Data Scientist",
    "Stage Data Science",
    "Stage Data Analyst",
    "Stage Intelligence Artificielle",
    "Stage IA Generative",
    "Stage Machine Learning",
    "Stage Data Engineer",
    "Stage LLM",
    # Français — Alternance
    "Alternance Data Scientist",
    "Alternance Data Science",
    "Alternance Data Analyst",
    "Alternance Machine Learning",
    "Alternance Intelligence Artificielle",
    "Alternance Data Engineer",
    # Anglais
    "Data Scientist Intern",
    "Data Science Internship",
    "Machine Learning Intern",
    "AI Intern",
    "LLM Intern",
    "Generative AI Intern",
    "Data Engineer Intern",
    "Computer Vision Intern",
    "NLP Intern",
]

CITIES = [
    "Paris, France",
    "Lyon, France",
    "Toulouse, France",
    "Lille, France",
    "Nantes, France",
    "Bordeaux, France",
    "Grenoble, France",
    "Sophia Antipolis, France",
    "Strasbourg, France",
    "Mulhouse, France",
    "Marseille, France",
    "Montpellier, France",
    "Rennes, France",
    "Nice, France",
    "Remote",
]

# Schéma commun imposé après fusion de toutes les sources — évite les NaN
COLONNES_STANDARD = ["site", "company", "title", "location", "description", "job_url"]


def _normaliser_dataframe(df: pd.DataFrame, site_defaut: str = "JobSpy") -> pd.DataFrame:
    """Force un schéma commun et des types string sur toutes les sources."""
    if df.empty:
        return pd.DataFrame(columns=COLONNES_STANDARD)

    for col in COLONNES_STANDARD:
        if col not in df.columns:
            df[col] = ""

    df = df[COLONNES_STANDARD].copy()
    df["site"] = df["site"].fillna(site_defaut)
    df["company"] = df["company"].fillna("Inconnue").astype(str)
    df["title"] = df["title"].fillna("Sans titre").astype(str)
    df["location"] = df["location"].fillna("France").astype(str)
    df["description"] = df["description"].fillna("").astype(str)
    df["job_url"] = df["job_url"].fillna("").astype(str)
    return df


# ==========================================
# 2. FONCTION PRINCIPALE APPELÉE PAR MAIN.PY
# ==========================================
def collecter_offres(recherche=None, localisation=None, limites=5) -> pd.DataFrame:
    """
    Parcourt les combinaisons de mots-clés et de villes sur JobSpy 
    (LinkedIn, Indeed, Google, ZipRecruiter).
    Retourne un DataFrame au schéma normalisé.
    """
    toutes_les_offres = []

    termes_a_chercher = [recherche] if recherche else SEARCH_TERMS[:8]
    villes_a_chercher = [localisation] if localisation else CITIES[:4]

    print(f"🔎 Lancement de la collecte globale sur {len(termes_a_chercher)} termes et {len(villes_a_chercher)} zones...")

    # JobSpy (LinkedIn, Indeed, Google, ZipRecruiter)
    for term in termes_a_chercher:
        for city in villes_a_chercher:
            print(f"🔎 Check JobSpy : '{term}' à '{city}'")
            try:
                jobs = scrape_jobs(
                    site_name=["linkedin", "indeed", "google", "zip_recruiter"],
                    search_term=term,
                    location=city,
                    results_wanted=limites,
                    hours_old=72,
                    country_indeed='France'
                )
                if not jobs.empty:
                    toutes_les_offres.append(_normaliser_dataframe(jobs, site_defaut="JobSpy"))
                else:
                    print("   └─ 0 résultat pour ce passage")
            except Exception as e:
                print(f"⚠️ Erreur JobSpy ({term} - {city}) : {e}")

            # Délai aléatoire pour réduire le risque de rate-limit/ban
            time.sleep(random.uniform(3, 7))

    # Fusion et nettoyage
    if toutes_les_offres:
        df_final = pd.concat(toutes_les_offres, ignore_index=True)
        df_final = df_final[df_final["job_url"] != ""]
        df_final = df_final.drop_duplicates(subset=['job_url'], keep='first')
        print(f"✅ Total : {len(df_final)} offres uniques récupérées via JobSpy.")
        return df_final
    else:
        print("❌ Aucune offre trouvée sur ce passage.")
        return pd.DataFrame(columns=COLONNES_STANDARD)


if __name__ == "__main__":
    df = collecter_offres(limites=3)
    print(df.head(10))
