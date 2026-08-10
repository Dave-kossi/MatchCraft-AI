"""
Agent de génération de CV adapté à l'offre.
Utilise Llama 3.3 70B via Groq pour la sélection stratégique du contenu 
et FPDF2 pour le rendu déterministe sur 1 page A4.
"""

import json
import os
import re
from groq import Groq
from fpdf import FPDF

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL_ROBUSTE = "llama-3.3-70b-versatile"

# Gestion dynamique du chemin vers le dossier 'fonts' à la racine du projet
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.path.join(BASE_DIR, "fonts")
FONT_REGULAR = os.path.join(FONT_DIR, "DejaVuSans.ttf")
FONT_BOLD = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")
FONT_ITALIC = os.path.join(FONT_DIR, "DejaVuSans-Oblique.ttf")

# Palette visuelle
FOREST = (31, 61, 43)      # #1F3D2B
COPPER = (156, 91, 51)     # #9C5B33
DARKGRAY = (58, 58, 58)
MIDGRAY = (90, 90, 90)


# ---------------------------------------------------------------------------
# 1. Base de données statique du candidat
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
    "Esprit critique et rigueur professionnelle : approche analytique et souci du détail dans la conception et la validation des modèles",
    "Autodidacte et curieux : capacité à apprendre et à m'adapter rapidement à de nouveaux outils et frameworks",
    "Esprit attentif et communicant : favorisant la collaboration et la compréhension mutuelle en équipe",
]

PROJETS_DISPONIBLES = {
    "job_agent": {
        "nom": "Agent IA Autonome de Candidature (Job Agent AI)",
        "tag": "IA Agentique, LLM, Automatisation",
        "stack": "Python · Groq API (Llama 3.3/3.1) · pipeline multi-étapes · GitHub Actions (cron) · Streamlit Cloud",
        "objectif": "automatiser la veille d'offres d'emploi (scraping multi-sources) et la génération de lettres de motivation personnalisées via un pipeline agentique en 3 étapes : extraction des besoins entreprise en JSON, rédaction de la lettre, auto-critique et régénération conditionnelle si le score de spécificité est insuffisant",
        "impact": "solution déployée en production (GitHub + Streamlit Cloud, automatisation hebdomadaire par CI/CD), conçue pour être open-sourcée à destination d'autres étudiants",
        "mots_cles": ["agent", "agentique", "llm", "automatisation", "orchestration", "pipeline", "ia générative", "python"],
    },
    "ventire": {
        "nom": "Copilote d'Arbitrage Réglementaire (VentiRE)",
        "tag": "RAG, LLM open source, Recherche hybride",
        "stack": "Python · LlamaIndex · LLM open source (Ollama) · FastEmbed · Cohere Rerank · Streamlit",
        "objectif": "concevoir un moteur RAG hybride multi-segments pour automatiser l'analyse de conformité des systèmes de ventilation (RE2020, Arrêtés ERP 2016/2025)",
        "impact": "automatisation de l'analyse de conformité multi-réglementaire, élimination des risques d'erreur d'interprétation des débits, renforçant la fiabilité des audits techniques",
        "mots_cles": ["rag", "llm", "embeddings", "recherche", "nlp", "conformité", "réglementaire", "ia générative", "ollama"],
    },
    "fraude": {
        "nom": "Analyse et détection de fraude bancaire",
        "tag": "Machine Learning supervisé",
        "stack": "Python · Scikit-learn · LightGBM · données déséquilibrées",
        "objectif": "analyse de 50 000 transactions et comparaison de 5 modèles supervisés ; LightGBM retenu comme modèle optimal (F1-score 0.764, Recall 0.620, Précision 0.997, AUC 0.804)",
        "impact": "amélioration de la détection des fraudes et réduction des fausses alertes envoyées à des clients innocents",
        "mots_cles": ["fraude", "scoring", "classification", "risque", "finance", "ml supervisé", "déséquilibré", "scikit-learn"],
    },
    "rte": {
        "nom": "Dashboard énergétique RTE France",
        "tag": "Time Series Forecasting",
        "stack": "Python · Streamlit · LightGBM (Gradient Boosting quantile) · API éCO2mix (RTE)",
        "objectif": "dashboard d'analyse de la production et consommation électrique française avec module de prévision (J+1) et détection d'anomalies",
        "impact": "outil de pilotage connecté à une API officielle temps réel, avec forecast quantile et backtest du modèle",
        "mots_cles": ["forecast", "prévision", "time series", "énergie", "anomalies", "gradient boosting", "api"],
    },
    "europa_energie": {
        "nom": "Analyse décisionnelle de la transition énergétique en Europe",
        "tag": "Data Visualisation, Clustering",
        "stack": "Python · Pandas · NumPy · Plotly · Streamlit · SciPy · Clustering · Time Series",
        "objectif": "outil d'intelligence décisionnelle pour évaluer la performance des pays européens et simuler des scénarios prospectifs à horizon 2050 (données OWID Energy)",
        "impact": "aide à la décision comparative sur la transition énergétique européenne",
        "mots_cles": ["énergie", "clustering", "dataviz", "prospective", "europe", "bi", "pandas", "plotly"],
    },
}

