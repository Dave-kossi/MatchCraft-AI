import base64
import json
import os
import requests

REPO = "Dave-kossi/MatchCraft-AI"
FICHIER = "data/historique.json"
BRANCHE = "main"


def _headers():
    token = os.getenv("GITHUB_TOKEN")
    return {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}


def sauvegarder_historique_sur_github(historique: list, message: str = "Mise à jour statut offres") -> bool:
    """
    Écrit data/historique.json directement sur le repo GitHub via l'API Contents.
    Nécessaire car app.py (Streamlit Cloud) et main.py (GitHub Actions) tournent
    dans des conteneurs séparés — le repo Git est la seule source de vérité commune.
    """
    url = f"https://api.github.com/repos/{REPO}/contents/{FICHIER}"

    r = requests.get(url, headers=_headers(), params={"ref": BRANCHE}, timeout=10)
    sha = r.json().get("sha") if r.status_code == 200 else None

    contenu_json = json.dumps(historique, ensure_ascii=False, indent=2)
    contenu_b64 = base64.b64encode(contenu_json.encode("utf-8")).decode("utf-8")

    payload = {"message": message, "content": contenu_b64, "branch": BRANCHE}
    if sha:
        payload["sha"] = sha

    res = requests.put(url, headers=_headers(), json=payload, timeout=10)
    return res.status_code in (200, 201)
