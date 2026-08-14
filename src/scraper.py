import time
import random
import requests
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
# qui remontent dans agent.py (ex: offre.get('description', '')[:3000] sur
# un NaN plante, car un float n'a pas de méthode de slicing de string).
COLONNES_STANDARD = ["site", "company", "title", "location", "description", "job_url"]


def _normaliser_dataframe(df: pd.DataFrame, site_defaut: str = "Autre") -> pd.DataFrame:
    """Force un schéma commun et des types string sur toutes les sources,
    quelle que soit leur origine (JobSpy a beaucoup plus de colonnes que
    les scrapers maison)."""
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
# 2. SCRAPER WELCOME TO THE JUNGLE (API)
# ==========================================
def collecter_offres_wttj(recherche: str, limite: int = 5) -> list:
    """Récupère les offres sur Welcome to the Jungle via leur endpoint interne."""
    url = f"https://www.welcometothejungle.com/api/v1/jobs?query={recherche}&per_page={limite}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    offres = []

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"⚠️ WTTJ status {response.status_code} pour '{recherche}'")
            return offres

        for job in response.json().get('jobs', []):
            org = job.get('organization', {})
            job_slug = job.get('slug', '')
            org_slug = org.get('slug', '')

            job_url = (
                f"https://www.welcometothejungle.com/fr/companies/{org_slug}/jobs/{job_slug}"
                if org_slug and job_slug else ""
            )

            offres.append({
                "site": "Welcome to the Jungle",
                "company": org.get('name', 'Inconnue'),
                "title": job.get('name', 'Sans titre'),
                "location": job.get('office', {}).get('city', 'France'),
                "description": (job.get('profile', '') or '') + "\n\n" + (job.get('description', '') or ''),
                "job_url": job_url
            })
    except Exception as e:
        print(f"⚠️ Erreur WTTJ ({recherche}) : {e}")

    return offres


# ==========================================
# 3. FONCTION PRINCIPALE APPELÉE PAR MAIN.PY
# ==========================================
def collecter_offres(recherche=None, localisation=None, limites=5) -> pd.DataFrame:
    """
    Parcourt les combinaisons de mots-clés et de villes sur :
    - JobSpy (LinkedIn, Indeed, Google, Glassdoor)
    - Welcome to the Jungle
    Retourne un DataFrame au schéma normalisé (voir COLONNES_STANDARD).
    """
    toutes_les_offres = []

    termes_a_chercher = [recherche] if recherche else SEARCH_TERMS[:8]
    villes_a_chercher = [localisation] if localisation else CITIES[:4]

    print(f"🔎 Lancement de la collecte globale sur {len(termes_a_chercher)} termes et {len(villes_a_chercher)} zones...")

    # 1. JobSpy (LinkedIn, Indeed, Google, Glassdoor)
    for term in termes_a_chercher:
        for city in villes_a_chercher:
            print(f"🔎 Check JobSpy : '{term}' à '{city}'")
            try:
                jobs = scrape_jobs(
                    site_name=["linkedin", "indeed", "google", "glassdoor"],
                    search_term=term,
                    location=city,
                    results_wanted=limites,
                    hours_old=72,
                    country_indeed='France'  # sert aussi de pays pour Glassdoor
                )
                if not jobs.empty:
                    toutes_les_offres.append(_normaliser_dataframe(jobs, site_defaut="JobSpy"))
                else:
                    print(f"   └─ 0 résultat (LinkedIn/Indeed/Glassdoor peuvent bloquer les IPs cloud partagées)")
            except Exception as e:
                print(f"⚠️ Erreur JobSpy ({term} - {city}) : {e}")

            # Délai aléatoire plutôt que fixe — réduit le risque de
            # rate-limit/ban sur LinkedIn/Indeed/Glassdoor.
            time.sleep(random.uniform(4, 9))

    # 2. Welcome to the Jungle
    for term in termes_a_chercher:
        print(f"🔎 Check WTTJ : '{term}'")
        offres_wttj = collecter_offres_wttj(recherche=term, limite=limites)
        if offres_wttj:
            toutes_les_offres.append(_normaliser_dataframe(pd.DataFrame(offres_wttj), site_defaut="Welcome to the Jungle"))
        time.sleep(random.uniform(1, 2))

    # 3. Fusion et nettoyage
    if toutes_les_offres:
        df_final = pd.concat(toutes_les_offres, ignore_index=True)
        df_final = df_final[df_final["job_url"] != ""]
        df_final = df_final.drop_duplicates(subset=['job_url'], keep='first')
        print(f"✅ Total : {len(df_final)} offres uniques récupérées (JobSpy + WTTJ).")
        return df_final
    else:
        print("❌ Aucune offre trouvée sur ce passage (JobSpy + WTTJ).")
        return pd.DataFrame(columns=COLONNES_STANDARD)


if __name__ == "__main__":
    # Exécution isolée pour tester rapidement la collecte sans lancer tout main.py
    df = collecter_offres(limites=3)
    print(df.head(10))
