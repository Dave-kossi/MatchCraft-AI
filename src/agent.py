# src/agent.py
import json
import re

# Import des fonctions d'appel sécurisées avec fallback (Groq + OpenRouter)
from src.llm_providers import appel_json, _appeler_avec_repli

SCORE_REGENERATION_SEUIL = 7


def _nettoyer_et_charger_json(texte_brut: str) -> dict:
    """Nettoie le texte renvoyé par le LLM pour garantir un parsing JSON valide."""
    if not texte_brut:
        return {}
    
    # Suppression des blocs Markdown ```json ... ```
    texte_propre = re.sub(r"^```(?:json)?|```$", "", texte_brut.strip(), flags=re.MULTILINE)
    try:
        return json.loads(texte_propre)
    except json.JSONDecodeError:
        # Tente de trouver le premier '{' et le dernier '}'
        match = re.search(r"\{.*\}", texte_propre, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return {}


def _extraire_et_matcher(offre: dict, cv_texte: str, portfolio_texte: str, github_texte: str) -> dict:
    """
    Étape 1 & 2 : Analyse l'offre et sélectionne
    les projets/compétences les plus pertinents.
    """
    prompt = f"""
    Tu es un Expert Recruteur et Data Scientist.
    Analyse l'offre d'emploi ci-dessous et effectue un matching dynamique avec le profil du candidat.

    OFFRE D'EMPLOI :
    Titre : {offre.get('title')}
    Entreprise : {offre.get('company')}
    Description : {offre.get('description', '')[:3500]}

    DOSSIER COMPLET DU CANDIDAT :
    [CV] : {cv_texte[:2500]}
    [PORTFOLIO] : {portfolio_texte[:1500]}
    [GITHUB] : {github_texte[:2000]}

    TÂCHES :
    1. Identifie le secteur et l'enjeu principal de l'entreprise (ex: détection de fraude, optimisation RAG, Computer Vision, etc.).
    2. Sélectionne les 2 PROJETS du candidat les plus pertinents par rapport à cet enjeu.
    3. Extrais les compétences techniques et le vocabulaire métier exacts à réutiliser dans la lettre.

    Réponds UNIQUEMENT sous forme de JSON strict :
    {{
      "secteur_enjeu": "Description en une phrase de l'enjeu principal de l'offre",
      "mots_cles_metier": ["mot1", "mot2", "mot3", "mot4"],
      "projets_selectionnes": [
        {{
          "nom": "Nom du projet 1",
          "technos_cles": "Technos/méthodes utilisées dans ce projet",
          "pourquoi_pertinent": "Pourquoi ce projet prouve que le candidat peut réussir sur ce poste"
        }},
        {{
          "nom": "Nom du projet 2",
          "technos_cles": "Technos/méthodes utilisées dans ce projet",
          "pourquoi_pertinent": "Pourquoi ce projet prouve que le candidat peut réussir sur ce poste"
        }}
      ],
      "score_adequation": 85,
      "points_forts": ["Point fort 1", "Point fort 2"]
    }}
    """
    messages = [{"role": "user", "content": prompt}]
    
    try:
        # Utilisation du module multi-fournisseurs (modèle léger)
        return appel_json(messages=messages, taille="leger", temperature=0.2, max_tokens=800)
    except Exception as e:
        print(f"⚠️ Erreur extraction & matching : {e}")
        return {
            "secteur_enjeu": "Analyse d'offre non disponible",
            "mots_cles_metier": [],
            "projets_selectionnes": [],
            "score_adequation": 50,
            "points_forts": []
        }


def _rediger_lettre_adaptee(offre: dict, cv_texte: str, analyse_matching: dict, retour_critique: str = None) -> str:
    """
    Étape 3 : Rédige la lettre de motivation sur mesure.
    """
    projets_str = ""
    for p in analyse_matching.get("projets_selectionnes", []):
        projets_str += f"• {p.get('nom')} : {p.get('technos_cles')} — {p.get('pourquoi_pertinent')}\n"

    system_prompt = f"""
    Tu es un candidat de niveau Master 2 Data Science / IA rédigant une LETTRE DE MOTIVATION SUR MESURE, PERCUTANTE ET EXTRÊMEMENT TECHNIQUE.

    ENTREPRISE CIBLE : {offre.get('company')}
    INTITULÉ DU POSTE : {offre.get('title')}
    ENJEU PRINCIPAL IDENTIFIÉ : {analyse_matching.get('secteur_enjeu')}
    MOTS CLÉS DU SECTEUR À INTÉGRER : {', '.join(analyse_matching.get('mots_cles_metier', []))}

    PROJETS SPÉCIFIQUES À VALORISER (ISSUS DU MATCHING) :
    {projets_str}

    CONSIGNES ET STRUCTURE DE RÉDACTION :
    1. Objet : Mentionner clairement l'intitulé du poste et la durée (ex: stage 6 mois).
    2. Accroche : Faire un lien direct entre le parcours du candidat et l'enjeu précis de l'entreprise.
    3. Corps (Preuves & Projets) : Utiliser OBLIGATOIREMENT une liste à puces (•) pour détailler les 2 projets sélectionnés ci-dessus, avec leurs caractéristiques techniques (architectures, algorithmes, métriques, outils).
    4. Projection Métier : Expliquer comment ces réalisations répondent concrètement aux défis décrits dans l'offre.
    5. Conclusion : Demande d'entretien directe et formule de politesse soignée.

    REGLES STRICTES DE STYLE (ANTI-RÉPÉTITION & ANTI-PHRASES CREUSES) :
    - INTERDIT d'utiliser des formules génériques : "je suis convaincu que", "un atout pour votre équipe", "excellent candidat", "passionné depuis toujours", "dynamique et motivé".
    - Chaque paragraphe doit apporter une preuve ou un élément factuel.
    - Ton : Professionnel, orienté ingénierie et résultats.
    """

    if retour_critique:
        system_prompt += f"\n\n⚠️ REVISION REQUISE : Corrige impérativement : {retour_critique}"

    user_prompt = f"""
    DESCRIPTION COMPLETE DE L'OFFRE :
    {offre.get('description', '')[:3000]}

    Rédige la lettre complète en texte pur.
    """

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    # Utilisation du module multi-fournisseurs (modèle rédaction)
    contenu = _appeler_avec_repli(
        messages=messages,
        taille="redaction",
        temperature=0.3,
        max_tokens=2500,
        json_mode=False
    )
    return contenu.strip() if contenu else ""


def _critiquer_lettre(lettre: str, offre: dict, analyse_matching: dict) -> dict:
    """Étape 4 : Vérification de la lettre."""
    if not lettre:
        return {"score": 0, "justification": "Lettre vide."}

    prompt = f"""
    Tu es un réviseur de candidatures ultra-strict.
    Évalue cette lettre de motivation destinée à l'offre '{offre.get('title')}' chez '{offre.get('company')}'.

    CRITÈRES D'ÉVALUATION :
    1. Prescriptions anti-phrases creuses : Contient-elle des expressions bannies comme "je suis convaincu", "atout pour votre équipe", "excellent candidat" ? (Si oui -> Baisse la note).
    2. Adaptation : Les projets cités et le vocabulaire correspondent-ils bien à cette offre spécifique ?
    3. Présence des puces techniques : La lettre utilise-t-elle des puces claires pour exposer les réalisations ?

    LETTRE À ÉVALUER :
    {lettre[:3000]}

    Réponds UNIQUEMENT en JSON strict :
    {{
      "score": <note sur 10>,
      "justification": "Explication courte si la note est inférieure à 8"
    }}
    """
    messages = [{"role": "user", "content": prompt}]
    
    try:
        res = appel_json(messages=messages, taille="leger", temperature=0.0, max_tokens=200)
        return {"score": int(res.get("score", 10)), "justification": str(res.get("justification", ""))}
    except Exception as e:
        print(f"⚠️ Erreur critique lettre : {e}")
        return {"score": 10, "justification": "Contrôle indisponible"}


def analyser_et_rediger(offre: dict, cv_texte: str, portfolio_texte: str, github_texte: str) -> dict:
    """Pipeline principal de l'agent adapteur d'offres."""
    try:
        print(f"🔍 Analyse et matching pour l'offre : {offre.get('title')} chez {offre.get('company')}...")
        
        # 1. Matching intelligent
        matching = _extraire_et_matcher(offre, cv_texte, portfolio_texte, github_texte)

        # 2. Rédaction
        lettre = _rediger_lettre_adaptee(offre, cv_texte, matching)

        # 3. Contrôle qualité / Critique
        critique = _critiquer_lettre(lettre, offre, matching)

        if critique["score"] < SCORE_REGENERATION_SEUIL:
            print(f"  ⚠️ Lettre ajustée ({critique['score']}/10 : {critique['justification']}) — régénération...")
            lettre = _rediger_lettre_adaptee(
                offre, cv_texte, matching, retour_critique=critique["justification"]
            )

        nb_mots = len(lettre.split()) if lettre else 0
        print(f"✅ Lettre adaptée générée ({nb_mots} mots).")

        return {
            "score_adequation": int(matching.get("score_adequation", 0)),
            "besoin_cle_entreprise": str(matching.get("secteur_enjeu", "")),
            "preuve_technique_citee": ", ".join([p.get("nom", "") for p in matching.get("projets_selectionnes", [])]),
            "points_forts": matching.get("points_forts", []),
            "lettre_motivation": lettre
        }

    except Exception as e:
        print(f"⚠️ Erreur globale agent : {e}")
        return None
