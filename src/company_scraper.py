import time
import requests
import pandas as pd

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*"
}

# Utilisé par main.py quand aucune liste de mots-clés n'est fournie explicitement
MOTS_CLES_PAR_DEFAUT = [
    "Data Stage",
    "Data Scientist",
    "Machine Learning",
]

# NOTE : Eiffage, Safran, EDF pas encore ajoutés — pas d'endpoint interne confirmé.
# Méthode pour les ajouter : F12 sur la page carrières → onglet Réseau → repérer
# l'appel XHR/Fetch qui retourne du JSON, puis dupliquer un des blocs ci-dessous.


def _requete_airbus(mot_cle: str, limite: int) -> list:
    offres = []
    try:
        url = f"https://ag.jobs2web.com/api/search?q={mot_cle}&locationFacet=France&pageSize={limite}"
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            for job in res.json().get('jobs', []):
                offres.append({
                    "site": "Airbus Careers",
                    "company": "Airbus",
                    "title": job.get('title'),
                    "location": job.get('location', 'France'),
                    "description": job.get('description', 'Voir offre sur le site Airbus'),
                    "job_url": job.get('url')
                })
        else:
            print(f"⚠️ Airbus status {res.status_code}")
    except Exception as e:
        print(f"⚠️ Erreur Airbus : {e}")
    return offres


def _requete_thales(mot_cle: str, limite: int) -> list:
    offres = []
    try:
        url = "https://thales.wd3.myworkdayjobs.com/wday/cxs/thales/Careers/jobs"
        payload = {
            "appliedFacets": {"locationCountry": ["f2e609fc29784ca1b80f12713d16f06d"]},
            "limit": limite,
            "searchText": mot_cle
        }
        res = requests.post(url, json=payload, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            for job in res.json().get('jobPostings', []):
                offres.append({
                    "site": "Thales Workday",
                    "company": "Thales",
                    "title": job.get('title'),
                    "location": job.get('locationHierarchy', 'France'),
                    "description": f"Poste chez Thales : {job.get('title')}",
                    "job_url": "https://thales.wd3.myworkdayjobs.com/en-US/Careers" + job.get('externalPath', '')
                })
        else:
            print(f"⚠️ Thales status {res.status_code}")
    except Exception as e:
        print(f"⚠️ Erreur Thales : {e}")
    return offres


def _requete_sg(mot_cle: str, limite: int) -> list:
    offres = []
    try:
        url = f"https://careers.societegenerale.com/api/offers?keywords={mot_cle}&languages=fr&limit={limite}"
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            for job in res.json().get('offers', []):
                offres.append({
                    "site": "Société Générale Careers",
                    "company": "Société Générale",
                    "title": job.get('title'),
                    "location": job.get('city', 'France'),
                    "description": job.get('summary', '') or job.get('title'),
                    "job_url": f"https://careers.societegenerale.com/offres-d-emploi/{job.get('slug', '')}"
                })
        else:
            print(f"⚠️ Société Générale status {res.status_code}")
    except Exception as e:
        print(f"⚠️ Erreur Société Générale : {e}")
    return offres


def _requete_bnp(mot_cle: str, limite: int) -> list:
    offres = []
    try:
        url = f"https://api.smartrecruiters.com/v1/companies/BNPParibas/postings?q={mot_cle}&limit={limite}"
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            for job in res.json().get('content', []):
                offres.append({
                    "site": "BNP Paribas Careers",
                    "company": "BNP Paribas",
                    "title": job.get('name'),
                    "location": job.get('location', {}).get('city', 'France'),
                    "description": f"Offre BNP Paribas : {job.get('name')}",
                    "job_url": f"https://jobs.smartrecruiters.com/BNPParibas/{job.get('id')}"
                })
        else:
            print(f"⚠️ BNP Paribas status {res.status_code}")
    except Exception as e:
        print(f"⚠️ Erreur BNP Paribas : {e}")
    return offres


def collecter_offres_grands_groupes(mots_cles: list = None, limite: int = 5) -> list:
    """
    Interroge les endpoints carrières publics des grands groupes pour
    chaque mot-clé fourni. Retourne une liste dédupliquée sur job_url.
    """
    mots_cles = mots_cles or MOTS_CLES_PAR_DEFAUT
    offres_totales = []

    for mot_cle in mots_cles:
        offres_totales += _requete_airbus(mot_cle, limite)
        offres_totales += _requete_thales(mot_cle, limite)
        offres_totales += _requete_sg(mot_cle, limite)
        offres_totales += _requete_bnp(mot_cle, limite)
        time.sleep(0.5)  # pause légère entre chaque mot-clé

    # Dédoublonnage sur job_url
    vues = set()
    offres_uniques = []
    for o in offres_totales:
        url = o.get("job_url")
        if url and url not in vues:
            vues.add(url)
            offres_uniques.append(o)

    return offres_uniques
