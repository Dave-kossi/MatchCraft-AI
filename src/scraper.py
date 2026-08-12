import time
import requests
import pandas as pd
from jobspy import scrape_jobs

# ==========================================
# 1. PARAMÈTRES DE RECHERCHE CIBLÉS
# ==========================================
SEARCH_TERMS = [
    "Stage Data Scientist",
    "Stage Data Science",
    "Stage Intelligence Artificielle",
    "Stage IA Generative",
    "Stage Machine Learning",
    "Stage Data Engineer",
    "Stage LLM",
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


# ==========================================
# 2. SCRAPER WELCOME TO THE JUNGLE (API)
# ==========================================
def collecter_offres_wttj(recherche: str, limite: int = 5) -> list:
    """Récupère les offres sur Welcome to the Jungle via leur API publique."""
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
                "site": "welcometothejungle",
                "company": org.get('name'),
                "title": job.get('name'),
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
    - JobSpy (LinkedIn, Indeed, Google)
    - Welcome to the Jungle
    """
    toutes_les_offres = []

    termes_a_chercher = [recherche] if recherche else SEARCH_TERMS[:4]
    villes_a_chercher = [localisation] if localisation else CITIES[:4]

    print(f"🔎 Lancement de la collecte globale sur {len(termes_a_chercher)} termes et {len(villes_a_chercher)} zones...")

    # 1. Recherche via JobSpy (LinkedIn, Indeed, Google)
    for term in termes_a_chercher:
        for city in villes_a_chercher:
            print(f"🔎 Check JobSpy : '{term}' à '{city}'")
            try:
                jobs = scrape_jobs(
                    site_name=["linkedin", "indeed", "google"],
                    search_term=term,
                    location=city,
                    results_wanted=limites,
                    hours_old=24,
                    country_indeed='France'
                )
                if not jobs.empty:
                    toutes_les_offres.append(jobs)
                else:
                    print(f"   └─ 0 résultat (LinkedIn/Indeed peuvent bloquer les IPs cloud partagées)")
            except Exception as e:
                print(f"⚠️ Erreur JobSpy ({term} - {city}) : {e}")

            time.sleep(1)

    # 2. Recherche via Welcome to the Jungle
    for term in termes_a_chercher:
        print(f"🔎 Check WTTJ : '{term}'")
        offres_wttj = collecter_offres_wttj(recherche=term, limite=limites)
        if offres_wttj:
            toutes_les_offres.append(pd.DataFrame(offres_wttj))

    # 3. Fusion et nettoyage des résultats
    if toutes_les_offres:
        df_final = pd.concat(toutes_les_offres, ignore_index=True)
        df_final = df_final.dropna(subset=['job_url'])
        df_final = df_final.drop_duplicates(subset=['job_url'], keep='first')
        print(f"✅ Total : {len(df_final)} offres uniques récupérées (JobSpy + WTTJ).")
        return df_final
    else:
        print("❌ Aucune offre trouvée sur ce passage (JobSpy + WTTJ).")
        return pd.DataFrame()
