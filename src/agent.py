import json
import time
import os
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL_REDACTION = "llama-3.3-70b-versatile"
MODEL_LEGER = "llama-3.1-8b-instant"

SCORE_REGENERATION_SEUIL = 7
MAX_RETRIES_API = 2


def _appel_groq(messages: list, model: str, temperature: float, max_tokens: int, json_mode: bool = True):
    """Centralise l'appel à l'API Groq avec gestion des erreurs et retries."""
    kwargs = {
        "messages": messages,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
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
                time.sleep(2 * tentative)

    raise derniere_erreur


def _extraire_et_matcher(offre: dict, cv_texte: str, portfolio_texte: str, github_texte: str) -> dict:
    """Analyse dynamiquement l'offre et sélectionne les projets/compétences les plus pertinents."""
    prompt = f"""
    Tu es un Lead Data Scientist et Recruteur Senior.
    Analyse l'offre d'emploi ci-dessous et effectue un matching stratégique avec le dossier du candidat.

    OFFRE D'EMPLOI :
    Titre : {offre.get('title')}
    Entreprise : {offre.get('company')}
    Description : {offre.get('description', '')[:3500]}

    DOSSIER DU CANDIDAT :
    [CV] : {cv_texte[:2500]}
    [PORTFOLIO] : {portfolio_texte[:1500]}
    [GITHUB] : {github_texte[:2000]}

    TÂCHES :
    1. Identifie l'enjeu business et technique majeur de l'entreprise sur ce poste.
    2. Sélectionne les 2 PROJETS du candidat dont l'architecture, la méthodologie ou le résultat répondent le plus directement à cet enjeu.
    3. Identifie 3 COMPÉTENCES CLÉS (hard + soft skills/méthodes) que le candidat pourra immédiatement mettre au service de l'entreprise.

    Réponds UNIQUEMENT sous forme de JSON strict :
    {{
      "secteur_enjeu": "Explication de l'enjeu stratégique de l'entreprise",
      "mots_cles_metier": ["mots", "techniques", "et", "métier"],
      "projets_selectionnes": [
        {{
          "nom": "Nom du projet 1",
          "technos_cles": "Outils, algos, frameworks utilisés",
          "pourquoi_pertinent": "En quoi la résolution de ce projet prouve la capacité à réussir chez l'employeur"
        }},
        {{
          "nom": "Nom du projet 2",
          "technos_cles": "Outils, algos, frameworks utilisés",
          "pourquoi_pertinent": "En quoi la résolution de ce projet prouve la capacité à réussir chez l'employeur"
        }}
      ],
      "competences_a_apporter": [
        "Compétence 1 et son application concrète pour l'entreprise",
        "Compétence 2 et son application concrète pour l'entreprise",
        "Compétence 3 et son application concrète pour l'entreprise"
      ],
      "score_adequation": 85,
      "points_forts": ["Point fort 1", "Point fort 2"]
    }}
    """
    try:
        r = _appel_groq(
            messages=[{"role": "user", "content": prompt}],
            model=MODEL_LEGER,
            temperature=0.2,
            max_tokens=900,
            json_mode=True
        )
        return json.loads(r.choices[0].message.content)
    except Exception as e:
        print(f"⚠️ Erreur extraction & matching : {e}")
        return {
            "secteur_enjeu": "Analyse d'offre non disponible",
            "mots_cles_metier": [],
            "projets_selectionnes": [],
            "competences_a_apporter": [],
            "score_adequation": 50,
            "points_forts": []
        }


def _rediger_lettre_adaptee(offre: dict, cv_texte: str, analyse_matching: dict, retour_critique: str = None) -> str:
    """Rédige la lettre de motivation sur-mesure avec un style fluide et pragmatique."""
    projets_list = analyse_matching.get("projets_selectionnes", [])
    projets_str = ""
    for p in projets_list:
        if isinstance(p, dict):
            projets_str += f"- **{p.get('nom')}** ({p.get('technos_cles')}) : {p.get('pourquoi_pertinent')}\n"

    competences_str = "\n".join([f"- {c}" for c in analyse_matching.get("competences_a_apporter", [])])

    system_prompt = f"""
    Tu es un ingénieur/candidat Data Science / IA de niveau Master 2.
    Tu rédiges une LETTRE DE MOTIVATION ULTRA-PERSONNALISÉE, NATURELLE ET CONVAINCANTE pour postuler chez {offre.get('company')}.

    CADRE DE RÉDACTION :
    - ENTREPRISE : {offre.get('company')}
    - INTITULÉ DU POSTE : {offre.get('title')}
    - ENJEU PRINCIPAL : {analyse_matching.get('secteur_enjeu')}

    ÉLÉMENTS À VALORISER DANS LE CORPS DE LA LETTRE :
    Projets sélectionnés pour l'entreprise :
    {projets_str}

    Compétences et valeur ajoutée directe :
    {competences_str}

    DIRECTIVES DU STYLE HUMAIN & STRUCTURE :
    1. **Accroche ciblée (VOUS) :** Montre d'emblée que tu as compris les enjeux actuels de {offre.get('company')} (pas de généralités platoniciennes).
    2. **Preuve par le projet (MOI) :** Expose les 2 projets sélectionnés en expliquant le "bien-fondé" de chacun. Explique la problématique initiale, les choix techniques faits et les résultats obtenus pour démontrer ta rigueur opérationnelle.
    3. **Valeur ajoutée (NOUS) :** Rédige un paragraphe dédié où tu détailles ce que tu apporteras concrètement aux équipes de {offre.get('company')} dès ton arrivée (méthodologie, autonomie, stack technique, vision métier).
    4. **Conclusion :** Demande d'échange technique directe et formule de politesse sobre et professionnelle.

    INTERDICTIONS STRICTES (ANTI-ROBOT & ANTI-LLM) :
    - Bannis absolument : "Je soussigné", "C'est avec un grand enthousiasme", "Je suis convaincu d'être le candidat idéal", "Atout précieux pour votre équipe", "Passionné depuis mon plus jeune âge".
    - Ne fais pas un simple catalogue du CV : fais du STORYTELLING TECHNIQUE.
    - Écris en Français parfait, fluide et direct.
    """

    if retour_critique:
        system_prompt += f"\n\n⚠️ REVISION REQUISE : Corrige les défauts identifiés : {retour_critique}"

    user_prompt = f"""
    DESCRIPTION DE L'OFFRE :
    {offre.get('description', '')[:3000]}

    Rédige la lettre complète prête à envoyer.
    """

    r = _appel_groq(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        model=MODEL_REDACTION,
        temperature=0.35,
        max_tokens=2500,
        json_mode=False
    )
    return r.choices[0].message.content.strip()


def _critiquer_lettre(lettre: str, offre: dict, analyse_matching: dict) -> dict:
    """Étape de contrôle qualité pour garantir le ton humain et la précision technique."""
    if not lettre:
        return {"score": 0, "justification": "Lettre vide."}

    prompt = f"""
    Tu es un réviseur de candidatures ultra-strict.
    Évalue le ton et la pertinence de cette lettre pour le poste '{offre.get('title')}' chez '{offre.get('company')}'.

    CRITÈRES STRICTS :
    1. Ton humain et naturel : Est-ce que cela ressemble à une vraie lettre rédigée par un ingénieur compétent, ou à du texte généré par IA ? (Formules pompeuses = Note < 7).
    2. Justification des projets : Les projets sont-ils bien explicités avec leur bien-fondé par rapport au besoin de l'entreprise ?
    3. Apport de compétences : La lettre détaille-t-elle la valeur ajoutée concrète pour l'équipe ?

    LETTRE :
    {lettre[:3000]}

    Réponds UNIQUEMENT en JSON strict :
    {{
      "score": <note sur 10>,
      "justification": "Raison courte si la note est < 8"
    }}
    """
    try:
        r = _appel_groq(
            messages=[{"role": "user", "content": prompt}],
            model=MODEL_LEGER,
            temperature=0,
            max_tokens=200,
            json_mode=True
        )
        res = json.loads(r.choices[0].message.content)
        return {"score": int(res.get("score", 10)), "justification": str(res.get("justification", ""))}
    except Exception as e:
        print(f"⚠️ Erreur critique lettre : {e}")
        return {"score": 10, "justification": "Contrôle indisponible"}


def analyser_et_rediger(offre: dict, cv_texte_ou_contexte, portfolio_texte: str = "", github_texte: str = "") -> dict:
    """Pipeline d'analyse, de matching et de rédaction dynamique."""
    try:
        if isinstance(cv_texte_ou_contexte, dict):
            cv_texte = cv_texte_ou_contexte.get("cv", "")
            portfolio_texte = cv_texte_ou_contexte.get("portfolio", "")
            github_texte = str(cv_texte_ou_contexte.get("github", ""))
        else:
            cv_texte = cv_texte_ou_contexte

        print(f"🔍 Analyse & Storytelling pour : {offre.get('title')} chez {offre.get('company')}...")

        matching = _extraire_et_matcher(offre, cv_texte, portfolio_texte, github_texte)
        lettre = _rediger_lettre_adaptee(offre, cv_texte, matching)
        critique = _critiquer_lettre(lettre, offre, matching)

        if critique["score"] < SCORE_REGENERATION_SEUIL:
            print(f"  ⚠️ Réajustement du style ({critique['score']}/10 : {critique['justification']})...")
            lettre = _rediger_lettre_adaptee(
                offre, cv_texte, matching, retour_critique=critique["justification"]
            )

        nb_mots = len(lettre.split())
        print(f"✅ Lettre rédigée ({nb_mots} mots). Score adéquation : {matching.get('score_adequation', 0)}%")

        projets_retenus = [p.get("nom", "") for p in matching.get("projets_selectionnes", []) if isinstance(p, dict)]

        return {
            "score_adequation": int(matching.get("score_adequation", 0)),
            "besoin_cle_entreprise": str(matching.get("secteur_enjeu", "")),
            "preuve_technique_citee": ", ".join(projets_retenus),
            "points_forts": matching.get("points_forts", []),
            "lettre_motivation": lettre
        }

    except Exception as e:
        print(f"⚠️ Erreur globale agent : {e}")
        return {
            "score_adequation": 0,
            "besoin_cle_entreprise": "Erreur d'analyse",
            "preuve_technique_citee": "Aucune",
            "points_forts": [],
            "lettre_motivation": "Génération de la lettre impossible."
        }
