import os
import json
import streamlit as st
from datetime import datetime, timedelta

CHEMIN_HISTORIQUE = "data/historique.json"

st.set_page_config(
    page_title="MatchCraft AI — Tableau de bord",
    page_icon="💼",
    layout="wide"
)

# ==========================================
# FONCTIONS DE GESTION DES DONNÉES
# ==========================================
def charger_historique() -> list:
    if os.path.exists(CHEMIN_HISTORIQUE):
        try:
            with open(CHEMIN_HISTORIQUE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def sauvegarder_historique(data: list):
    os.makedirs(os.path.dirname(CHEMIN_HISTORIQUE), exist_ok=True)
    with open(CHEMIN_HISTORIQUE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def extraire_donnees_offre(item: dict) -> dict:
    """
    Extrait harmonieusement les champs qu'ils soient imbriqués dans 
    item['analyse'] ou directement à la racine de l'objet.
    """
    analyse = item.get("analyse", {})
    if not isinstance(analyse, dict):
        analyse = {}

    score = analyse.get("score_adequation") or item.get("score_adequation", 0)
    besoin = analyse.get("besoin_cle_entreprise") or item.get("besoin_cle_entreprise", "Non précisé")
    preuve = analyse.get("preuve_technique_citee") or item.get("preuve_technique_citee", "Non précisée")
    points = analyse.get("points_forts") or item.get("points_forts", [])
    lettre = analyse.get("lettre_motivation") or item.get("lettre_motivation", "Lettre non disponible.")

    return {
        "score": score,
        "besoin": besoin,
        "preuve": preuve,
        "points": points,
        "lettre": lettre
    }

# ==========================================
# CHARGEMENT & FILTRES
# ==========================================
offres_brutes = charger_historique()

st.title("💼 MatchCraft AI — Tableau de bord")
st.markdown("Explore et gère tes opportunités qualifiées par l'IA.")

# --- BARRE DE FILTRES ET TRI (Haut de page) ---
with st.container():
    col_search, col_source, col_sort = st.columns([2, 1, 1])

    # 1. Recherche par mot-clé (Métier, entreprise, technologie...)
    search_query = col_search.text_input(
        "🔍 Rechercher (Entreprise, Titre, Compétence...)", 
        placeholder="Ex: Data Scientist, Sephora, Python, NLP..."
    )

    # 2. Filtre par provenance / source
    sources_disponibles = ["Toutes"] + sorted(list(set([str(o.get("source", "Inconnue")) for o in offres_brutes])))
    selected_source = col_source.selectbox("🌐 Provenance", sources_disponibles)

    # 3. Tri
    sort_option = col_sort.selectbox(
        "🔀 Trier par", 
        ["Plus récents d'abord", "Plus anciens d'abord", "Meilleur score IA"]
    )

# --- APPLICATION DES FILTRES ---
offres_filtrees = offres_brutes.copy()

# Filtre Recherche
if search_query:
    q = search_query.lower()
    offres_filtrees = [
        o for o in offres_filtrees 
        if q in str(o.get("title", "")).lower() 
        or q in str(o.get("company", "")).lower()
        or q in str(o.get("description", "")).lower()
        or q in str(o.get("analyse", {})).lower()
    ]

# Filtre Source
if selected_source != "Toutes":
    offres_filtrees = [o for o in offres_filtrees if str(o.get("source", "Inconnue")) == selected_source]

# Tri
if sort_option == "Plus récents d'abord":
    offres_filtrees.sort(key=lambda x: str(x.get("date_ajout", "")), reverse=True)
elif sort_option == "Plus anciens d'abord":
    offres_filtrees.sort(key=lambda x: str(x.get("date_ajout", "")), reverse=False)
elif sort_option == "Meilleur score IA":
    offres_filtrees.sort(key=lambda x: extraire_donnees_offre(x)["score"], reverse=True)

st.divider()

# ==========================================
# ONGLETS DE NAVIGATION
# ==========================================
tab_offres, tab_sources, tab_gestion = st.tabs([
    f" Offres Qualifiées ({len(offres_filtrees)})", 
    " Provenance & Stats", 
    "⚙️ Gestion & Nettoyage"
])

# ------------------------------------------
# ONGLET 1 : LES OFFRES FILTRÉES
# ------------------------------------------
with tab_offres:
    if not offres_filtrees:
        st.info("Aucune offre ne correspond à tes critères de recherche.")
    else:
        for idx, item in enumerate(offres_filtrees):
            infos = extraire_donnees_offre(item)
            score = infos["score"]
            source = item.get("source", "Source inconnue")
            date_raw = item.get("date_ajout", "")

            # Formate la date
            if date_raw:
                try:
                    dt = datetime.fromisoformat(str(date_raw).split(".")[0])
                    date_affichee = dt.strftime("%d/%m/%Y à %H:%M")
                except ValueError:
                    date_affichee = "Date inconnue"
            else:
                date_affichee = "Date inconnue"

            badge_score = "🟢" if score >= 80 else "🟠"
            titre = item.get("title", "Sans titre")
            entreprise = item.get("company", "Entreprise inconnue")

            with st.expander(f"{badge_score} **{titre}** — {entreprise} | {score}% Match ({source})"):
                c1, c2, c3 = st.columns(3)
                c1.caption(f"📅 Ajoutée le : **{date_affichee}**")
                c2.caption(f"🌐 Provenance : **{source}**")
                
                url_job = item.get("url") or item.get("id")
                if url_job:
                    c3.markdown(f"🔗 [Consulter l'offre]({url_job})")

                st.markdown("---")

                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    st.markdown("**🎯 Besoin clé :**")
                    st.write(infos["besoin"])
                    st.markdown("**📌 Preuve technique :**")
                    st.write(infos["preuve"])

                with col_b2:
                    st.markdown("**💪 Points forts :**")
                    pts = infos["points"]
                    if isinstance(pts, list) and pts:
                        for p in pts:
                            st.write(f"- {p}")
                    elif isinstance(pts, str) and pts:
                        st.write(pts)
                    else:
                        st.write("Aucun point fort spécifique relevé.")

                st.markdown("---")
                st.markdown("### ✉️ Lettre de motivation générée")
                st.info(infos["lettre"])

# ------------------------------------------
# ONGLET 2 : STATISTIQUES & PROVENANCE
# ------------------------------------------
with tab_sources:
    st.header("📊 Répartition par Provenance")
    if offres_brutes:
        counts = {}
        for o in offres_brutes:
            s = str(o.get("source", "Autre"))
            counts[s] = counts.get(s, 0) + 1
        
        cols = st.columns(max(len(counts), 1))
        for idx, (src_name, count) in enumerate(counts.items()):
            cols[idx].metric(f"Offres {src_name}", count)
    else:
        st.write("Pas de données disponibles pour le moment.")

# ------------------------------------------
# ONGLET 3 : CENTRE DE PURGE
# ------------------------------------------
with tab_gestion:
    st.header("⚙️ Nettoyage de l'historique")
    st.write("Les offres datant de plus de **2 jours** peuvent être purgées afin d'alléger la base de données.")
    
    if st.button("🧹 Purger les offres obsolètes maintenant", type="primary"):
        limite = datetime.now() - timedelta(days=2)
        recentes = []
        
        for o in offres_brutes:
            d_str = o.get("date_ajout")
            if d_str:
                try:
                    dt = datetime.fromisoformat(str(d_str).split(".")[0])
                    if dt >= limite:
                        recentes.append(o)
                except ValueError:
                    recentes.append(o)
            else:
                recentes.append(o)
                
        sauvegarder_historique(recentes)
        st.success("Nettoyage manuel effectué !")
        st.rerun()
