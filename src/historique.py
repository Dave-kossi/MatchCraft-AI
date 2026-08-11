# src/historique.py
import os
import json
from datetime import datetime, timedelta

CHEMIN_HISTORIQUE = "data/historique.json"
JOURS_RETENTION_MAX = 2


def _get_mtime(chemin: str) -> float:
    """Retourne la date de dernière modification du fichier JSON.
    Permet d'invalider automatiquement le cache Streamlit lorsque GitHub Actions met à jour le fichier.
    """
    if os.path.exists(chemin):
        return os.path.getmtime(chemin)
    return 0.0


def _charger_depuis_disque(chemin: str) -> list:
    """Lecture brute du fichier sur le disque."""
    if not os.path.exists(chemin):
        return []
    try:
        with open(chemin, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Erreur lors du chargement de l'historique : {e}")
        return []


def charger_historique(chemin: str = CHEMIN_HISTORIQUE) -> list:
    """Charge l'historique de manière optimisée.
    Applique le cache Streamlit si exécuté dans une app Streamlit.
    """
    mtime = _get_mtime(chemin)

    try:
        import streamlit as st

        @st.cache_data(ttl=300)
        def _charger_avec_cache(path: str, file_mtime: float) -> list:
            return _charger_depuis_disque(path)

        return _charger_avec_cache(chemin, mtime)

    except ImportError:
        # Exécution hors Streamlit (Agent / Script CRON)
        return _charger_depuis_disque(chemin)


def sauvegarder_historique(data: list, chemin: str = CHEMIN_HISTORIQUE):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Si on est dans Streamlit, on vide le cache immédiatement après modification
    try:
        import streamlit as st
        st.cache_data.clear()
    except Exception:
        pass


def _parser_date(date_str) -> datetime | None:
    """Parsing défensif — gère aussi bien une date absente qu'un type inattendu."""
    if not date_str or not isinstance(date_str, str):
        return None
    try:
        return datetime.fromisoformat(date_str)
    except (ValueError, TypeError):
        return None


def separer_recentes_obsoletes(historique: list, jours_max: int = JOURS_RETENTION_MAX) -> tuple[list, list]:
    """Sépare l'historique en (offres récentes, offres obsolètes) selon la
    date d'ajout. Une date absente/invalide est traitée comme récente,
    pour ne jamais purger par erreur une offre mal datée."""
    limite = datetime.now() - timedelta(days=jours_max)
    recentes, obsoletes = [], []

    for item in historique:
        dt = _parser_date(item.get("date_ajout"))
        if dt is None or dt >= limite:
            recentes.append(item)
        else:
            obsoletes.append(item)

    return recentes, obsoletes


def purger_historique(jours_max: int = JOURS_RETENTION_MAX, chemin: str = CHEMIN_HISTORIQUE) -> list:
    """Charge, purge et retourne l'historique nettoyé (ne sauvegarde pas —
    laisse l'appelant décider quand persister)."""
    historique = charger_historique(chemin)
    recentes, obsoletes = separer_recentes_obsoletes(historique, jours_max)
    if obsoletes:
        print(f"🧹 Purge automatique : {len(obsoletes)} offre(s) de plus de {jours_max} jours supprimée(s).")
    return recentes


def formater_date_affichage(date_str) -> str:
    dt = _parser_date(date_str)
    return dt.strftime("%d/%m/%Y à %H:%M") if dt else "Date inconnue"