COMPETENCES_DISPONIBLES = {
    "Langages & Data": "Python (Pandas, NumPy, Scikit-learn, TensorFlow, PyTorch), SQL, R, NoSQL",
    "IA Générative & Agents": "RAG (LlamaIndex), LLM (Mistral, Llama, Gemma), orchestration de pipelines agentiques, embeddings, prompt engineering",
    "Cloud & MLOps": "BigQuery, GitHub / GitHub Actions, Streamlit Cloud, Hugging Face",
    "Visualisation & BI": "Power BI, Tableau, Plotly, Matplotlib, Seaborn, Streamlit",
}


# ---------------------------------------------------------------------------
# 2. Pipeline d'Intelligence LLM (Llama 3.3 70B)
# ---------------------------------------------------------------------------

def _selectionner_contenu_cv(offre: dict, analyse_matching: dict | None = None) -> dict:
    """Analyse stratégique de l'offre par un LLM 70B pour adapter le CV."""
    catalogue_str = "\n".join(
        f'- ID "{cle}" : {p["nom"]} | Mots-clés: {", ".join(p["mots_cles"])}'
        for cle, p in PROJETS_DISPONIBLES.items()
    )
    
    prompt = f"""
    Tu es un Expert Recruteur Tech & Data Science.
    Ta mission est d'adapter le profil d'un étudiant Master 2 Data Science / IA pour une offre spécifique.

    OFFRE CIBLE :
    Intitulé : {offre.get('title')}
    Entreprise : {offre.get('company')}
    Description : {offre.get('description', '')[:2500]}

    CONTEXTE DE MATCHING :
    Enjeu : {analyse_matching.get('secteur_enjeu', '') if analyse_matching else 'Non spécifié'}

    CATALOGUE DE PROJETS :
    {catalogue_str}

    GROUPES DE COMPÉTENCES :
    {list(COMPETENCES_DISPONIBLES.keys())}

    CONSIGNES STRICTES :
    1. Sélectionne EXACTEMENT les 3 projets les plus pertinents pour cette offre spécifique.
    2. Rédige le paragraphe PROFIL (MAXIMUM 350 caractères / 3 phrases) en mettant en avant l'adéquation exacte entre la formation (Master 2 UHA) et l'enjeu de l'entreprise.
    3. Adapte la TAGLINE (accroche) pour refléter le poste ciblé (ex: Data Science • IA Générative & Agentique • Machine Learning).
    4. Ordonne les groupes de compétences du plus important au moins important pour cette offre.

    Format de réponse attendu (JSON STRICT uniquement) :
    {{
      "tagline": "Accroche personnalisée pour le poste",
      "profil": "Paragraphe de présentation hautement ciblé...",
      "projets_ordonnes": ["id_projet_1", "id_projet_2", "id_projet_3"],
      "groupes_competences_ordre": ["Nom du groupe 1", "Nom du groupe 2", ...]
    }}
    """
    
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=MODEL_ROBUSTE,
            temperature=0.1,
            max_tokens=800,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"⚠️ Erreur sélection LLM CV : {e}")
        return {
            "tagline": "Data Science • IA Générative & Agentique • Machine Learning",
            "profil": (
                "Étudiant en Master 2 Ingénierie Mathématique & Data Science à l'Université "
                "de Haute-Alsace, je conçois des solutions de Data Science, Machine Learning "
                "et IA Générative/Agentique en Python, de l'exploration des données jusqu'au "
                "déploiement. J'ai développé un agent IA autonome orchestrant plusieurs appels LLM "
                "en production ainsi qu'un système RAG hybride pour l'automatisation de processus métier "
                f"réglementaires. Curieux et rigoureux, je recherche un stage de fin d'études de six mois à partir de {CANDIDAT['disponibilite']}."
            ),
            "projets_ordonnes": ["job_agent", "ventire", "fraude"],
            "groupes_competences_ordre": list(COMPETENCES_DISPONIBLES.keys()),
        }


