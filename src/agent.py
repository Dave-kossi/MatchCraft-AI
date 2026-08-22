import json
import os
import time
from typing import Any, Dict, List, Optional

from groq import Groq


# ============================================================
# CONFIGURATION
# ============================================================

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


class ErreurTechniqueMatchCraft(Exception):
    """
    Levée quand analyser_et_rediger échoue pour une raison technique (API Groq
    indisponible après retries, JSON malformé...) — PAS pour un rejet qualité
    légitime (hallucination, score insuffisant), qui reste un `return None` normal.
    main.py doit attraper spécifiquement cette exception pour éviter de mettre
    l'offre en cache de rejet permanent suite à un problème transitoire.
    """
    pass

MODEL_LEGER = "qwen/qwen3.6-27b"       # analyse offre, fact-check, critique — reasoning_effort="none" (off complet)
MODEL_REDACTION = "openai/gpt-oss-120b"  # matching + rédaction — bénéficient du raisonnement, reasoning_effort="low"

# Répartir le pipeline sur 2 modèles distincts au lieu d'un seul exploite le fait
# que Groq applique un quota (RPM/RPD/TPM) SÉPARÉ par modèle. Avec 5 appels/offre
# sur un seul modèle, on tape un seul quota ~5x plus vite. En scindant 3 appels
# structurés (Qwen, reasoning="none", zéro coût de raisonnement) et 2 appels qui
# ont vraiment besoin de jugement (gpt-oss-120b, reasoning="low"), chaque modèle
# absorbe moins de charge sur son propre quota. Les chiffres exacts de quota
# évoluent régulièrement chez Groq — vérifier console.groq.com/settings/limits
# plutôt que de se fier à un chiffre figé en dur ici.

SCORE_REGENERATION_SEUIL = 7
SCORE_MINIMUM_VALIDATION = 7

MAX_RETRIES_API = 3
RETRY_BASE_DELAY = 2

MAX_OFFRE_CHARS = 6000
MAX_CV_CHARS = 5000
MAX_PORTFOLIO_CHARS = 6000
MAX_GITHUB_CHARS = 6000


# ============================================================
# OUTILS GÉNÉRIQUES
# ============================================================

def _nettoyer_texte(texte: Optional[str]) -> str:
    if not texte:
        return ""
    return str(texte).replace("\x00", " ").strip()


def _json_valide(contenu: str) -> Dict[str, Any]:
    if not contenu:
        raise ValueError("Réponse LLM vide.")
    try:
        return json.loads(contenu)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON invalide retourné par le modèle : {e}")


