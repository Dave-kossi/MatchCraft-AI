import time
import requests
import pandas as pd

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*"
}

MOTS_CLES_PAR_DEFAUT = [
    "Stage Data Scientist", "Alternance Data Scientist",
    "Stage Data Science", "Alternance Data Science",
    "Stage Machine Learning", "Alternance Machine Learning",
]


# ==========================================
# SOURCE OPÉRATIONNELLE — confirmée en fonctionnement
# ==========================================
def _requete_bnp(mot_cle: str, limite: int) -> list:
    offres = []
    try:
        url = f"https://api.smartrecruiters.com/v1/companies/BNPParibas/postings?q={mot_cle}&limit={limite}"
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            for job in res.json().get('content', []):
                offres.append({
                    "site": "BNP Paribas Careers", "company": "BNP Paribas",
                    "title": job.get('name'), "location": job.get('location', {}).get('city', 'France'),
                    "description": f"Offre BNP Paribas : {job.get('name')}",
                    "job_url": f"https://jobs.smartrecruiters.com/BNPParibas/{job.get('id')}"
                })
        else:
            print(f"⚠️ BNP Paribas status {res.status_code}")
    except Exception as e:
        print(f"⚠️ Erreur BNP Paribas : {e}")
    return offres


SOURCES_OPERATIONNELLES = [_requete_bnp]


# ==========================================
# SOURCES EN PAUSE — code gardé pour référence, retiré du pipeline actif
# suite aux échecs constatés le [date du run]. Diagnostic déjà posé,
# à corriger dès que l'endpoint réel est reconfirmé manuellement.
# ==========================================
def _requete_airbus(mot_cle: str, limite: int) -> list:
    """EN PAUSE — ag.jobs2web.com ne se résout plus en DNS (échec de résolution,
    pas un blocage HTTP). Soit Airbus a changé de prestataire ATS, soit c'est un
    souci réseau local. À vérifier manuellement avant de réactiver."""
    offres = []
    try:
        url = f"https://ag.jobs2web.com/api/search?q={mot_cle}&locationFacet=France&pageSize={limite}"
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            for job in res.json().get('jobs', []):
                offres.append({
                    "site": "Airbus Careers", "company": "Airbus",
                    "title": job.get('title'), "location": job.get('location', 'France'),
                    "description": job.get('description', 'Voir offre sur le site Airbus'),
                    "job_url": job.get('url')
                })
        else:
            print(f"⚠️ Airbus status {res.status_code}")
    except Exception as e:
        print(f"⚠️ Erreur Airbus : {e}")
    return offres