# ---------------------------------------------------------------------------
# 3. Rendu PDF (Strictement 1 Page)
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
            self.puce = "◆"
        else:
            self.base_font = "helvetica"
            self.puce = "-"
        
        self.set_margins(10, 8, 10)
        self.set_auto_page_break(auto=False)  # Verrouille le saut automatique pour garantir 1 seule page

    def _font(self, style="", size=8, color=DARKGRAY):
        self.set_font(self.base_font, style, size)
        self.set_text_color(*color)

    def entete(self, tagline: str):
        self._font("B", 16, FOREST)
        self.cell(0, 6, CANDIDAT["nom"], new_x="LMARGIN", new_y="NEXT")
        
        self._font("B", 8.5, COPPER)
        stage_line = f"Recherche d'un stage de fin d'études (min 6 mois) - {CANDIDAT['disponibilite']} | {tagline}"
        self.multi_cell(0, 3.8, stage_line, new_x="LMARGIN", new_y="NEXT")
        
        self._font("", 8, DARKGRAY)
        self.cell(0, 3.5, f"{CANDIDAT['localisation']} | {CANDIDAT['telephone']} | {CANDIDAT['email']}", new_x="LMARGIN", new_y="NEXT")
        
        self._font("", 8, COPPER)
        self.cell(0, 3.5, f"LinkedIn: {CANDIDAT['linkedin']} | GitHub: {CANDIDAT['github']} | Portfolio: {CANDIDAT['portfolio']}", new_x="LMARGIN", new_y="NEXT")
        
        self.set_draw_color(*FOREST)
        self.set_line_width(0.4)
        self.ln(1)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(1.5)

    def section(self, titre: str):
        self._font("B", 8.5, FOREST)
        self.cell(0, 4, titre.upper(), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*FOREST)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(1)

    def paragraphe(self, texte: str):
        self._font("", 7.8, DARKGRAY)
        self.multi_cell(0, 3.2, texte, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def projet(self, p: dict):
        self._font("B", 8, COPPER)
        self.write(3.2, f"{self.puce} ")
        self._font("B", 8, FOREST)
        self.write(3.2, p["nom"])
        self._font("I", 7.5, MIDGRAY)
        self.write(3.2, f"  —  {p['tag']}")
        self.ln(3.5)
        
        self._font("I", 7.2, MIDGRAY)
        self.multi_cell(0, 3, p["stack"], new_x="LMARGIN", new_y="NEXT")
        
        self._font("B", 7.5, DARKGRAY)
        self.write(3, "Objectif: ")
        self._font("", 7.5, DARKGRAY)
        self.write(3, p["objectif"])
        self.ln(3.2)
        
        self._font("B", 7.5, DARKGRAY)
        self.write(3, "Impact: ")
        self._font("", 7.5, DARKGRAY)
        self.write(3, p["impact"])
        self.ln(3.5)

    def ligne_bullet(self, gras: str, texte: str = ""):
        self._font("B", 8, COPPER)
        self.write(3.2, f"{self.puce} ")
        if texte:
            self._font("B", 8, DARKGRAY)
            self.write(3.2, f"{gras} : ")
            self._font("", 8, DARKGRAY)
            self.write(3.2, texte)
        else:
            self._font("", 8, DARKGRAY)
            self.write(3.2, gras)
        self.ln(3.5)

    def experience_bloc(self, exp: dict):
        self._font("B", 8, FOREST)
        self.write(3.2, exp["titre"])
        self._font("I", 7.5, MIDGRAY)
        self.write(3.2, f"  —  {exp['structure']}")
        self.ln(3.2)
        self._font("I", 7, MIDGRAY)
        self.cell(0, 3, exp["periode"], new_x="LMARGIN", new_y="NEXT")
        for b in exp["bullets"]:
            self._font("", 7.5, DARKGRAY)
            self.set_x(self.l_margin + 3)
            self.multi_cell(0, 3, f"• {b}", new_x="LMARGIN", new_y="NEXT")
        self.ln(1)


def generer_cv_pdf(offre: dict, analyse_matching: dict | None = None, dossier_sortie: str = "output") -> str:
    """Génère un CV PDF ultra-ciblé sur 1 page A4."""
    contenu = _selectionner_contenu_cv(offre, analyse_matching)

    # Restriction stricte aux 3 meilleurs projets
    ids_projets = [i for i in contenu.get("projets_ordonnes", []) if i in PROJETS_DISPONIBLES][:3]
    if not ids_projets:
        ids_projets = list(PROJETS_DISPONIBLES.keys())[:3]
    projets = [PROJETS_DISPONIBLES[i] for i in ids_projets]

    groupes = [g for g in contenu.get("groupes_competences_ordre", []) if g in COMPETENCES_DISPONIBLES]
    groupes += [g for g in COMPETENCES_DISPONIBLES if g not in groupes]

    pdf = CVPdf()
    pdf.add_page()
    pdf.entete(contenu.get("tagline", "Data Science • IA Générative & Agentique • Machine Learning"))

    pdf.section("Profil")
    pdf.paragraphe(contenu.get("profil", ""))

    pdf.section("Projets Data Science & IA")
    for p in projets:
        pdf.projet(p)

    pdf.section("Compétences techniques")
    for g in groupes:
        pdf.ligne_bullet(g, COMPETENCES_DISPONIBLES[g])
    pdf.ln(1)

    pdf.section("Soft skills")
    for s in SOFT_SKILLS:
        pdf.ligne_bullet(s)
    pdf.ln(1)

    pdf.section("Expérience & Leadership")
    for exp in EXPERIENCES:
        pdf.experience_bloc(exp)

    pdf.section("Formation")
    for f in FORMATION:
        pdf.ligne_bullet(f)
    pdf.ln(1)

    pdf.section("Certifications & Langues")
    for c in CERTIFICATIONS:
        pdf.ligne_bullet(c)
    pdf.ligne_bullet(LANGUES)

    os.makedirs(dossier_sortie, exist_ok=True)
    nom_fichier = re.sub(r"[^\w\-]+", "_", offre.get("company", "entreprise")).strip("_")
    chemin = os.path.join(dossier_sortie, f"CV_NOUMAGNO_{nom_fichier}.pdf")
    pdf.output(chemin)
    print(f"✅ CV adapté généré (1 page A4) : {chemin}")
    return chemin