def _appel_groq(
    messages: List[Dict[str, str]],
    model: str,
    temperature: float,
    max_tokens: int,
    json_mode: bool = True,
    reasoning_effort: str = "low",
):
    """
    Centralise tous les appels Groq — retry automatique, backoff progressif, JSON strict si demandé.

    reasoning_effort : openai/gpt-oss-* n'accepte que low/medium/high (pas de vrai
    "off" — on utilise "low" pour ces appels). qwen/qwen3.6-27b accepte "none" pour
    désactiver complètement le raisonnement — utilisé pour les 3 étapes purement
    structurées (analyse offre, fact-check, critique) qui n'ont pas besoin de
    chaîne de raisonnement. Sans ce contrôle, le raisonnement interne peut épuiser
    tout le budget max_tokens avant que le JSON final ne soit généré → erreur Groq
    "max completion tokens reached before generating a valid document" / failed_generation
    vide. Chaque appelant passe la valeur adaptée à son modèle — voir chaque fonction.
    reasoning_format="hidden" retire le raisonnement du contenu retourné (recommandé
    par Groq en mode JSON — seuls "hidden" et "parsed" sont supportés avec response_format).
    """
    kwargs = {
        "messages": messages,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "reasoning_effort": reasoning_effort,
        "reasoning_format": "hidden",
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    derniere_erreur = None
    for tentative in range(1, MAX_RETRIES_API + 1):
        try:
            return client.chat.completions.create(**kwargs)
        except Exception as e:
            derniere_erreur = e
            print(f"⚠️ Erreur Groq (tentative {tentative}/{MAX_RETRIES_API}) : {e}")
            if tentative < MAX_RETRIES_API:
                time.sleep(RETRY_BASE_DELAY * tentative)

    raise RuntimeError(f"Échec définitif de l'appel Groq après {MAX_RETRIES_API} tentatives.") from derniere_erreur


# ============================================================
# 1. ANALYSE DE L'OFFRE
# ============================================================

def _analyser_offre(offre: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyse uniquement l'offre : missions, compétences, technologies, mots-clés.
    Aucun matching candidat n'est effectué ici.

    Chaque besoin reçoit un "id" numérique stable — c'est CET id, et non une
    reformulation du texte, qui sera réutilisé à l'étape de matching. Ça évite
    qu'une paraphrase du LLM entre deux appels fasse échouer silencieusement
    le calcul du score (cf. version précédente, qui comparait des sous-chaînes
    de texte entre deux appels LLM indépendants — fragile).
    """
    description = _nettoyer_texte(offre.get("description", ""))[:MAX_OFFRE_CHARS]

    prompt = f"""
Tu es un expert en recrutement technique et en analyse d'offres
Data Science, IA, Machine Learning et Software Engineering.

Analyse UNIQUEMENT l'offre ci-dessous.

OFFRE
-----
Titre :
{offre.get("title", "")}

Entreprise :
{offre.get("company", "")}

Description :
{description}

OBJECTIF

Extrais les besoins réels de l'entreprise sans inventer d'informations.

Pour chaque besoin important, assigne-lui un "id" numérique séquentiel
commençant à 0 (0, 1, 2...). Cet id sera réutilisé tel quel à l'étape
suivante — ne le change jamais et ne le confonds pas avec un autre besoin.

Pour chaque besoin :
1. Reprends fidèlement le besoin exprimé dans l'offre.
2. Identifie son type : mission / compétence / technologie / soft_skill / formation / autre
3. Évalue son importance : high / medium / low
4. Identifie les mots-clés métier réellement présents.

IMPORTANT :
- Ne transforme pas une information générique en exigence.
- Ne suppose aucune technologie absente de l'offre.
- Ne complète pas l'offre avec tes connaissances générales.
- Les éléments doivent être traçables au texte fourni.

Réponds UNIQUEMENT en JSON valide.

FORMAT :

{{
  "poste": "...",
  "entreprise": "...",
  "secteur": "...",
  "enjeu_principal": "...",

  "besoins": [
    {{
      "id": 0,
      "texte": "...",
      "type": "mission",
      "importance": "high"
    }}
  ],

  "technologies": ["Python", "SQL"],
  "mots_cles_metier": ["mot-clé 1", "mot-clé 2"],
  "niveau_recherche": "...",
  "type_contrat": "stage / alternance / emploi / inconnu"
}}
"""

    response = _appel_groq(
        messages=[
            {"role": "system", "content": "Tu es un analyste d'offres rigoureux. Tu n'inventes aucune information."},
            {"role": "user", "content": prompt},
        ],
        model=MODEL_LEGER,
        temperature=0.1,
        max_tokens=2200,
        json_mode=True,
        reasoning_effort="none",
    )

    resultat = _json_valide(response.choices[0].message.content)

    # Garde-fou : si le modèle a oublié un id ou l'a mal typé, on le régénère
    # nous-mêmes par position plutôt que de laisser le matching échouer plus tard.
    for i, besoin in enumerate(resultat.get("besoins", [])):
        if not isinstance(besoin.get("id"), int):
            besoin["id"] = i

    return resultat


# ============================================================
# 2. MATCHING CANDIDAT / OFFRE
# ============================================================

def _matcher_candidat(
    analyse_offre: Dict[str, Any],
    cv_texte: str,
    portfolio_texte: str,
    github_texte: str,
) -> Dict[str, Any]:
    """
    Analyse la correspondance entre les besoins de l'entreprise (identifiés
    par leur id, pas leur texte) et les preuves réelles disponibles dans le
    dossier candidat. Cette étape ne rédige PAS la lettre.
    """
    cv = _nettoyer_texte(cv_texte)[:MAX_CV_CHARS]
    portfolio = _nettoyer_texte(portfolio_texte)[:MAX_PORTFOLIO_CHARS]
    github = _nettoyer_texte(github_texte)[:MAX_GITHUB_CHARS]

    besoins = json.dumps(analyse_offre.get("besoins", []), ensure_ascii=False, indent=2)

    prompt = f"""
Tu es un expert senior en recrutement Data Science / IA.

Ta mission est de déterminer objectivement la correspondance entre une
offre et le dossier réel d'un candidat.

OFFRE ANALYSÉE
==============

Entreprise : {analyse_offre.get("entreprise", "")}
Poste : {analyse_offre.get("poste", "")}

Besoins (chacun a un "id" — RÉUTILISE cet id exact dans ta réponse,
ne reformule jamais le texte du besoin) :
{besoins}

Technologies :
{json.dumps(analyse_offre.get("technologies", []), ensure_ascii=False)}

DOSSIER CANDIDAT
================

[CV]
{cv}

[PORTFOLIO]
{portfolio}

[GITHUB]
{github}

RÈGLES ABSOLUES

1. Tu ne peux utiliser qu'une information réellement présente dans les documents candidat.
2. Une technologie n'est considérée comme maîtrisée que si elle apparaît explicitement dans les sources.
3. Une métrique ne peut être utilisée que si elle apparaît explicitement dans les sources.
4. Ne transforme jamais une compétence supposée en expérience.
5. Si aucune preuve ne correspond à un besoin, indique "aucune_preuve".
6. Distingue : preuve forte / preuve partielle / compétence transférable / absence de preuve.
7. Le matching doit être basé sur les besoins précis de l'offre, pas uniquement sur le domaine général.
8. Identifie les deux projets les plus pertinents maximum.
9. Le facteur différenciant doit être basé sur un fait vérifiable.
10. Ne rédige aucune lettre à cette étape.
11. Pour chaque correspondance, indique "besoin_id" (l'entier exact fourni ci-dessus) — JAMAIS "besoin" en texte libre.

FORMAT JSON STRICT :

{{
  "correspondances": [
    {{
      "besoin_id": 0,
      "niveau_correspondance": "forte",
      "preuve": "...",
      "source": "CV / Portfolio / GitHub",
      "projet": "..."
    }}
  ],

  "projets_selectionnes": [
    {{
      "nom": "...",
      "description_factuelle": "...",
      "technologies": [],
      "metriques": [],
      "sources": [],
      "besoins_couverts": [],
      "niveau_preuve": "forte"
    }}
  ],

  "facteur_differenciant": "...",
  "points_forts": [],
  "gaps": [],
  "competences_transferables": []
}}
"""

    response = _appel_groq(
        messages=[
            {
                "role": "system",
                "content": "Tu es un évaluateur de candidature extrêmement factuel. Toute affirmation doit être soutenue par une preuve présente dans les documents.",
            },
            {"role": "user", "content": prompt},
        ],
        model=MODEL_REDACTION,
        temperature=0.1,
        max_tokens=3000,
        json_mode=True,
        reasoning_effort="low",
    )

    return _json_valide(response.choices[0].message.content)


# ============================================================
# 3. CALCUL DU SCORE D'ADEQUATION (côté Python — jamais inventé par le LLM)
# ============================================================

def _calculer_score_adequation(analyse_offre: Dict[str, Any], matching: Dict[str, Any]) -> int:
    """
    Calcule le score en Python à partir des jugements qualitatifs du LLM.
    Le matching besoin ↔ correspondance se fait par ID, pas par comparaison
    de texte — fiable même si les deux appels LLM ne formulent pas le besoin
    à l'identique.
    """
    poids = {"high": 5, "medium": 3, "low": 1}
    correspondances = {"forte": 5, "partielle": 3, "transferable": 2, "faible": 1, "aucune_preuve": 0}

    besoins = analyse_offre.get("besoins", [])
    resultats = matching.get("correspondances", [])

    if not besoins:
        return 0

    resultats_par_id: Dict[int, List[Dict[str, Any]]] = {}
    for resultat in resultats:
        bid = resultat.get("besoin_id")
        if isinstance(bid, int):
            resultats_par_id.setdefault(bid, []).append(resultat)

    score_total = 0
    score_max = 0

    for besoin in besoins:
        importance = besoin.get("importance", "medium")
        poids_besoin = poids.get(importance, 3)
        besoin_id = besoin.get("id")

        score_max += poids_besoin * 5

        meilleure_correspondance = 0
        for resultat in resultats_par_id.get(besoin_id, []):
            niveau = resultat.get("niveau_correspondance", "aucune_preuve")
            meilleure_correspondance = max(meilleure_correspondance, correspondances.get(niveau, 0))

        score_total += poids_besoin * meilleure_correspondance

    if score_max == 0:
        return 0

    return round((score_total / score_max) * 100)


# ============================================================
# 4. CONSTRUCTION DE L'EVIDENCE PACK
# ============================================================

def _construire_evidence_pack(analyse_offre: Dict[str, Any], matching: Dict[str, Any]) -> Dict[str, Any]:
    """
    Contexte minimal et déjà vérifié que le rédacteur est autorisé à utiliser.
    Le rédacteur ne reçoit jamais le CV/portfolio/GitHub bruts — seulement
    ce qui a déjà été validé à l'étape de matching. C'est le vrai garde-fou
    anti-hallucination : structurel, pas juste une instruction de prompt.
    """
    return {
        "entreprise": analyse_offre.get("entreprise", ""),
        "poste": analyse_offre.get("poste", ""),
        "enjeu_principal": analyse_offre.get("enjeu_principal", ""),
        "besoins": analyse_offre.get("besoins", []),
        "mots_cles_metier": analyse_offre.get("mots_cles_metier", []),
        "correspondances": matching.get("correspondances", []),
        "projets_selectionnes": matching.get("projets_selectionnes", []),
        "facteur_differenciant": matching.get("facteur_differenciant", ""),
        "points_forts": matching.get("points_forts", []),
        "gaps": matching.get("gaps", []),
        "competences_transferables": matching.get("competences_transferables", []),
    }


# ============================================================
# 5. RÉDACTION DE LA LETTRE
# ============================================================

def _rediger_lettre(offre: Dict[str, Any], evidence_pack: Dict[str, Any], retour_critique: Optional[str] = None) -> str:
    """Génère la lettre à partir de l'Evidence Pack. Le modèle n'a pas le droit d'inventer une nouvelle preuve."""
    evidence = json.dumps(evidence_pack, ensure_ascii=False, indent=2)
    description_offre = _nettoyer_texte(offre.get("description", ""))[:MAX_OFFRE_CHARS]

    revision = ""
    if retour_critique:
        revision = f"""
RÉVISION OBLIGATOIRE

La précédente lettre a été critiquée pour :
{retour_critique}

Corrige précisément ces problèmes. Ne crée aucune nouvelle information.
"""

    system_prompt = f"""
Tu es un rédacteur expert en candidatures Data Science, Machine Learning
et Intelligence Artificielle.

Tu rédiges une lettre de motivation professionnelle, naturelle, spécifique
à l'entreprise et fondée uniquement sur des preuves vérifiées.

POSTURE : Un recruteur reçoit des centaines de candidatures pour cette offre.
Chaque phrase doit répondre implicitement à "pourquoi ce candidat plutôt
qu'un autre profil Data/IA de même niveau" — via des faits précis de
l'Evidence Pack, jamais via des superlatifs.

ENTREPRISE : {offre.get("company", "")}
POSTE : {offre.get("title", "")}

EVIDENCE PACK AUTORISÉ :
{evidence}

RÈGLES ABSOLUES

1. N'invente aucune expérience.
2. N'invente aucune technologie.
3. N'invente aucune métrique.
4. N'invente aucune responsabilité exercée par le candidat.
5. Utilise uniquement les projets présents dans "projets_selectionnes".
6. Si une compétence demandée n'a pas de preuve directe, utilise uniquement
   une compétence transférable réellement présente dans "competences_transferables".
7. Ne prétends jamais que le candidat maîtrise une technologie simplement
   parce qu'elle est demandée dans l'offre.
8. Ne dis jamais "je suis le candidat idéal".
9. Évite : "je suis convaincu que", "passionné depuis toujours", "dynamique
   et motivé", "atout pour votre équipe", "excellent candidat", "correspond parfaitement".
10. La différenciation ("facteur_differenciant") doit apparaître à travers
    les faits eux-mêmes, jamais être proclamée directement.
11. Le vocabulaire métier de l'entreprise doit être utilisé naturellement.
12. La lettre doit rester humaine, pas un rapport technique.
13. Varie la formulation de l'accroche d'une lettre à l'autre — évite les
    tournures d'ouverture répétitives type "correspond exactement à la mission de X".

STRUCTURE
- Objet
- Accroche contextualisée
- Pourquoi cette entreprise / ce poste
- Deux preuves concrètes maximum
- Correspondance avec les missions
- Projection
- Demande d'entretien
- Formule de politesse

FORMAT
Texte brut uniquement. Pas de JSON. Pas de Markdown. Pas de titre "Lettre de motivation".

LONGUEUR
Environ 350 à 500 mots.

{revision}
"""

    user_prompt = f"""
DESCRIPTION DE L'OFFRE :
{description_offre}

Rédige maintenant la lettre.
"""

    response = _appel_groq(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        model=MODEL_REDACTION,
        temperature=0.35,
        max_tokens=2600,
        json_mode=False,
        reasoning_effort="low",
    )

    lettre = response.choices[0].message.content
    if not lettre:
        raise ValueError("Le modèle n'a retourné aucune lettre.")

    return lettre.strip()


# ============================================================
# 6. CONTRÔLE FACTUEL
# ============================================================

def _verifier_faits(lettre: str, evidence_pack: Dict[str, Any]) -> Dict[str, Any]:
    """Vérifie que la lettre ne contient aucun fait absent de l'Evidence Pack."""
    evidence = json.dumps(evidence_pack, ensure_ascii=False, indent=2)

    prompt = f"""
Tu es un fact-checker extrêmement strict.

Compare la lettre avec l'Evidence Pack.

EVIDENCE PACK
=============
{evidence}

LETTRE
======
{lettre}

Vérifie : technologies citées, projets cités, métriques citées, expériences
citées, réalisations, responsabilités, toute affirmation factuelle.

Une information non explicitement soutenue par l'Evidence Pack doit être
considérée comme non vérifiée.

Réponds UNIQUEMENT en JSON :
{{
  "fidelite_factuelle_ok": true,
  "faits_non_verifies": [],
  "score_fidelite": 10,
  "justification": "..."
}}
"""

    response = _appel_groq(
        messages=[
            {
                "role": "system",
                "content": "Tu ne dois jamais supposer qu'une affirmation est vraie. Si elle n'est pas démontrée dans l'Evidence Pack, elle est non vérifiée.",
            },
            {"role": "user", "content": prompt},
        ],
        model=MODEL_LEGER,
        temperature=0,
        max_tokens=1500,
        json_mode=True,
        reasoning_effort="none",
    )

    resultat = _json_valide(response.choices[0].message.content)

    fidelite = resultat.get("fidelite_factuelle_ok")
    if not isinstance(fidelite, bool):
        raise ValueError("fidelite_factuelle_ok doit être un booléen JSON.")

    try:
        score = int(resultat.get("score_fidelite", 0))
    except (TypeError, ValueError):
        score = 0
    score = max(0, min(10, score))

    return {
        "fidelite_factuelle_ok": fidelite,
        "faits_non_verifies": resultat.get("faits_non_verifies", []),
        "score_fidelite": score,
        "justification": str(resultat.get("justification", "")),
    }


# ============================================================
# 7. CRITIQUE QUALITATIVE
# ============================================================

def _critiquer_lettre(lettre: str, offre: Dict[str, Any], evidence_pack: Dict[str, Any]) -> Dict[str, Any]:
    """Critique la qualité : personnalisation, adéquation, clarté, différenciation, style."""
    evidence = json.dumps(evidence_pack, ensure_ascii=False, indent=2)

    prompt = f"""
Tu es un recruteur senior spécialisé en Data Science et IA.

OFFRE :
Entreprise : {offre.get("company")}
Poste : {offre.get("title")}

EVIDENCE PACK :
{evidence}

LETTRE :
{lettre}

Évalue la lettre sur 10.

CRITÈRES :
1. Adéquation avec l'offre
2. Personnalisation
3. Pertinence des projets
4. Pouvoir différenciant
5. Clarté
6. Ton professionnel
7. Absence de phrases creuses
8. Absence de répétitions
9. Capacité à donner envie d'un entretien

Ne pénalise pas une lettre parce qu'elle ne prétend pas maîtriser une
technologie qui n'est pas prouvée.

Réponds UNIQUEMENT en JSON :
{{
  "score": 0,
  "adequation_ok": true,
  "differenciation_suffisante": true,
  "style_ok": true,
  "justification": "...",
  "points_a_corriger": []
}}
"""

    response = _appel_groq(
        messages=[
            {"role": "system", "content": "Tu es un critique de lettres de motivation exigeant mais objectif."},
            {"role": "user", "content": prompt},
        ],
        model=MODEL_LEGER,
        temperature=0,
        max_tokens=1500,
        json_mode=True,
        reasoning_effort="none",
    )

    resultat = _json_valide(response.choices[0].message.content)

    try:
        score = int(resultat.get("score", 0))
    except (TypeError, ValueError):
        score = 0
    score = max(0, min(10, score))

    return {
        "score": score,
        "adequation_ok": resultat.get("adequation_ok", False),
        "differenciation_suffisante": resultat.get("differenciation_suffisante", False),
        "style_ok": resultat.get("style_ok", False),
        "justification": str(resultat.get("justification", "")),
        "points_a_corriger": resultat.get("points_a_corriger", []),
    }


# ============================================================
# 8. PIPELINE PRINCIPAL
# ============================================================

def analyser_et_rediger(
    offre: Dict[str, Any],
    cv_texte: str,
    portfolio_texte: str,
    github_texte: str,
) -> Optional[Dict[str, Any]]:
    """
    Pipeline MatchCraft AI :
    OFFRE → ANALYSE → MATCHING (par besoin_id) → SCORE PYTHON → EVIDENCE PACK
          → REDACTION → FACT CHECK → CRITIQUE → REGENERATION éventuelle → RESULTAT
    """
    try:
        print(f"🔍 MatchCraft AI — {offre.get('title')} chez {offre.get('company')}")

        print("  1️⃣ Analyse de l'offre...")
        analyse_offre = _analyser_offre(offre)

        print("  2️⃣ Matching candidat/offre...")
        matching = _matcher_candidat(analyse_offre, cv_texte, portfolio_texte, github_texte)

        score_adequation = _calculer_score_adequation(analyse_offre, matching)
        print(f"  📊 Score d'adéquation : {score_adequation}/100")

        evidence_pack = _construire_evidence_pack(analyse_offre, matching)

        print("  3️⃣ Rédaction de la lettre...")
        lettre = _rediger_lettre(offre, evidence_pack)

        print("  4️⃣ Vérification factuelle...")
        verification = _verifier_faits(lettre, evidence_pack)

        print("  5️⃣ Critique qualitative...")
        critique = _critiquer_lettre(lettre, offre, evidence_pack)

        besoin_regeneration = (
            verification["score_fidelite"] < SCORE_MINIMUM_VALIDATION
            or not verification["fidelite_factuelle_ok"]
            or critique["score"] < SCORE_REGENERATION_SEUIL
        )

        if besoin_regeneration:
            print("  ⚠️ Lettre nécessitant une correction.")

            motifs = []
            if not verification["fidelite_factuelle_ok"]:
                motifs.append("FAITS NON VÉRIFIÉS : " + json.dumps(verification.get("faits_non_verifies", []), ensure_ascii=False))
            if verification.get("justification"):
                motifs.append(verification["justification"])
            if critique.get("justification"):
                motifs.append(critique["justification"])
            if critique.get("points_a_corriger"):
                motifs.extend(critique["points_a_corriger"])

            motif_revision = "\n- ".join(motifs)

            print("  🔄 Régénération...")
            lettre = _rediger_lettre(offre, evidence_pack, retour_critique=motif_revision)

            # Second contrôle factuel obligatoire — le contenu a changé, on ne
            # peut pas réutiliser l'ancien verdict.
            verification = _verifier_faits(lettre, evidence_pack)

            if not verification["fidelite_factuelle_ok"]:
                print("  🚫 Hallucination persistante après régénération.")
                return None

            # La critique qualitative est re-jouée aussi, car le contenu a pu
            # changer significativement (une lettre corrigée pour un problème
            # factuel n'a pas nécessairement le même score de différenciation
            # ou de style que l'originale) — réutiliser l'ancien score serait
            # source d'incohérence entre le score affiché et la lettre livrée.
            critique = _critiquer_lettre(lettre, offre, evidence_pack)

        if not verification["fidelite_factuelle_ok"]:
            print("  🚫 Lettre rejetée : contrôle factuel négatif.")
            return None

        if verification["score_fidelite"] < SCORE_MINIMUM_VALIDATION:
            print("  🚫 Lettre rejetée : fidélité insuffisante.")
            return None

        nb_mots = len(lettre.split())
        print(f"  ✅ Lettre validée ({nb_mots} mots)")

        projets = matching.get("projets_selectionnes", [])

        return {
            # Identification
            "entreprise": offre.get("company", ""),
            "poste": offre.get("title", ""),

            # Matching
            "score_adequation": score_adequation,
            "enjeu_principal": analyse_offre.get("enjeu_principal", ""),
            "besoins_entreprise": analyse_offre.get("besoins", []),

            # Preuves
            "projets_selectionnes": projets,
            "points_forts": matching.get("points_forts", []),
            "gaps": matching.get("gaps", []),
            "facteur_differenciant": matching.get("facteur_differenciant", ""),

            # Contrôle qualité
            "score_fidelite": verification.get("score_fidelite", 0),
            "score_lettre": critique.get("score", 0),
            "validation_factuelle": verification.get("fidelite_factuelle_ok", False),

            # Lettre finale
            "lettre_motivation": lettre,
            "nb_mots": nb_mots,

            # Métadonnées
            "modele_analyse": MODEL_LEGER,
            "modele_matching": MODEL_REDACTION,
            "modele_redaction": MODEL_REDACTION,

            # --- Alias de compatibilité avec l'ancien schéma (utilisés par app.py) ---
            # Évite que le dashboard affiche silencieusement "N/A" sur ces deux champs
            # tant qu'app.py n'a pas été mis à jour pour lire le nouveau schéma enrichi.
            "besoin_cle_entreprise": analyse_offre.get("enjeu_principal", ""),
            "preuve_technique_citee": ", ".join(p.get("nom", "") for p in projets),
        }

    except Exception as e:
        print(f"🚨 Erreur globale MatchCraft AI : {e}")
        # IMPORTANT : on NE retourne PAS None ici. Un None est traité par main.py
        # comme un rejet qualité légitime et mis en cache DÉFINITIVEMENT dans
        # data/offres_rejetees.json. Une erreur technique (API Groq indisponible,
        # JSON malformé, rate-limit...) est transitoire — l'offre doit pouvoir être
        # retentée au prochain run, pas bannie pour toujours à cause d'un problème
        # qui n'a rien à voir avec sa pertinence réelle. On propage donc une
        # exception dédiée que main.py peut distinguer d'un rejet normal.
        raise ErreurTechniqueMatchCraft(str(e)) from e
