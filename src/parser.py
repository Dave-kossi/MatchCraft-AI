import os
from pypdf import PdfReader
from bs4 import BeautifulSoup

'''def lire_cv_pdf(chemin_pdf: str) -> str:
    """Extrait le texte brut du CV PDF."""
    if not os.path.exists(chemin_pdf):
        return "CV non trouvé."
    reader = PdfReader(chemin_pdf)
    texte = ""
    for page in reader.pages:
        texte += page.extract_text() or ""
    return texte'''

def lire_portfolio_html(chemin_html: str) -> str:
    """Extrait et nettoie le texte du Portfolio HTML."""
    if not os.path.exists(chemin_html):
        return "Portfolio non trouvé."
    with open(chemin_html, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    
    # Suppression des balises inutiles
    for element in soup(["script", "style", "nav", "footer"]):
        element.decompose()
        
    return soup.get_text(separator=" ", strip=True)
