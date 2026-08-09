import os
import re
import time
import random
import pandas as pd
from datetime import datetime
# lire_cv_pdf,
from src.parser import lire_portfolio_html
from src.github_parser import lire_profil_github
from src.scraper import collecter_offres
from src.company_scraper import collecter_offres_grands_groupes, MOTS_CLES_PAR_DEFAUT
from src.agent import analyser_et_rediger
from src.historique import (
    charger_historique,
    sauvegarder_historique,
    purger_historique,
    JOURS_RETENTION_MAX,
)

SEUIL_SCORE_MIN = 70
CHEMIN_REJETS = "data/offres_rejetees.json"

# ==========================================
# FILTRES : STAGE OU ALTERNANCE en Data Science / Analytics / ML / LLM / AI Engineering
# ==========================================
MOTS_CLES_DOMAINE = [
    "data science", "data scientist", "data analyst", "data analytics", "analytics",
    "machine learning", "deep learning",
    "intelligence artificielle", "ia", "ai", "ai engineer", "ai engineering",
    "nlp", "computer vision", "llm", "large language model",
    "generative ai", "ia generative", "genai",
    "data engineer", "data engineering",
    "mlops", "ml engineer", "ml engineering",
]

MOTS_CLES_CONTRAT = [
    "stage", "stagiaire", "intern", "internship",
    "alternance", "alternant", "apprentissage", "apprenti",
    "contrat de professionnalisation", "contrat d'apprentissage",
]


def _contient_mot(mots: list, texte: str) -> bool:
    """Matching à limites de mots — évite les faux positifs du type
    'ml' dans 'html' ou 'ai' dans 'portail'."""
    return any(re.search(rf"\b{re.escape(mot)}\b", texte) for mot in mots)


def est_stage_data_valide(titre: str, description: str) -> bool:
    """Vérifie que l'offre est un stage OU une alternance dans
    Data Science / Analytics / ML / LLM / AI Engineering."""
    texte = f"{titre} {description}".lower()
    est_stage_ou_alternance = _contient_mot(MOTS_CLES_CONTRAT, texte)
    est_domaine_cible = _contient_mot(MOTS_CLES_DOMAINE, texte)
    return est_stage_ou_alternance and est_domaine_cible


# ==========================================
# OFFRES REJETÉES — évite de re-payer un appel Groq
# pour une offre déjà scorée sous le seuil lors d'un run précédent
# ==========================================
def charger_ids_rejetes(chemin: str = CHEMIN_REJETS) -> set:
    if not os.path.exists(chemin):
        return set()
    try:
        import json
        with open(chemin, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception as e:
        print(f"⚠️ Erreur lors du chargement des rejets : {e}")
        return set()


def sauvegarder_ids_rejetes(ids: set, chemin: str = CHEMIN_REJETS):
    import json
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(list(ids), f, ensure_ascii=False, indent=2)


# ==========================================
# COLLECTE MULTI-SOURCES & PRÉ-FILTRAGE
# ==========================================
def tout_rassembler() -> pd.DataFrame:
    """
    Rassemble les offres de toutes les sources (JobSpy, WTTJ, Stage.fr,
    Grands Groupes) et filtre exclusivement les stages/alternances
    Data Science / Analytics / ML / LLM / AI Engineering.
    """
    print("\n🔄 Collecte globale des opportunités (Data Science, Analytics, ML, LLM & AI Engineering)...")

    df_general = collecter_offres(limites=5)

    offres_entreprises = collecter_offres_grands_groupes(mots_cles=MOTS_CLES_PAR_DEFAUT, limite=5)
    df_entreprises = pd.DataFrame(offres_entreprises)

    liste_df = [df for df in [df_general, df_entreprises] if isinstance(df, pd.DataFrame) and not df.empty]

    if not liste_df:
        return pd.DataFrame()

    df_brut = pd.concat(liste_df, ignore_index=True)
    df_brut = df_brut[df_brut["job_url"].astype(str) != ""]
    df_brut = df_brut.drop_duplicates(subset=['job_url'], keep='first')

    offres_filtrees = []
    for _, row in df_brut.iterrows():
        titre = str(row.get('title', ''))
        desc = str(row.get('description', ''))

        if est_stage_data_valide(titre, desc):
            offres_filtrees.append(row)

    print(f"🔍 {len(df_brut)} offres scannées au total ➔ {len(offres_filtrees)} stages/alternances Data/ML/IA validés.")
    return pd.DataFrame(offres_filtrees)


# ==========================================
# WORKFLOW PRINCIPAL DE L'AGENT
# ==========================================
def execution_job():
    print("\n🚀 [AGENT DATA SCIENCE / ANALYTICS / ML / LLM / AI ENGINEERING] Démarrage du scan d'offres...")

    cv_texte = lire_cv_pdf("data/cv.pdf")
    portfolio_texte = lire_portfolio_html("data/portfolio.html")
    github_texte = lire_profil_github("Dave-kossi")

    historique = purger_historique(JOURS_RETENTION_MAX)
    ids_connus = {item['id'] for item in historique if item.get('id')}
    ids_rejetes = charger_ids_rejetes()

    offres = tout_rassembler()

    if offres.empty:
        print("❌ Aucune nouvelle offre de stage/alternance Data/ML/IA trouvée lors de ce passage.")
        sauvegarder_historique(historique)
        print("🏁 [AGENT] Fin de l'exécution.")
        return

    print(f"📊 {len(offres)} offres à évaluer par l'IA...\n")

    for _, row in offres.iterrows():
        job_id = str(row.get('job_url', ''))

        # Ignore : déjà en base, déjà rejetée dans un run précédent, ou déjà traitée dans ce run
        if not job_id or job_id in ids_connus or job_id in ids_rejetes:
            continue

        entreprise = row.get('company', 'Inconnue')
        titre = row.get('title', 'Sans titre')
        raw_site = row.get('site', 'Autre')
        source_plateforme = str(raw_site).capitalize() if raw_site else "Autre"

        print(f"⚡ Analyse IA : '{titre}' chez {entreprise} (Source: {source_plateforme})...")

        offre_dict = {
            'company': entreprise,
            'title': titre,
            'description': str(row.get('description', ''))
        }

        analyse = analyser_et_rediger(offre_dict, cv_texte, portfolio_texte, github_texte)
        score = analyse.get('score_adequation', 0) if analyse else 0

        if analyse and score >= SEUIL_SCORE_MIN:
            resultat = {
                "id": job_id,
                "title": titre,
                "company": entreprise,
                "url": job_id,
                "source": source_plateforme,
                "date_ajout": datetime.now().isoformat(),
                "analyse": analyse
            }
            historique.append(resultat)
            ids_connus.add(job_id)
            print(f"  └─ ✅ Offre retenue ! (Match : {score}%)")
        else:
            ids_rejetes.add(job_id)
            print(f"  └─ ❌ Offre écartée (Match : {score}%)")

        # Évite de marteler l'API Groq sans pause si beaucoup d'offres passent le pré-filtre
        time.sleep(random.uniform(1, 2))

    sauvegarder_historique(historique)
    sauvegarder_ids_rejetes(ids_rejetes)
    print("\n✅ [AGENT] Traitement et sauvegarde réussis !")


# ==========================================
# EXÉCUTION EN POINT D'ENTRÉE
# ==========================================
if __name__ == "__main__":
    print("🤖 Agent Autonome (Stage / Alternance — Data Science, Analytics, ML, LLM, AI Engineering) démarré !")
    execution_job()
