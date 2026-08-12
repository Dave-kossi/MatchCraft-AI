import base64
import json
import os
import requests

REPO = "Dave-kossi/MatchCraft-AI"
BRANCHE = "main"


def _headers() -> dict:
    """Génère les en-têtes d'authentification pour l'API GitHub."""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("⚠️ GITHUB_TOKEN introuvable dans les variables d'environnement.")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def sauvegarder_json_sur_github(
    donnees: list | dict,
    chemin_fichier: str = "data/historique.json",
    message_commit: str = "Mise à jour via MatchCraft AI"
) -> bool:
    """
    Écrit un fichier JSON sur le dépôt GitHub via l'API Contents.
    Résout l'isolation de stockage entre Streamlit Cloud et GitHub Actions.
    """
    url = f"https://api.github.com/repos/{REPO}/contents/{chemin_fichier}"

    try:
        # Récupération du SHA courant (requis pour une mise à jour HTTP PUT)
        r = requests.get(url, headers=_headers(), params={"ref": BRANCHE}, timeout=10)
        sha = r.json().get("sha") if r.status_code == 200 else None

        # Conversion en JSON et encodage UTF-8 -> Base64
        contenu_json = json.dumps(donnees, ensure_ascii=False, indent=2)
        contenu_b64 = base64.b64encode(contenu_json.encode("utf-8")).decode("utf-8")

        payload = {
            "message": message_commit,
            "content": contenu_b64,
            "branch": BRANCHE,
        }
        if sha:
            payload["sha"] = sha

        res = requests.put(url, headers=_headers(), json=payload, timeout=10)

        if res.status_code in (200, 201):
            print(f"✅ {chemin_fichier} synchronisé sur GitHub.")
            return True
        else:
            print(f"❌ Échec de synchronisation GitHub ({res.status_code}) : {res.text}")
            return False

    except Exception as e:
        print(f"⚠️ Erreur lors de l'écriture sur GitHub ({chemin_fichier}) : {e}")
        return False


def sauvegarder_historique_sur_github(historique: list, message: str = "Mise à jour historique") -> bool:
    """Alias raccourci pour l'historique d'offres."""
    return sauvegarder_json_sur_github(
        donnees=historique,
        chemin_fichier="data/historique.json",
        message_commit=message
    )
