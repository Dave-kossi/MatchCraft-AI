from datetime import datetime, timedelta
import json
import os
from src.github_writer import sauvegarder_historique_sur_github

HISTORIQUE_FILE = "data/historique.json"


def charger_historique() -> list:
    """Charge le fichier historique.json s'il existe."""
    if not os.path.exists(HISTORIQUE_FILE):
        return []
    try:
        with open(HISTORIQUE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Erreur de lecture de l'historique : {e}")
        return []


def sauvegarder_historique(historique: list, synchroniser_github: bool = True, message_commit: str = "Mise à jour statut offres"):
    """Enregistre l'historique en local ET pousse sur GitHub."""
    os.makedirs(os.path.dirname(HISTORIQUE_FILE), exist_ok=True)
    
    # 1. Écriture locale
    with open(HISTORIQUE_FILE, "w", encoding="utf-8") as f:
        json.dump(historique, f, ensure_ascii=False, indent=2)

    # 2. Synchronisation GitHub
    if synchroniser_github:
        sauvegarder_historique_sur_github(historique, message=message_commit)


def supprimer_offre_par_id(offre_id: str) -> list:
    """Supprime une offre spécifique par son ID."""
    historique = charger_historique()
    nouvel_historique = [o for o in historique if o.get("id") != offre_id]
    
    sauvegarder_historique(
        nouvel_historique, 
        synchroniser_github=True, 
        message_commit=f"Suppression de l'offre ID {offre_id}"
    )
    return nouvel_historique


def nettoyer_offres_obsoletes(max_jours: int = 2) -> list:
    """
    Supprime automatiquement les offres de plus de `max_jours`.
    Conserve toujours les offres avec le statut 'Postulé' ou 'Entretien'.
    """
    historique = charger_historique()
    if not historique:
        return []

    offres_gardees = []
    nb_purged = 0

    for offre in historique:
        statut = offre.get("statut", "A postuler")
        # Ne jamais supprimer si on a déjà postulé ou obtenu un entretien
        if statut in ["Postulé", "Entretien"]:
            offres_gardees.append(offre)
            continue

        date_str = offre.get("date_ajout") or offre.get("created_at") or offre.get("date")
        if not date_str:
            offres_gardees.append(offre)
            continue

        try:
            date_offre = datetime.fromisoformat(date_str.split("T")[0])
            if (datetime.now() - date_offre) > timedelta(days=max_jours):
                nb_purged += 1
            else:
                offres_gardees.append(offre)
        except Exception:
            offres_gardees.append(offre)

    if nb_purged > 0:
        print(f"🧹 {nb_purged} offre(s) obsolète(s) supprimée(s).")
        sauvegarder_historique(
            offres_gardees, 
            synchroniser_github=True, 
            message_commit=f"🧹 Nettoyage auto : {nb_purged} offre(s) expirée(s)"
        )

    return offres_gardees
