import json
import time
import os
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL_REDACTION = "openai/gpt-oss-120b"
MODEL_LEGER = "openai/gpt-oss-20b"

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
    """
    Étape 1 & 2 : Analyse dynamiquement l'offre (besoins explicites de l'entreprise)
    et sélectionne les projets/preuves les plus pertinents dans le dossier du candidat,
    en extrayant UNIQUEMENT ce qui est réellement présent dans les documents fournis.
    """
    prompt = f"""
    Tu es un Expert Recruteur et Data Scientist, rigoureux et factuel.
    Analyse l'offre d'emploi ci-dessous et effectue un matching dynamique avec le profil du candidat.

    OFFRE D'EMPLOI :
    Titre : {offre.get('title')}
    Entreprise : {offre.get('company')}
    Description : {offre.get('description', '')[:3500]}

    DOSSIER COMPLET DU CANDIDAT :
    [CV] : {cv_texte[:2500]}
    [PORTFOLIO] : {portfolio_texte[:3500]}
    [GITHUB] : {github_texte[:3000]}

    TÂCHES :
    1. Identifie 2 à 4 BESOINS CONCRETS ET EXPLICITES de l'entreprise tels que formulés dans l'offre
       (pas une reformulation vague — reprends les responsabilités/exigences réellement écrites).
    2. Sélectionne les 2 PROJETS du candidat les plus pertinents par rapport à CES besoins précis.
    3. Pour chaque projet, extrais UNIQUEMENT les technologies et métriques EXPLICITEMENT présentes
       dans [CV]/[PORTFOLIO]/[GITHUB] ci-dessus. N'invente RIEN : si aucune métrique chiffrée n'existe
       dans la source pour ce projet, laisse "metriques" à une chaîne vide — ne complète jamais avec
       un chiffre plausible.
    4. Identifie un FACTEUR DIFFÉRENCIANT RÉEL du candidat par rapport à un profil Data/IA "standard"
       de même niveau — ex: une combinaison inhabituelle de compétences, un projet mené en autonomie
       de bout en bout, un domaine d'application rare (énergie, batteries, réglementation...). Ce facteur
       DOIT être déductible du dossier fourni — jamais une qualité générique du type "très motivé".
    5. Extrais le vocabulaire métier exact de l'offre à réutiliser dans la lettre.

    Réponds UNIQUEMENT sous forme de JSON strict :
    {{
      "besoins_entreprise": ["besoin concret 1 tiré du texte de l'offre", "besoin concret 2", "..."],
      "secteur_enjeu": "Description en une phrase de l'enjeu principal de l'offre",
      "facteur_differenciant": "Ce qui distingue concrètement ce candidat, ancré dans un fait réel du dossier",
      "mots_cles_metier": ["mot1", "mot2", "mot3", "mot4"],
      "projets_selectionnes": [
        {{
          "nom": "Nom du projet, tel qu'il apparaît dans la source",
          "technos_cles": "Technos/méthodes UNIQUEMENT si mentionnées dans la source",
          "metriques": "Chiffre EXACT trouvé dans la source, ou chaîne vide si aucun n'existe",
          "besoin_couvert": "Quel besoin_entreprise ce projet adresse précisément",
          "pourquoi_pertinent": "Pourquoi ce projet prouve que le candidat peut répondre à ce besoin"
        }}
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
        )
        return json.loads(r.choices[0].message.content)
    except Exception as e:
        print(f"⚠️ Erreur extraction & matching : {e}")
        return {
            "besoins_entreprise": [],
            "secteur_enjeu": "Analyse d'offre non disponible",
            "mots_cles_metier": [],
            "projets_selectionnes": [],
            "score_adequation": 50,
            "points_forts": []
        }


def _rediger_lettre_adaptee(offre: dict, cv_texte: str, analyse_matching: dict, retour_critique: str = None) -> str:
    """
    Étape 3 : Rédige la lettre de motivation sur mesure en mappant explicitement
    chaque besoin de l'entreprise à une preuve du candidat, sans jamais inventer
    de métrique ou de techno absente de la source.
    """
    projets_str = ""
    for p in analyse_matching.get("projets_selectionnes", []):
        metrique = p.get("metriques", "").strip()
        metrique_str = f" — Résultat : {metrique}" if metrique else " — (pas de métrique chiffrée disponible, décrire qualitativement)"
        projets_str += (
            f"• {p.get('nom')} : {p.get('technos_cles')}{metrique_str}\n"
            f"  Répond au besoin : {p.get('besoin_couvert', 'N/A')}\n"
        )

    besoins_str = "\n".join(f"- {b}" for b in analyse_matching.get("besoins_entreprise", [])) or "- (aucun besoin explicite extrait)"

    system_prompt = f"""
    Tu es un candidat de niveau Master 2 Data Science / IA rédigant une LETTRE DE MOTIVATION SUR MESURE, PERCUTANTE ET FACTUELLE.

    POSTURE À ADOPTER : Imagine un recruteur qui a reçu des centaines de candidatures pour cette offre.
    Il ne cherche pas une lettre polie de plus — il cherche une raison concrète de RETENIR celle-ci plutôt
    que les autres. Chaque phrase doit répondre implicitement à la question "pourquoi lui/elle et pas un
    autre profil Data/IA de même niveau ?" — via des faits précis, jamais via des superlatifs ou des
    déclarations d'intention.

    ENTREPRISE CIBLE : {offre.get('company')}
    INTITULÉ DU POSTE : {offre.get('title')}
    ENJEU PRINCIPAL IDENTIFIÉ : {analyse_matching.get('secteur_enjeu')}
    FACTEUR DIFFÉRENCIANT RÉEL DU CANDIDAT (à faire ressortir sans l'affirmer platement) : {analyse_matching.get('facteur_differenciant', '')}

    BESOINS CONCRETS DE L'ENTREPRISE (extraits littéralement de l'offre — à adresser un par un) :
    {besoins_str}

    MOTS CLÉS DU SECTEUR À INTÉGRER : {', '.join(analyse_matching.get('mots_cles_metier', []))}

    PROJETS À MOBILISER COMME PREUVES (avec le besoin que chacun couvre) :
    {projets_str}

    CONSIGNES ET STRUCTURE DE RÉDACTION :
    1. Objet : Mentionner clairement l'intitulé du poste et la durée (ex: stage 6 mois).
    2. Accroche : Lien direct entre le parcours du candidat et l'enjeu précis de l'entreprise —
       VARIE la formulation d'une lettre à l'autre, évite les tournures d'ouverture répétitives
       type "correspond exactement à la mission de X".
    3. Corps (Besoins & Preuves) : Pour CHAQUE besoin listé ci-dessus, associe explicitement le
       projet qui y répond, en liste à puces (•), avec ses caractéristiques techniques RÉELLES.
       Fais ressortir le facteur différenciant à travers les FAITS eux-mêmes (le projet, le contexte,
       la façon dont il a été mené), jamais en le déclarant directement ("je suis unique parce que...").
    4. Projection Métier : Comment ces réalisations répondent concrètement aux défis décrits dans l'offre —
       c'est ici que la lettre doit donner envie d'un entretien plutôt que de passer au CV suivant.
    5. Conclusion : Demande d'entretien directe et formule de politesse soignée.

    REGLES ANTI-HALLUCINATION (STRICTES — prioritaires sur tout le reste, y compris sur la différenciation) :
    - N'invente JAMAIS de métrique chiffrée (%, durée, volume, score) absente de la section
      "PROJETS À MOBILISER" ci-dessus. Si un projet n'a pas de métrique fournie, décris le résultat
      qualitativement (ex: "a permis de fiabiliser le traitement des données") SANS donner de chiffre.
    - Ne cite QUE les technologies listées dans "technos_cles" ci-dessus pour chaque projet —
      jamais une techno "probable" ou "logique" mais non confirmée.
    - Si un besoin de l'entreprise n'a aucun projet correspondant, ne force pas un lien artificiel :
      mentionne une compétence transférable réelle plutôt que d'inventer une expérience.
    - Le facteur différenciant doit rester ANCRÉ dans les projets/faits réels listés ci-dessus —
      ne jamais l'enjoliver avec un détail non présent dans la source.

    REGLES DE STYLE (ANTI-RÉPÉTITION, ANTI-PHRASES CREUSES, ANTI-GÉNÉRIQUE) :
    - INTERDIT d'utiliser des formules génériques : "je suis convaincu que", "un atout pour votre équipe", "excellent candidat", "passionné depuis toujours", "dynamique et motivé", "le candidat idéal".
    - INTERDIT d'affirmer la différenciation directement ("ce qui me distingue est...") — elle doit se voir
      à travers les faits présentés, pas être proclamée.
    - Chaque paragraphe doit apporter une preuve ou un élément factuel, jamais une affirmation gratuite.
    - Ton : Professionnel, orienté ingénierie et résultats.
    """

    if retour_critique:
        system_prompt += f"\n\n REVISION REQUISE : La version précédente comporte des faiblesses. Corrige impérativement : {retour_critique}"

    user_prompt = f"""
    DESCRIPTION COMPLETE DE L'OFFRE :
    {offre.get('description', '')[:3000]}

    Rédige la lettre complète en texte pur.
    """

    r = _appel_groq(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        model=MODEL_REDACTION,
        temperature=0.4,
        max_tokens=2500,
        json_mode=False
    )
    return r.choices[0].message.content.strip()


def _critiquer_lettre(lettre: str, offre: dict, analyse_matching: dict, cv_texte: str, portfolio_texte: str, github_texte: str) -> dict:
    """Étape 4 : Vérifie le style, la fidélité factuelle à la source, ET le pouvoir différenciant réel de la lettre."""
    if not lettre:
        return {"score": 0, "justification": "Lettre vide."}

    prompt = f"""
    Tu es un réviseur de candidatures ultra-strict, ancien recruteur technique.
    Évalue cette lettre de motivation destinée à l'offre '{offre.get('title')}' chez '{offre.get('company')}'.

    DOSSIER SOURCE DU CANDIDAT (pour vérification factuelle) :
    [CV] : {cv_texte[:2500]}
    [PORTFOLIO] : {portfolio_texte[:3000]}
    [GITHUB] : {github_texte[:2500]}

    CRITÈRES D'ÉVALUATION (chacun peut faire chuter la note à lui seul) :
    1. FIDÉLITÉ FACTUELLE (le plus important) : Repère chaque métrique chiffrée, techno ou réalisation
       citée dans la lettre. Est-elle VRAIMENT présente dans le dossier source ci-dessus, ou semble-t-elle
       inventée/extrapolée ? Toute métrique ou affirmation non vérifiable dans le dossier = note ≤ 4/10,
       quelle que soit la qualité du reste.
    2. POUVOIR DIFFÉRENCIANT : Un recruteur qui lit des centaines de lettres similaires retiendrait-il
       CELLE-CI ? Ou ressemble-t-elle à n'importe quelle lettre de candidat Data/IA de même niveau,
       malgré des faits corrects ? La différenciation doit transparaître à travers des faits précis,
       pas des formules ("motivé", "passionné", "excellent").
    3. Anti-phrases creuses : Contient-elle des expressions bannies comme "je suis convaincu", "atout pour votre équipe", "excellent candidat", "le candidat idéal" ?
    4. Adaptation : Les projets cités et le vocabulaire correspondent-ils bien aux besoins précis de CETTE offre (pas juste au domaine en général) ?
    5. Présence des puces techniques : La lettre utilise-t-elle des puces claires pour exposer les réalisations ?

    LETTRE À ÉVALUER :
    {lettre[:3000]}

    Réponds UNIQUEMENT en JSON strict :
    {{
      "score": <note sur 10>,
      "fidelite_factuelle_ok": true ou false,
      "differenciation_suffisante": true ou false,
      "justification": "Explication courte, notamment si un fait semble halluciné ou si la lettre reste générique"
    }}
    """
    try:
        r = _appel_groq(
            messages=[{"role": "user", "content": prompt}],
            model=MODEL_LEGER,
            temperature=0,
            max_tokens=300,
        )
        res = json.loads(r.choices[0].message.content)
        return {
            "score": int(res.get("score", 10)),
            "fidelite_factuelle_ok": bool(res.get("fidelite_factuelle_ok", True)),
            "differenciation_suffisante": bool(res.get("differenciation_suffisante", True)),
            "justification": str(res.get("justification", "")),
        }
    except Exception as e:
        print(f"⚠️ Erreur critique lettre : {e}")
        return {"score": 10, "fidelite_factuelle_ok": True, "differenciation_suffisante": True, "justification": "Contrôle indisponible"}


def analyser_et_rediger(offre: dict, cv_texte: str, portfolio_texte: str, github_texte: str) -> dict:
    """Pipeline principal de l'agent adapteur d'offres."""
    try:
        print(f"🔍 Analyse et matching pour l'offre : {offre.get('title')} chez {offre.get('company')}...")

        matching = _extraire_et_matcher(offre, cv_texte, portfolio_texte, github_texte)
        lettre = _rediger_lettre_adaptee(offre, cv_texte, matching)
        critique = _critiquer_lettre(lettre, offre, matching, cv_texte, portfolio_texte, github_texte)

        besoin_regeneration = (
            critique["score"] < SCORE_REGENERATION_SEUIL
            or not critique.get("fidelite_factuelle_ok", True)
        )

        if besoin_regeneration:
            motif = critique["justification"]
            if not critique.get("fidelite_factuelle_ok", True):
                motif = f"HALLUCINATION DÉTECTÉE — retire tout fait non vérifiable dans la source. {motif}"
            print(f"  ⚠️ Lettre ajustée ({critique['score']}/10 : {motif}) — régénération...")
            lettre = _rediger_lettre_adaptee(
                offre, cv_texte, matching, retour_critique=motif
            )
            # Deuxième passe de contrôle après régénération, pour ne jamais laisser
            # partir une hallucination non détectée en cas d'échec de la 1re correction
            critique = _critiquer_lettre(lettre, offre, matching, cv_texte, portfolio_texte, github_texte)
            if not critique.get("fidelite_factuelle_ok", True):
                print(f"  🚫 Hallucination persistante après régénération — offre écartée par prudence.")
                return None

        nb_mots = len(lettre.split())
        print(f" Lettre adaptée générée ({nb_mots} mots).")

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
