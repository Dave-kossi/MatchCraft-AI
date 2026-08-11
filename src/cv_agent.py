import json
import os
import re
import unicodedata
from fpdf import FPDF
from fpdf.enums import XPos, YPos
import matplotlib
import groq

# ==========================================
# 0. CONFIGURATION & DONNÉES CIBLE (FIGÉES)
# ==========================================

CANDIDAT = {
    "nom": "Kossi NOUMAGNO",
    "titre": "Ingénieur IA & Data Science",
    "contact": "Echirolles (38130) | 07 43 28 89 25 | davekossia23@gmail.com",
    "liens": [
        ("LinkedIn", "https://www.linkedin.com/in/kossi-noumagno"),
        ("GitHub", "https://github.com/Dave-kossi"),
        ("Portfolio", "https://dave-kossi.github.io/kossi-NOUMAGNO/"),
    ],
}

# Catalogue complet des projets - Le LLM choisit et ordonne UNIQUEMENT parmi ceux-ci
CATALOGUE_PROJETS = {
    "CV_Agent": {
        "titre": "Agent IA Générateur de Candidatures Ciblées (CV & LM) — Groq, Llama-3, Python",
        "description": "Conception d'un agent IA autonome analysant une offre d'emploi, adaptant un CV sur-mesure (catalogue fermé) et rédigeant une LM percutante.",
        "points": [
            "Architecture basée sur Groq API (Llama-3-8b-8192) avec réponse JSON structurée et validation par Pydantic.",
            "Génération PDF automatisée avec FPDF2 (mise en page stricte 1-page, gestion typographique dynamique).",
            "Moteur de matching sémantique calculant le taux d'adéquation et isolant les compétences clés de l'offre."
        ]
    },
    "Detection_Deepfake": {
        "titre": "Détection de Deepfakes & Falsifications Audio/Vidéo par Deep Learning — PyTorch, CNN, ViT",
        "description": "Développement d'un pipeline de détection d'anomalies visuelles et acoustiques générées par IA (FaceForensics++, ASVspoek).",
        "points": [
            "Entraînement de modèles hybrides Vision Transformer (ViT) + EfficientNet pour repérer les artéfacts spectraux et spatiaux.",
            "Pipeline d'extraction de caractéristiques audio (MFCC, Spectrogrammes) couplé à un ResNet 1D (Précision: 94.2%).",
            "Mise en production d'une interface d'analyse en temps réel avec Streamlit et FastAPI."
        ]
    },
    "IA_Sante_Tumeur": {
        "titre": "Segmentation Automatique de Tumeurs Cérébrales (BraTS) — U-Net, PyTorch, MONAI",
        "description": "Modèle de segmentation sémantique 3D pour la détection de gliomes à partir d'imagerie par résonance magnétique (IRM).",
        "points": [
            "Implémentation de architectures U-Net 3D et SegResNet sous MONAI, optimisées pour la mémoire GPU.",
            "Score Dice atteint de 0.88 sur l'œdème et le cœur tumoral grâce à des techniques d'augmentation avancées.",
            "Visualisation interactive des volumes 3D segmentés via Plotly et Trame."
        ]
    },
    "Chatbot_RAG_Entreprise": {
        "titre": "Assistant RAG Souverain pour Documentation Technique — LangChain, ChromaDB, Ollama",
        "description": "Système de recherche documentaire intelligente en local (Privacy-First) alimenté par un LLM open-source.",
        "points": [
            "Indexation vectorielle de plus de 500 documents PDF/Markdown via ChromaDB et BGE-Embeddings.",
            "Optimisation du RAG avec Hybrid Search (BM25 + Dense Retrieval) et Re-ranking par Cohere.",
            "Déploiement local sécurisé sous Docker avec Ollama (Llama-3-8B) sans fuite de données."
        ]
    }
}

