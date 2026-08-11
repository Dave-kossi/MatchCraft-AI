import json
import os
import random
import re
import time
from datetime import datetime
import pandas as pd

from src.agent import analyser_et_rediger
from src.company_scraper import MOTS_CLES_PAR_DEFAUT, collecter_offres_grands_groupes
from src.cv_agent import generer_cv_pdf  # Import du module CV
from src.github_parser import lire_profil_github
from src.historique import (
    JOURS_RETENTION_MAX,
    charger_historique,
    purger_historique,
    sauvegarder_historique,
)
from src.parser import lire_cv_pdf, lire_portfolio_html
from src.scraper import collecter_offres

# ==========================================
# CONFIGURATION MATCHCRAFT AI
# ==========================================
GITHUB_USERNAME = "Dave-kossi"
SEUIL_SCORE_MIN = 70

CHEMIN_CV = "data/cv.pdf"
CHEMIN_PORTFOLIO = "data/portfolio.html"
CHEMIN_REJETS = "data/offres_rejetees.json"

# ==========================================
# FILTRES : STAGE OU ALTERNANCE (DATA / IA)
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
    """Matching à limites de mots — évite les faux positifs."""
    return any(re.search(rf"\b{re.escape(mot)}\b", texte) for mot in mots)


def est_stage_data_valide(titre: str, description: str) -> bool:
    """Vérifie que l'offre est un stage/alternance ciblant la Data / IA."""
    texte = f"{titre} {description}".lower()
    est_stage_ou_alternance = _contient_mot(MOTS_CLES_CONTRAT, texte)
    est_domaine_cible = _contient_mot(MOTS_CLES_DOMAINE, texte)
    return est_stage_ou_alternance and est_domaine_cible


# ==========================================
# GESTION DU CACHE DES REJETS
# ==========================================
def charger_ids_rejetes(chemin: str = CHEMIN_REJETS) -> set:
    if not os.path.exists(chemin):
        return set()
    try:
        with open(chemin, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception as e:
        print(f"⚠️ Erreur chargement rejets : {e}")
        return set()


def sauvegarder_ids_rejetes(ids: set, chemin: str = CHEMIN_REJETS):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(list(ids), f, ensure_ascii=False, indent=2)


# ==========================================
# COLLECTE MULTI-SOURCES & PRÉ-FILTRAGE
# ==========================================
def tout_rassembler() -> pd.DataFrame:
    """Rassemble et filtre les offres provenant de toutes les sources."""
    print("\n🔍 [MatchCraft AI] Lancement de la collecte multi-sources...")

    df_general = collecter_offres(limites=5)
    offres_entreprises = collecter_offres_grands_groupes(
        mots_cles=MOTS_CLES_PAR_DEFAUT, limite=5
    )
    df_entreprises = pd.DataFrame(offres_entreprises)

    liste_df = [
        df for df in [df_general, df_entreprises]
        if isinstance(df, pd.DataFrame) and not df.empty
    ]

    if not liste_df:
        return pd.DataFrame()

    df_brut = pd.concat(liste_df, ignore_index=True)
    df_brut = df_brut[df_brut["job_url"].astype(str) != ""]
    df_brut = df_brut.drop_duplicates(subset=["job_url"], keep="first")

    offres_filtrees = [
        row for _, row in df_brut.iterrows()
        if est_stage_data_valide(str(row.get("title", "")), str(row.get("description", "")))
    ]

    print(f"📊 Total scanné : {len(df_brut)} | Retenu après pré-filtrage : {len(offres_filtrees)}")
    return pd.DataFrame(offres_filtrees)


# ==========================================
# WORKFLOW PRINCIPAL DU MATCHCRAFT AGENT
# ==========================================
def execution_job():
    print(f"\n🚀 [MatchCraft AI] Démarrage de l'agent pour {GITHUB_USERNAME}...")

    # Chargement des données candidat
    cv_texte = lire_cv_pdf(CHEMIN_CV) if os.path.exists(CHEMIN_CV) else ""
    portfolio_texte = lire_portfolio_html(CHEMIN_PORTFOLIO) if os.path.exists(CHEMIN_PORTFOLIO) else ""
    github_texte = lire_profil_github(GITHUB_USERNAME)

    historique = purger_historique(JOURS_RETENTION_MAX)
    ids_connus = {item["id"] for item in historique if item.get("id")}
    ids_rejetes = charger_ids_rejetes()

    offres = tout_rassembler()

    if offres.empty:
        print("❌ Aucune nouvelle opportunité qualifiée lors de ce scan.")
        sauvegarder_historique(historique)
        print("🏁 [MatchCraft AI] Fin du cycle.")
        return

    print(f"⚡ {len(offres)} offres prêtes pour évaluation agentique...\n")

    for _, row in offres.iterrows():
        job_id = str(row.get("job_url", ""))

        if not job_id or job_id in ids_connus or job_id in ids_rejetes:
            continue

        entreprise = row.get("company", "Inconnue")
        titre = row.get("title", "Sans titre")
        raw_site = row.get("site", "Autre")
        source_plateforme = str(raw_site).capitalize() if raw_site else "Autre"

        print(f"🤖 Analyse MatchCraft : '{titre}' chez {entreprise} ({source_plateforme})...")

        offre_dict = {
            "company": entreprise,
            "title": titre,
            "description": str(row.get("description", "")),
        }

        # 1. Pipeline LLM (Matching + Rédaction de la lettre)
        analyse = analyser_et_rediger(
            offre=offre_dict,
            cv_texte=cv_texte,
            portfolio_texte=portfolio_texte,
            github_texte=github_texte
        )

        score = analyse.get("score_adequation", 0) if analyse else 0

        if analyse and score >= SEUIL_SCORE_MIN:
            # 2. Génération du CV PDF sur-mesure pour cette offre qualifiée
            # Réutilise le matching déjà calculé dans analyser_et_rediger() —
            # évite un second appel LLM identique (économie de quota).
            matching_info = analyse["matching"]
            chemin_cv = generer_cv_pdf(offre_dict, analyse_matching=matching_info)

            resultat = {
                "id": job_id,
                "title": titre,
                "company": entreprise,
                "url": job_id,
                "source": source_plateforme,
                "date_ajout": datetime.now().isoformat(),
                "analyse": analyse,
                "cv_pdf_path": chemin_cv,  # Ajout de la référence du fichier CV généré
            }

            historique.append(resultat)
            ids_connus.add(job_id)
            sauvegarder_historique(historique)  # Sauvegarde incrémentale de sécurité
            print(f"   └─ ✅ QUALIFIÉE ! (Score MatchCraft : {score}%) — CV PDF : {chemin_cv}")
        else:
            ids_rejetes.add(job_id)
            sauvegarder_ids_rejetes(ids_rejetes)  # Sauvegarde incrémentale
            print(f"   └─ ❌ ÉCARTÉE (Score MatchCraft : {score}%)")

        time.sleep(random.uniform(1, 2))

    print("\n✅ [MatchCraft AI] Synchronisation de la base terminée avec succès !")


# ==========================================
# POINT D'ENTRÉE
# ==========================================
if __name__ == "__main__":
    print("⚡ Démarrage du moteur MatchCraft AI...")
    execution_job()
