# src/cv_agent.py
"""
Agent de génération de CV adapté à l'offre.
S'appuie sur le même client Groq et le même style de pipeline que agent.py
(extraction JSON -> sélection/rédaction -> rendu). Réutilise si possible le
résultat de `_extraire_et_matcher()` (agent.py) pour éviter un appel API redondant.
"""

import json
import os
import re
from datetime import datetime

from groq import Groq
from fpdf import FPDF

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL_LEGER = "llama-3.1-8b-instant"

# Chemins des polices Unicode (nécessaires pour les accents français ET
# les puces spéciales). Si absentes, on retombe sur Helvetica + puces ASCII.
FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
FONT_REGULAR = os.path.join(FONT_DIR, "DejaVuSans.ttf")
FONT_BOLD = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")
FONT_ITALIC = os.path.join(FONT_DIR, "DejaVuSans-Oblique.ttf")

# Palette identique à l'identité visuelle du portfolio
FOREST = (31, 61, 43)      # #1F3D2B
COPPER = (156, 91, 51)     # #9C5B33
DARKGRAY = (58, 58, 58)
MIDGRAY = (90, 90, 90)


# ---------------------------------------------------------------------------
# 1. Données statiques du candidat (ne dépendent pas de l'offre)
# ---------------------------------------------------------------------------

CANDIDAT = {
    "nom": "Kossi NOUMAGNO",
    "localisation": "Brunstatt (France)",
    "telephone": "+33 7 45 97 43 82",
    "email": "noumagnokossi0@gmail.com",
    "linkedin": "linkedin.com/in/kossi-noumagno",
    "github": "github.com/Dave-kossi",
    "portfolio": "dave-kossi.github.io/kossi-NOUMAGNO",
    "disponibilite": "Mars 2027",
}

FORMATION = [
    "Master 2 Ingénierie Mathématique & Data Science – Université de Haute-Alsace (2026–2027)",
    "Licence Mathématiques Appliquées – Université de Haute-Alsace (2024–2025)",
    "Licence Fondamentale de Mathématiques – Université de Lomé (2019–2023)",
]

CERTIFICATIONS = [
    "Spécialisation en Machine Learning – DeepLearning.AI & Stanford Online",
    "Google Data Analytics Certificate",
    "Certification : IA in Fraud Detection",
]

LANGUES = "Français : natif  |  Anglais : B2 (langue de travail)"

EXPERIENCES = [
    {
        "titre": "Optimisation et Administration logistique (Bénévolat)",
        "structure": "Secours populaire français du Haut-Rhin (France)",
        "periode": "02/2026 – Aujourd'hui",
        "bullets": [
            "Analyse des flux logistiques",
            "Optimisation de la gestion des stocks et participation à la digitalisation des processus",
        ],
    },
    {
        "titre": "Technicien informatique & support IT",
        "structure": "COMPUTER FOREVER (Togo)",
        "periode": "2022 – 2024",
        "bullets": [
            "Maintenance, diagnostic et résolution de problèmes matériels et logiciels pour les PME et PMI",
            "Support aux utilisateurs et gestion d'outils numériques avec une approche analytique et rigoureuse",
        ],
    },
]

SOFT_SKILLS = [
    "Esprit critique et rigueur professionnelle : approche analytique et souci du détail",
    "Autodidacte et curieux : capacité à apprendre et à m'adapter rapidement",
    "Esprit attentif et communicant : favorisant la collaboration en équipe",
]

