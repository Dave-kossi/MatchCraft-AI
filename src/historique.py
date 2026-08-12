from datetime import datetime, timedelta
import json
import os

HISTORIQUE_FILE = "data/historique.json"
JOURS_RETENTION_MAX = 2


def charger_historique(chemin: str = HISTORIQUE_FILE) -> list:
    """Charge le fichier historique.json s'il existe."""
    if not os.path.exists(chemin):
        return []
    try:
        with open(chemin, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Erreur de lecture de l'historique : {e}")
        return []


def sauvegarder_historique(historique: list, chemin: str = HISTORIQUE_FILE):
    """Enregistre la liste des offres dans le fichier local JSON."""
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(historique, f, ensure_ascii=False, indent=2)


def purger_historique(jours_max: int = JOURS_RETENTION_MAX, chemin: str = HISTORIQUE_FILE) -> list:
    """
    Purge les offres de plus de `jours_max` jours.
    Conserve systématiquement les offres avec un statut de suivi active (ex: 'Postulé', 'Entretien').
    """
    historique = charger_historique(chemin)
    if not historique:
        return []

    offres_conservees = []
    nb_purges = 0

    for offre in historique:
        statut = offre.get("statut", "A postuler")
        # Ne jamais supprimer si la candidature est engagée
        if statut in ["Postulé", "Entretien"]:
            offres_conservees.append(offre)
            continue

        date_str = offre.get("date_ajout") or offre.get("created_at") or offre.get("date")
        if not date_str:
            offres_conservees.append(offre)
            continue

        try:
            date_offre = datetime.fromisoformat(date_str.split("T")[0])
            if (datetime.now() - date_offre) > timedelta(days=jours_max):
                nb_purges += 1
            else:
                offres_conservees.append(offre)
        except Exception:
            offres_conservees.append(offre)

    if nb_purges > 0:
        print(f"🧹 {nb_purges} offre(s) obsolète(s) supprimée(s).")
        sauvegarder_historique(offres_conservees, chemin)

    return offres_conservees


def supprimer_offre_par_id(offre_id: str, chemin: str = HISTORIQUE_FILE) -> list:
    """Supprime manuellement une offre via son ID."""
    historique = charger_historique(chemin)
    nouvel_historique = [o for o in historique if o.get("id") != offre_id]
    sauvegarder_historique(nouvel_historique, chemin)
    return nouvel_historique
