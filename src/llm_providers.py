# src/llm_providers.py
"""
Couche d'abstraction à 2 fournisseurs pour tous les appels LLM du pipeline
MatchCraft AI (agent.py, cv_agent.py).

Problème résolu : Groq seul a un quota journalier vite atteint (100k
tokens/jour sur le tier gratuit) quand on traite 40+ offres/jour x plusieurs
appels chacune. Ce module essaie Groq en premier, puis bascule
automatiquement sur OpenRouter en cas de rate limit (429) ou d'erreur serveur.

Pourquoi Groq + OpenRouter (et pas Cerebras/Gemini) :
- Aucun des deux n'exige de carte bancaire, y compris pour un compte
  français/UE (Cerebras la demande désormais à l'inscription ; Google AI
  Studio impose d'activer la facturation pour les comptes UE/UK/Suisse même
  sur le tier "gratuit" — les deux sont donc écartés ici)
- Les deux exposent une API compatible OpenAI (un seul client `openai` suffit)
- OpenRouter est utilisé via son routeur automatique "openrouter/free", qui
  sélectionne lui-même un modèle gratuit disponible à l'instant T. Le
  catalogue de modèles :free d'OpenRouter change très souvent (plusieurs
  par semaine) — coder un nom en dur (ex: "meta-llama/llama-3.3-70b-
  instruct:free") casse au bout de quelques semaines. Le routeur auto évite
  ce problème de maintenance.

Limites à connaître :
- OpenRouter free : 20 req/min, 50 req/jour sans crédit ajouté (1000/jour
  si tu ajoutes un jour 10$ de crédit, mais ça redemande une carte)
- Le style de sortie peut varier légèrement d'un appel à l'autre sur
  OpenRouter puisque le modèle réel change selon ce qui est disponible

Variables d'environnement (secrets GitHub Actions) :
    GROQ_API_KEY        -> https://console.groq.com          (obligatoire)
    OPENROUTER_API_KEY  -> https://openrouter.ai/keys         (recommandé, gratuit, sans CB)
"""

import json
import os
import time

from openai import OpenAI, RateLimitError, APIStatusError, APIConnectionError


def _client(base_url: str, api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key, base_url=base_url)


_PROVIDERS = []

if os.getenv("GROQ_API_KEY"):
    _PROVIDERS.append({
        "nom": "Groq",
        "client": _client("https://api.groq.com/openai/v1", os.getenv("GROQ_API_KEY")),
        "modele_leger": "llama-3.1-8b-instant",
        "modele_redaction": "llama-3.3-70b-versatile",
    })

if os.getenv("OPENROUTER_API_KEY"):
    _PROVIDERS.append({
        "nom": "OpenRouter",
        "client": _client("https://openrouter.ai/api/v1", os.getenv("OPENROUTER_API_KEY")),
        # Routeur automatique : choisit lui-même un modèle :free disponible.
        # Évite de coder en dur un ID de modèle qui disparaîtra du catalogue.
        "modele_leger": "openrouter/free",
        "modele_redaction": "openrouter/free",
    })

if not _PROVIDERS:
    raise RuntimeError(
        "Aucune clé API LLM configurée. Définis au moins GROQ_API_KEY "
        "(et idéalement aussi OPENROUTER_API_KEY pour la bascule automatique "
        "en cas de quota atteint)."
    )

print(f"🔌 Fournisseurs LLM actifs (ordre de priorité) : {', '.join(p['nom'] for p in _PROVIDERS)}")


def _appeler_avec_repli(messages: list, taille: str, temperature: float, max_tokens: int, json_mode: bool):
    """
    Essaie Groq puis OpenRouter. Ne bascule que sur des erreurs de
    quota/connexion/serveur — une vraie erreur de contenu (prompt invalide,
    etc.) resterait la même sur les deux fournisseurs de toute façon, donc
    autant réessayer plutôt que d'échouer immédiatement.
    """
    derniere_erreur = None
    for provider in _PROVIDERS:
        modele = provider["modele_leger"] if taille == "leger" else provider["modele_redaction"]
        kwargs = {
            "model": modele,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        try:
            r = provider["client"].chat.completions.create(**kwargs)
            return r.choices[0].message.content
        except (RateLimitError, APIStatusError, APIConnectionError) as e:
            print(f"⚠️ {provider['nom']} indisponible ({e.__class__.__name__}) — bascule sur le fournisseur suivant...")
            derniere_erreur = e
            time.sleep(1)
            continue
    raise derniere_erreur


def appel_json(messages: list, taille: str = "leger", temperature: float = 0.2, max_tokens: int = 900) -> dict:
    """Équivalent JSON pour cv_agent.py."""
    contenu = _appeler_avec_repli(messages, taille=taille, temperature=temperature, max_tokens=max_tokens, json_mode=True)
    return json.loads(contenu)


def appel_texte(messages: list, taille: str = "redaction", temperature: float = 0.3, max_tokens: int = 2500) -> str:
    """Équivalent texte brut (non utilisé directement par agent.py, qui passe par _appeler_avec_repli)."""
    return _appeler_avec_repli(messages, taille=taille, temperature=temperature, max_tokens=max_tokens, json_mode=False)