# Catalogue exhaustif des projets réalisés. Le LLM choisit et ordonne un
# sous-ensemble (3 à 4) en fonction de l'offre — il n'invente jamais de contenu,
# il sélectionne parmi cette liste fermée.
PROJETS_DISPONIBLES = {
    "job_agent": {
        "nom": "Agent IA Autonome de Candidature (Job Agent AI)",
        "tag": "IA Agentique, LLM, Automatisation",
        "stack": "Python · Groq API (Llama 3.3/3.1) · pipeline multi-étapes · GitHub Actions (cron) · Streamlit Cloud",
        "objectif": "automatiser la veille d'offres d'emploi (scraping multi-sources) et la génération de lettres de motivation personnalisées via un pipeline agentique en 3 étapes : extraction des besoins entreprise en JSON, rédaction, auto-critique et régénération conditionnelle",
        "impact": "solution déployée en production (GitHub + Streamlit Cloud, automatisation par CI/CD), conçue pour être open-sourcée",
        "mots_cles": ["agent", "agentique", "llm", "automatisation", "orchestration", "pipeline", "ia générative"],
    },
    "ventire": {
        "nom": "Copilote d'Arbitrage Réglementaire (VentiRE)",
        "tag": "RAG, LLM open source, Recherche hybride",
        "stack": "Python · LlamaIndex · LLM open source (Ollama) · FastEmbed · Cohere Rerank · Streamlit",
        "objectif": "concevoir un moteur RAG hybride multi-segments pour automatiser l'analyse de conformité des systèmes de ventilation (RE2020, Arrêtés ERP 2016/2025)",
        "impact": "élimination des risques d'erreur d'interprétation réglementaire, fiabilité des audits techniques renforcée",
        "mots_cles": ["rag", "llm", "embeddings", "recherche", "nlp", "conformité", "réglementaire", "ia générative"],
    },
    "fraude": {
        "nom": "Analyse et détection de fraude bancaire",
        "tag": "Machine Learning supervisé",
        "stack": "Python · Scikit-learn · LightGBM · données déséquilibrées",
        "objectif": "analyse de 50 000 transactions et comparaison de 5 modèles supervisés ; LightGBM retenu comme optimal (F1 0.764, Recall 0.620, AUC 0.804)",
        "impact": "amélioration de la détection des fraudes et réduction des fausses alertes clients",
        "mots_cles": ["fraude", "scoring", "classification", "risque", "finance", "ml supervisé", "déséquilibré"],
    },
    "rte": {
        "nom": "Dashboard énergétique RTE France",
        "tag": "Time Series Forecasting",
        "stack": "Python · Streamlit · LightGBM (Gradient Boosting quantile) · API éCO2mix (RTE)",
        "objectif": "dashboard d'analyse de la production/consommation électrique française avec module de prévision (J+1) et détection d'anomalies",
        "impact": "outil connecté à une API officielle temps réel, avec forecast quantile et backtest du modèle",
        "mots_cles": ["forecast", "prévision", "time series", "énergie", "anomalies", "gradient boosting"],
    },
    "europa_energie": {
        "nom": "Analyse décisionnelle de la transition énergétique en Europe",
        "tag": "Data Visualisation, Clustering",
        "stack": "Python · Pandas · NumPy · Plotly · Streamlit · SciPy · Clustering · Time Series",
        "objectif": "outil d'intelligence décisionnelle pour évaluer la performance des pays européens et simuler des scénarios prospectifs à horizon 2050 (données OWID Energy)",
        "impact": "aide à la décision comparative sur la transition énergétique européenne",
        "mots_cles": ["énergie", "clustering", "dataviz", "prospective", "europe", "bi"],
    },
}

# Groupes de compétences ; le LLM choisit uniquement l'ORDRE d'affichage,
# jamais le contenu (pour ne rien inventer).
COMPETENCES_DISPONIBLES = {
    "Langages & Data": "Python (Pandas, NumPy, Scikit-learn, TensorFlow, PyTorch), SQL, R, NoSQL",
    "IA Générative & Agents": "RAG (LlamaIndex), LLM (Mistral, Llama, Gemma), orchestration de pipelines agentiques, embeddings, prompt engineering",
    "Cloud & MLOps": "BigQuery, GitHub / GitHub Actions, Streamlit Cloud, Hugging Face",
    "Visualisation & BI": "Power BI, Tableau, Plotly, Matplotlib, Seaborn, Streamlit",
}


# ---------------------------------------------------------------------------
# 2. Sélection et rédaction du contenu adapté (LLM)
# ---------------------------------------------------------------------------

def _appel_groq_json(prompt: str, model: str = MODEL_LEGER, temperature: float = 0.2, max_tokens: int = 900) -> dict:
    r = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    return json.loads(r.choices[0].message.content)