CATALOGUE_FORMATIONS = [
    {
        "diplome": "Master 2 Informatique & Data Science",
        "ecole": "Université Grenoble Alpes",
        "annee": "2023 - 2024",
        "details": "Machine Learning, Deep Learning, NLP, Computer Vision, MLOps."
    },
    {
        "diplome": "Licence Informatique",
        "ecole": "Université de Lomé",
        "annee": "2019 - 2022",
        "details": "Algorithmique, Bases de Données, Génie Logiciel, Mathématiques Appliquées."
    }
]

# ==========================================
# 1. MOTEUR PDF (FPDF2) AVEC SUPPORT UTF-8
# ==========================================

class PDFCV(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_margins(10, 8, 10)
        self.set_auto_page_break(auto=True, margin=8)
        
        # Configuration des polices UTF-8
        self.font_utf8 = False
        self._charger_police_unicode()

    def _charger_police_unicode(self):
        """Tente de charger une police TrueType système pour un rendu UTF-8 propre."""
        try:
            # Recherche DejaVuSans via matplotlib si dispo
            font_path = matplotlib.font_manager.findfont('DejaVu Sans')
            if os.path.exists(font_path):
                self.add_font("DejaVu", "", font_path)
                self.add_font("DejaVu", "B", font_path)
                self.font_utf8 = True
                return
        except Exception:
            pass

        # Chemins standards sous Linux/Debian/Ubuntu
        chemins_possibles = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans.ttf"
        ]
        for path in chemins_possibles:
            if os.path.exists(path):
                path_bold = path.replace(".ttf", "-Bold.ttf")
                self.add_font("DejaVu", "", path)
                if os.path.exists(path_bold):
                    self.add_font("DejaVu", "B", path_bold)
                else:
                    self.add_font("DejaVu", "B", path)
                self.font_utf8 = True
                return

    def config_font(self, style="", size=10):
        if self.font_utf8:
            self.set_font("DejaVu", style, size)
        else:
            self.set_font("Helvetica", style, size)

    def clean_text(self, text: str) -> str:
        if self.font_utf8:
            return text
        # Fallback pour police standard Helvetica (Latin-1)
        text = text.replace("•", "-")
        text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8')
        return text

    def get_bullet_char(self) -> str:
        """Retourne une puce adaptée à la police disponible."""
        return "\u2022 " if self.font_utf8 else "- "

    def entete(self, profil_accorche: str):
        self.config_font("B", 18)
        self.set_text_color(20, 40, 80)
        self.cell(0, 8, self.clean_text(CANDIDAT["nom"]), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")

        self.config_font("B", 12)
        self.set_text_color(70, 70, 70)
        self.cell(0, 6, self.clean_text(CANDIDAT["titre"]), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")

        self.config_font("", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, self.clean_text(CANDIDAT["contact"]), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")

        # Liens
        liens_str = " | ".join([f"{label}: {url}" for label, url in CANDIDAT["liens"]])
        self.cell(0, 5, self.clean_text(liens_str), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        self.ln(2)

        # Accroche / Profil
        if profil_accorche:
            self.config_font("I", 9.5)
            self.set_text_color(40, 40, 40)
            self.multi_cell(0, 4.5, self.clean_text(profil_accorche), align="C")
            self.ln(3)

    def section_title(self, title: str):
        self.config_font("B", 11)
        self.set_text_color(20, 40, 80)
        self.cell(0, 6, self.clean_text(title.upper()), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(20, 40, 80)
        self.set_line_width(0.4)
        self.line(self.get_x(), self.get_y(), self.get_x() + 190, self.get_y())
        self.ln(2)

    def ajouter_projet(self, key_projet: str):
        if key_projet not in CATALOGUE_PROJETS:
            return

        p = CATALOGUE_PROJETS[key_projet]
        self.config_font("B", 10)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 5, self.clean_text(p["titre"]))

        self.config_font("I", 9)
        self.set_text_color(80, 80, 80)
        self.multi_cell(0, 4.5, self.clean_text(p["description"]))

        self.config_font("", 8.5)
        self.set_text_color(50, 50, 50)
        bullet = self.get_bullet_char()
        for point in p["points"]:
            self.multi_cell(0, 4, self.clean_text(f"{bullet}{point}"))
        self.ln(2)

    def ajouter_formations(self):
        self.section_title("Formations")
        for f in CATALOGUE_FORMATIONS:
            self.config_font("B", 9.5)
            self.set_text_color(30, 30, 30)
            self.cell(140, 5, self.clean_text(f["diplome"]), new_x=XPos.RIGHT, new_y=YPos.TOP)
            
            self.config_font("I", 9)
            self.cell(50, 5, self.clean_text(f["annee"]), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="R")

            self.config_font("", 9)
            self.set_text_color(80, 80, 80)
            self.cell(0, 4.5, self.clean_text(f"{f['ecole']} — {f['details']}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(1.5)

    def ajouter_competences(self, competences_cles: list):
        self.section_title("Compétences Clés")
        self.config_font("", 9)
        self.set_text_color(40, 40, 40)
        comps_str = " • ".join(competences_cles)
        self.multi_cell(0, 4.5, self.clean_text(comps_str))


# ==========================================
# 2. LOGIQUE AGENT (GROQ & MATCHING)
# ==========================================

def _appel_groq_json(prompt: str) -> dict:
    """Effectue un appel Groq en forçant le format JSON."""
    client = groq.Groq(api_key=os.environ.get("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "Tu es un expert RH et relecteur de CV. Tu réponds STRICTEMENT un objet JSON valide."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.2
    )
    return json.loads(response.choices[0].message.content)


def _selectionner_contenu_cv(offre: dict, analyse_matching: dict | None = None) -> dict:
    """Interroge Llama-3 pour sélectionner les projets les plus pertinents et rédiger l'accroche."""
    
    projets_dispo_str = json.dumps(CATALOGUE_PROJETS, ensure_ascii=False, indent=2)
    matching_info = json.dumps(analyse_matching, ensure_ascii=False) if analyse_matching else "Non fournie"

    prompt = f"""
    SITUATION:
    Un candidat postule à une offre d'emploi. Tu dois adapter son CV pour maximiser son score ATS.

    DONNÉES CIBLE DE L'OFFRE:
    - Intitulé: {offre.get('titre', 'Non spécifié')}
    - Entreprise: {offre.get('entreprise', 'Non spécifiée')}
    - Description/Besoins: {offre.get('description', '')[:1000]}
    - Analyse de Matching pré-calculée: {matching_info}

    CATALOGUE DE PROJETS DISPONIBLES:
    {projets_dispo_str}

    CONSIGNES STRICTES:
    1. Sélectionne entre 2 et 3 projets du catalogue qui répondent LE MIEUX aux exigences de l'offre.
    2. Ordonne les clés de ces projets par ordre de pertinence décroissante.
    3. Rédige un paragraphe de profil/d'accroche ultra-percutant (2 PHRASES MAXIMUM, STRICTEMENT MOINS DE 200 CARACTÈRES).
    4. Propose une liste optimisée de 6 à 10 compétences clés adaptées à l'offre.

    FORMAT DE RÉPONSE EXIGÉ (JSON STRICT):
    {{
      "tagline": "Description/Accroche en 2 phrases max...",
      "projets_ordonnes": ["Nom_Clé_Projet_1", "Nom_Clé_Projet_2"],
      "competences_cles": ["Python", "PyTorch", "RAG", ...]
    }}
    """

    try:
        res = _appel_groq_json(prompt)
        # Validation des clés minimales
        if "projets_ordonnes" in res and "tagline" in res and "competences_cles" in res:
            return res
        raise KeyError("Clés manquantes dans le JSON retourné")
    except Exception as e:
        print(f"⚠️ Erreur sélection contenu CV ({e}) — utilisation du fallback.")
        return {
            "tagline": f"Ingénieur IA & Data Science passionné par le déploiement de solutions d'IA générative et de Deep Learning appliquées aux défis de {offre.get('entreprise', 'l\'entreprise')}.",
            "projets_ordonnes": list(CATALOGUE_PROJETS.keys())[:3],
            "competences_cles": ["Python", "PyTorch", "Deep Learning", "NLP", "LLM", "Docker", "Git"]
        }


def generer_cv_pdf(offre: dict, analyse_matching: dict | None = None, output_path: str = "CV_Kossi_NOUMAGNO.pdf") -> str:
    """Génère le PDF du CV adapté à l'offre."""
    
    # 1. Sélection intelligente par le LLM
    selection = _selectionner_contenu_cv(offre, analyse_matching)

    # 2. Instanciation PDF
    pdf = PDFCV()
    pdf.add_page()

    # 3. Entête & Profil
    pdf.entete(selection.get("tagline", ""))

    # 4. Compétences
    comps = selection.get("competences_cles", ["Python", "PyTorch", "NLP", "Docker"])
    pdf.ajouter_competences(comps)
    pdf.ln(2)

    # 5. Projets sélectionnés
    pdf.section_title("Projets & Réalisations Clés")
    projets_a_inclure = selection.get("projets_ordonnes", [])
    
    # Sécurité au cas où le LLM renvoie des clés invalides
    projets_valides = [k for k in projets_a_inclure if k in CATALOGUE_PROJETS]
    if not projets_valides:
        projets_valides = list(CATALOGUE_PROJETS.keys())[:2]

    for key in projets_valides:
        pdf.ajouter_projet(key)

    # 6. Formations
    pdf.ajouter_formations()

    # Output
    pdf.output(output_path)
    print(f"✅ CV généré avec succès : {output_path}")
    return output_path


# ==========================================
# 3. PIPELINE COMPLET (INTEGRATION AGENT)
# ==========================================

def generer_candidature_complete(texte_offre: str, output_prefix: str = "Candidature") -> dict:
    """
    Pipeline global : 
    1. Analyse l'offre d'emploi & calcule le matching (via agent.py).
    2. Génère le CV PDF sur-mesure (via cv_agent.py).
    3. Rédige la lettre de motivation (via agent.py).
    """
    # Importation retardée (lazy) pour éviter les imports circulaires
    try:
        from agent import _extraire_et_matcher, analyser_et_rediger
    except ImportError:
        raise ImportError("Le module `agent.py` est requis pour exécuter le pipeline complet.")

    print("🔍 Analyse de l'offre et calcul du matching...")
    analyse_matching = _extraire_et_matcher(texte_offre)
    
    offre_info = {
        "titre": analyse_matching.get("titre_poste", "Poste IA"),
        "entreprise": analyse_matching.get("entreprise", "Entreprise"),
        "description": texte_offre
    }

    # Génération du CV
    cv_filename = f"{output_prefix}_CV.pdf"
    print("📄 Génération du CV PDF sur-mesure...")
    generer_cv_pdf(offre_info, analyse_matching, output_path=cv_filename)

    # Génération de la Lettre de Motivation
    print("✉️ Rédaction de la Lettre de Motivation...")
    resultat_lm = analyser_et_rediger(texte_offre)

    return {
        "analyse": analyse_matching,
        "cv_pdf": cv_filename,
        "lettre_motivation": resultat_lm.get("lettre_motivation", "")
    }


# ==========================================
# 4. EXÉCUTION / TEST AUTONOME
# ==========================================

if __name__ == "__main__":
    # Test autonome du module
    test_offre = {
        "titre": "Ingénieur IA & LLM",
        "entreprise": "TechCorp",
        "description": "Nous recherchons un Ingénieur IA spécialisé dans le déploiement d'agents RAG et de modèles de Deep Learning sous PyTorch. Expérience avec Docker et Groq appréciée."
    }

    print("🚀 Test d'exécution autonome de cv_agent.py...")
    generer_cv_pdf(test_offre, output_path="Test_CV_Kossi.pdf")