def _requete_thales(mot_cle: str, limite: int) -> list:
    """EN PAUSE — status 400. L'ID de facette locationCountry codé en dur
    n'est probablement plus valide (ces IDs Workday changent par tenant/mise
    à jour). À recapturer via F12 sur une recherche réelle avant réactivation."""
    offres = []
    try:
        url = "https://thales.wd3.myworkdayjobs.com/wday/cxs/thales/Careers/jobs"
        payload = {
            "appliedFacets": {"locationCountry": ["f2e609fc29784ca1b80f12713d16f06d"]},
            "limit": limite, "searchText": mot_cle
        }
        res = requests.post(url, json=payload, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            for job in res.json().get('jobPostings', []):
                offres.append({
                    "site": "Thales Workday", "company": "Thales",
                    "title": job.get('title'), "location": job.get('locationHierarchy', 'France'),
                    "description": f"Poste chez Thales : {job.get('title')}",
                    "job_url": "https://thales.wd3.myworkdayjobs.com/en-US/Careers" + job.get('externalPath', '')
                })
        else:
            print(f"⚠️ Thales status {res.status_code}")
    except Exception as e:
        print(f"⚠️ Erreur Thales : {e}")
    return offres


def _requete_sg(mot_cle: str, limite: int) -> list:
    """EN PAUSE — status 404. La route /api/offers n'existe plus telle quelle,
    Société Générale a probablement changé son endpoint interne. À retrouver
    via F12 avant réactivation."""
    offres = []
    try:
        url = f"https://careers.societegenerale.com/api/offers?keywords={mot_cle}&languages=fr&limit={limite}"
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            for job in res.json().get('offers', []):
                offres.append({
                    "site": "Société Générale Careers", "company": "Société Générale",
                    "title": job.get('title'), "location": job.get('city', 'France'),
                    "description": job.get('summary', '') or job.get('title'),
                    "job_url": f"https://careers.societegenerale.com/offres-d-emploi/{job.get('slug', '')}"
                })
        else:
            print(f"⚠️ Société Générale status {res.status_code}")
    except Exception as e:
        print(f"⚠️ Erreur Société Générale : {e}")
    return offres


# ==========================================
# SOURCES À INTÉGRER — endpoint jamais identifié.
#
# Méthode : ouvrir "url_carriere" → F12 → onglet Réseau → filtrer "Fetch/XHR"
# → lancer une recherche sur le site → repérer l'appel qui retourne du JSON
# avec la liste d'offres → écrire une fonction _requete_xxx() sur le modèle
# de _requete_bnp() → l'ajouter à SOURCES_OPERATIONNELLES.
# ==========================================
SOURCES_A_INTEGRER = [
    {"nom": "TotalEnergies", "secteur": "Énergie", "url_carriere": "https://jobs.totalenergies.com"},
    {"nom": "ENGIE", "secteur": "Énergie", "url_carriere": "https://jobs.engie.com"},
    {"nom": "EDF / Enedis", "secteur": "Énergie", "url_carriere": "https://www.edf.fr/edf-recrute"},
    {"nom": "Veolia", "secteur": "Énergie", "url_carriere": "https://www.veolia.com/fr/carrieres"},
    {"nom": "Suez", "secteur": "Énergie", "url_carriere": "https://www.suez.com/fr/carrieres"},

    {"nom": "Renault Group", "secteur": "Industrie", "url_carriere": "https://www.renaultgroup.com/carrieres/"},
    {"nom": "Safran", "secteur": "Industrie", "url_carriere": "https://www.safran-group.com/fr/carrieres"},
    {"nom": "Dassault Systèmes", "secteur": "Industrie", "url_carriere": "https://www.3ds.com/fr/careers"},
    {"nom": "Alstom", "secteur": "Industrie", "url_carriere": "https://www.alstom.com/fr/carrieres"},
    {"nom": "Saint-Gobain", "secteur": "Industrie", "url_carriere": "https://www.saint-gobain.com/fr/carrieres"},
    {"nom": "Schneider Electric", "secteur": "Industrie", "url_carriere": "https://www.se.com/fr/fr/about-us/careers/"},
    {"nom": "Michelin", "secteur": "Industrie", "url_carriere": "https://carrieres.michelin.fr"},
    {"nom": "Air Liquide", "secteur": "Industrie", "url_carriere": "https://www.airliquide.com/fr/carrieres"},

    {"nom": "Crédit Agricole", "secteur": "Banque", "url_carriere": "https://groupecreditagricole.jobs"},
    {"nom": "BPCE / Natixis", "secteur": "Banque", "url_carriere": "https://www.groupebpce.com/carrieres"},
    {"nom": "Crédit Mutuel", "secteur": "Banque", "url_carriere": "https://www.creditmutuel.com/fr/emploi.html"},
    {"nom": "La Banque Postale", "secteur": "Banque", "url_carriere": "https://www.labanquepostale.com/carrieres.html"},

    {"nom": "AXA", "secteur": "Assurance", "url_carriere": "https://www.axa.fr/carrieres"},
    {"nom": "Allianz France", "secteur": "Assurance", "url_carriere": "https://www.allianz.fr/carrieres"},
    {"nom": "Generali France", "secteur": "Assurance", "url_carriere": "https://www.generali.fr/carrieres"},
    {"nom": "Covéa (MAAF/MMA/GMF)", "secteur": "Assurance", "url_carriere": "https://www.covea.eu/fr/carrieres"},
    {"nom": "MAIF", "secteur": "Assurance", "url_carriere": "https://www.maif.fr/recrutement.html"},
    {"nom": "Groupama", "secteur": "Assurance", "url_carriere": "https://www.groupama.com/fr/carrieres/"},
]


def lister_sources_a_completer():
    """Affiche le backlog de sources non encore intégrées, groupé par secteur."""
    par_secteur = {}
    for s in SOURCES_A_INTEGRER:
        par_secteur.setdefault(s["secteur"], []).append(s["nom"])
    for secteur, noms in par_secteur.items():
        print(f"\n{secteur} ({len(noms)} sources à intégrer) :")
        for nom in noms:
            print(f"  - {nom}")
    print(f"\nEn pause (code gardé, désactivé) : Airbus, Thales, Société Générale")


def collecter_offres_grands_groupes(mots_cles: list = None, limite: int = 5) -> list:
    """
    Interroge les endpoints carrières publics des grands groupes actuellement
    opérationnels (voir SOURCES_OPERATIONNELLES) pour chaque mot-clé fourni.
    Retourne une liste dédupliquée sur job_url.
    """
    mots_cles = mots_cles or MOTS_CLES_PAR_DEFAUT
    offres_totales = []

    for mot_cle in mots_cles:
        for fonction_source in SOURCES_OPERATIONNELLES:
            offres_totales += fonction_source(mot_cle, limite)
        time.sleep(0.5)

    vues = set()
    offres_uniques = []
    for o in offres_totales:
        url = o.get("job_url")
        if url and url not in vues:
            vues.add(url)
            offres_uniques.append(o)

    return offres_uniques


if __name__ == "__main__":
    lister_sources_a_completer()