def _selectionner_contenu_cv(offre: dict, analyse_matching: dict | None = None) -> dict:
    """
    Choisit 3 à 4 projets (parmi PROJETS_DISPONIBLES), l'ordre des groupes de
    compétences, et rédige le paragraphe PROFIL — tout est adapté à l'offre,
    mais le LLM ne fait QUE sélectionner/prioriser/reformuler du profil : les
    projets eux-mêmes (stack, objectif, impact) restent figés dans le catalogue
    pour éviter toute invention de faits.
    """
    catalogue_str = "\n".join(
        f'- ID "{cle}" : {p["nom"]} — mots-clés : {", ".join(p["mots_cles"])}'
        for cle, p in PROJETS_DISPONIBLES.items()
    )
    contexte_matching = ""
    if analyse_matching:
        contexte_matching = f"""
    ANALYSE DE MATCHING DÉJÀ RÉALISÉE POUR CETTE OFFRE :
    Enjeu principal : {analyse_matching.get('secteur_enjeu', '')}
    Mots-clés métier : {', '.join(analyse_matching.get('mots_cles_metier', []))}
    """

    prompt = f"""
    Tu prépares un CV d'un étudiant Master 2 Data Science / IA pour une offre de stage précise.
    Tu ne dois JAMAIS inventer de projet, de compétence ou de chiffre : tu choisis uniquement
    parmi les éléments fournis ci-dessous et tu reformules le paragraphe de profil.

    OFFRE : {offre.get('title')} chez {offre.get('company')}
    DESCRIPTION (extrait) : {offre.get('description', '')[:2500]}
    {contexte_matching}

    CATALOGUE DE PROJETS DISPONIBLES :
    {catalogue_str}

    GROUPES DE COMPÉTENCES DISPONIBLES (ordonne du plus au moins pertinent) :
    {list(COMPETENCES_DISPONIBLES.keys())}

    Réponds UNIQUEMENT en JSON strict :
    {{
      "tagline": "Accroche courte (ex: Data Science - IA Générative & Agentique - Machine Learning), adaptée au vocabulaire de l'offre",
      "profil": "Paragraphe de 3-4 phrases à la première personne, factuel, mentionnant le Master 2, les compétences clés démontrées et la disponibilité de stage",
      "projets_ordonnes": ["id_projet_le_plus_pertinent", "id_projet_2e_plus_pertinent", "id_projet_3e_plus_pertinent"],
      "groupes_competences_ordre": ["Groupe le plus pertinent", "..."]
    }}

    IMPORTANT : "projets_ordonnes" doit contenir EXACTEMENT 3 identifiants (pas 2, pas 4),
    choisis parmi les IDs du catalogue ci-dessus, du plus pertinent au moins pertinent
    par rapport à cette offre précise. Ce CV doit tenir sur UNE seule page : ne
    sélectionne que les 3 projets qui maximisent la pertinence, pas plus.
    """
    try:
        return _appel_groq_json(prompt)
    except Exception as e:
        print(f"⚠️ Erreur sélection contenu CV : {e}")
        # Repli sûr : ordre par défaut, profil générique
        return {
            "tagline": "Data Science • IA Générative & Agentique • Machine Learning",
            "profil": (
                "Étudiant en Master 2 Ingénierie Mathématique & Data Science à l'Université "
                "de Haute-Alsace, je conçois des solutions de Data Science, Machine Learning "
                "et IA Générative/Agentique en Python, de l'exploration des données jusqu'au "
                f"déploiement. Je recherche un stage de fin d'études à partir de {CANDIDAT['disponibilite']}."
            ),
            "projets_ordonnes": ["job_agent", "ventire", "fraude"],
            "groupes_competences_ordre": list(COMPETENCES_DISPONIBLES.keys()),
        }


# ---------------------------------------------------------------------------
# 3. Rendu PDF (fpdf2)
# ---------------------------------------------------------------------------

class CVPdf(FPDF):
    def __init__(self):
        super().__init__(format="A4")
        self.unicode_ok = os.path.exists(FONT_REGULAR) and os.path.exists(FONT_BOLD)
        if self.unicode_ok:
            self.add_font("DejaVu", "", FONT_REGULAR)
            self.add_font("DejaVu", "B", FONT_BOLD)
            if os.path.exists(FONT_ITALIC):
                self.add_font("DejaVu", "I", FONT_ITALIC)
            self.base_font = "DejaVu"
            self.puce = "•"
        else:
            # Repli : polices DejaVu introuvables (ex: dossier fonts/ non commité
            # ou chemin différent sur le runner CI). On force l'encodage cp1252
            # pour les polices standard (Helvetica) : il couvre bullet/tirets
            # longs/guillemets typographiques/œ, contrairement à latin-1 strict
            # qui casse dessus. Voir _safe() ci-dessous pour la dernière protection.
            print("⚠️ Polices DejaVu introuvables (dossier 'fonts/') — repli sur Helvetica (cp1252).")
            self.base_font = "helvetica"
            self.puce = "•"
            self.core_fonts_encoding = "cp1252"
        self.set_margins(15, 10, 15)
        self.set_auto_page_break(auto=True, margin=10)

    def _font(self, style="", size=10, color=DARKGRAY):
        self.set_font(self.base_font, style, size)
        self.set_text_color(*color)

    def _safe(self, text: str) -> str:
        """
        Dernier filet de sécurité : ne DOIT jamais lever d'exception, quel que
        soit le texte (y compris du texte généré par le LLM, imprévisible).
        Avec DejaVu (unicode_ok=True), la couverture est large mais pas totale
        (émojis, symboles rares) -> on encode/décode en UTF-8 pour ne garder
        que ce que la police peut réellement afficher, en remplaçant le reste.
        Sans DejaVu, on force cp1252 (couvre bullet, tirets, guillemets, œ).
        """
        if text is None:
            return ""
        text = str(text)
        encodage = "utf-8" if self.unicode_ok else "cp1252"
        return text.encode(encodage, errors="replace").decode(encodage, errors="replace")

    def cell(self, *args, **kwargs):
        if "text" in kwargs:
            kwargs["text"] = self._safe(kwargs["text"])
        elif len(args) >= 3:
            args = list(args)
            args[2] = self._safe(args[2])
        return super().cell(*args, **kwargs)

    def multi_cell(self, *args, **kwargs):
        if "text" in kwargs:
            kwargs["text"] = self._safe(kwargs["text"])
        elif len(args) >= 3:
            args = list(args)
            args[2] = self._safe(args[2])
        return super().multi_cell(*args, **kwargs)

    def write(self, *args, **kwargs):
        if "text" in kwargs:
            kwargs["text"] = self._safe(kwargs["text"])
        elif len(args) >= 2:
            args = list(args)
            args[1] = self._safe(args[1])
        return super().write(*args, **kwargs)

    def entete(self, tagline: str):
        self._font("B", 20, FOREST)
        self.cell(0, 9, CANDIDAT["nom"], new_x="LMARGIN", new_y="NEXT")
        self._font("B", 10, COPPER)
        stage_line = f"Recherche d'un stage de fin d'études (min 6 mois) — {CANDIDAT['disponibilite']}  |  {tagline}"
        self.multi_cell(0, 5, stage_line, new_x="LMARGIN", new_y="NEXT")
        self._font("", 9, DARKGRAY)
        self.cell(0, 5, f"{CANDIDAT['localisation']}  |  {CANDIDAT['telephone']}  |  {CANDIDAT['email']}", new_x="LMARGIN", new_y="NEXT")
        self._font("", 9, COPPER)
        self.cell(0, 5, f"{CANDIDAT['linkedin']}   |   {CANDIDAT['github']}   |   {CANDIDAT['portfolio']}", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*FOREST)
        self.set_line_width(0.5)
        self.ln(2)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(3)

    def section(self, titre: str):
        self._font("B", 10.5, FOREST)
        self.cell(0, 5.2, titre.upper(), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*FOREST)
        self.set_line_width(0.3)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(1.2)

    def paragraphe(self, texte: str):
        self._font("", 9.5, DARKGRAY)
        self.multi_cell(0, 4.6, texte, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def projet(self, p: dict):
        self._font("B", 10, COPPER)
        self.write(4.6, f"{self.puce} ")
        self._font("B", 10, FOREST)
        self.write(4.6, p["nom"])
        self._font("I", 9, MIDGRAY)
        self.write(4.6, f"   —  {p['tag']}")
        self.ln(4.6)
        self._font("I", 8.5, MIDGRAY)
        self.multi_cell(0, 3.9, p["stack"], new_x="LMARGIN", new_y="NEXT")
        self._font("B", 9, DARKGRAY)
        self.write(4.1, "Objectif : ")
        self._font("", 9, DARKGRAY)
        self.write(4.1, p["objectif"])
        self.ln(4.3)
        self._font("B", 9, DARKGRAY)
        self.write(4.1, "Impact : ")
        self._font("", 9, DARKGRAY)
        self.write(4.1, p["impact"])
        self.ln(5.2)

    def ligne_bullet(self, gras: str, texte: str = ""):
        self._font("B", 9.5, COPPER)
        self.write(4.2, f"{self.puce} ")
        if texte:
            self._font("B", 9.5, DARKGRAY)
            self.write(4.2, f"{gras} : ")
            self._font("", 9.5, DARKGRAY)
            self.write(4.2, texte)
        else:
            self._font("", 9.5, DARKGRAY)
            self.write(4.2, gras)
        self.ln(4.4)

    def experience_bloc(self, exp: dict):
        self._font("B", 9.5, FOREST)
        self.write(4.2, exp["titre"])
        self._font("I", 8.5, MIDGRAY)
        self.write(4.2, f"   —  {exp['structure']}")
        self.ln(4.2)
        self._font("I", 8, MIDGRAY)
        self.cell(0, 3.6, exp["periode"], new_x="LMARGIN", new_y="NEXT")
        for b in exp["bullets"]:
            self._font("", 8.8, DARKGRAY)
            self.set_x(self.l_margin + 4)
            self.multi_cell(0, 3.9, f"{self.puce} {b}", new_x="LMARGIN", new_y="NEXT")
        self.ln(0.5)


def generer_cv_pdf(offre: dict, analyse_matching: dict | None = None, dossier_sortie: str = "output") -> str:
    """Point d'entrée principal : construit le PDF adapté et retourne le chemin du fichier."""
    contenu = _selectionner_contenu_cv(offre, analyse_matching)

    NB_PROJETS_CV = 3  # fixe : garantit la tenue sur une page
    ids_projets = [i for i in contenu.get("projets_ordonnes", []) if i in PROJETS_DISPONIBLES]
    ids_projets = list(dict.fromkeys(ids_projets))  # dédoublonne en gardant l'ordre
    if len(ids_projets) < NB_PROJETS_CV:
        # complète avec les projets par défaut non déjà sélectionnés
        for cle in PROJETS_DISPONIBLES:
            if cle not in ids_projets:
                ids_projets.append(cle)
            if len(ids_projets) == NB_PROJETS_CV:
                break
    ids_projets = ids_projets[:NB_PROJETS_CV]
    projets = [PROJETS_DISPONIBLES[i] for i in ids_projets]

    groupes = [g for g in contenu.get("groupes_competences_ordre", []) if g in COMPETENCES_DISPONIBLES]
    groupes += [g for g in COMPETENCES_DISPONIBLES if g not in groupes]  # sécurité : n'en oublie aucun

    pdf = CVPdf()
    pdf.add_page()
    pdf.entete(contenu.get("tagline", "Data Science • Machine Learning"))

    pdf.section("Profil")
    pdf.paragraphe(contenu.get("profil", ""))

    pdf.section("Projets Data Science & IA")
    for p in projets:
        pdf.projet(p)

    pdf.section("Compétences techniques")
    for g in groupes:
        pdf.ligne_bullet(g, COMPETENCES_DISPONIBLES[g])

    pdf.section("Soft skills")
    for s in SOFT_SKILLS:
        pdf.ligne_bullet(s)

    pdf.section("Expérience & Leadership")
    for exp in EXPERIENCES:
        pdf.experience_bloc(exp)

    pdf.section("Formation")
    for f in FORMATION:
        pdf.ligne_bullet(f)

    pdf.section("Certifications & Langues")
    for c in CERTIFICATIONS:
        pdf.ligne_bullet(c)
    pdf.ligne_bullet(LANGUES)

    os.makedirs(dossier_sortie, exist_ok=True)
    nom_fichier = re.sub(r"[^\w\-]+", "_", offre.get("company", "entreprise")).strip("_")
    chemin = os.path.join(dossier_sortie, f"CV_NOUMAGNO_{nom_fichier}.pdf")
    pdf.output(chemin)
    print(f"✅ CV adapté généré : {chemin}")
    return chemin


# ---------------------------------------------------------------------------
# 4. Intégration avec le pipeline existant (agent.py)
# ---------------------------------------------------------------------------

def generer_candidature_complete(offre: dict, cv_texte: str, portfolio_texte: str, github_texte: str) -> dict:
    """
    Exemple d'intégration : réutilise agent.py pour la lettre, et cv_agent.py
    pour le CV, en partageant le même résultat de matching entre les deux
    pour ne payer l'appel d'extraction qu'une seule fois.
    """
    from agent import _extraire_et_matcher, analyser_et_rediger  # import local pour éviter la dépendance circulaire

    matching = _extraire_et_matcher(offre, cv_texte, portfolio_texte, github_texte)
    resultat_lettre = analyser_et_rediger(offre, cv_texte, portfolio_texte, github_texte)
    chemin_cv = generer_cv_pdf(offre, analyse_matching=matching)

    return {
        **(resultat_lettre or {}),
        "cv_pdf_path": chemin_cv,
    }


if __name__ == "__main__":
    # Test rapide sans appel réseau (mode hors-ligne / démonstration)
    offre_test = {
        "title": "Stagiaire Data Scientist – IA Générative & Agentique",
        "company": "Parfums Christian Dior",
        "description": "Recherche stagiaire Data Science pour développer des applications d'IA Générative/Agentique, du RAG au chatbot, en Python avec GCP et Dataiku.",
    }
    matching_test = {
        "secteur_enjeu": "Automatisation de processus métier via IA Générative et Agentique",
        "mots_cles_metier": ["IA Agentique", "RAG", "LLM", "Python", "GCP"],
    }
    generer_cv_pdf(offre_test, analyse_matching=matching_test)
