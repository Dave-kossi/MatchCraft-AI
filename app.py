# app.py
import json
import os
import streamlit as st

from src.github_writer import sauvegarder_historique_sur_github

CHEMIN_HISTORIQUE = "data/historique.json"

st.set_page_config(
    page_title="MatchCraft AI Dashboard",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 Dashboard de Candidature - MatchCraft AI")
st.markdown("Consultez les offres analysées et retenues par votre agent IA.")


@st.cache_data(ttl=60)
def charger_offres():
    if os.path.exists(CHEMIN_HISTORIQUE):
        with open(CHEMIN_HISTORIQUE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


offres = charger_offres()

# On ne montre que les offres pas encore marquées comme "postulée"
offres_actives = [o for o in offres if o.get('statut', 'nouvelle') != 'postulee']

if not offres_actives:
    st.info("Aucune offre active pour le moment. L'agent continue de tourner...")
else:
    col_search, col_score = st.columns([2, 1])
    with col_search:
        recherche = st.text_input("🔍 Rechercher une entreprise ou un poste...")
    with col_score:
        score_min = st.slider("Score d'adéquation minimum (%)", 0, 100, 70)

    offres_filtrees = [
        o for o in offres_actives
        if o.get('analyse', {}).get('score_adequation', 0) >= score_min
        and (recherche.lower() in o.get('title', '').lower() or recherche.lower() in o.get('company', '').lower())
    ]

    st.write(f"### 📋 {len(offres_filtrees)} offre(s) qualifiée(s) trouvée(s)")

    for item in offres_filtrees:
        analyse = item.get('analyse', {})
        score = analyse.get('score_adequation', 0)
        badge_color = "🟢" if score >= 80 else "🟡"

        with st.expander(f"{badge_color} **{item.get('title')}** chez **{item.get('company')}** — Match: **{score}%**"):
            col1, col2 = st.columns([1, 1])

            with col1:
                st.write("**🎯 Besoin clé détecté :**", analyse.get('besoin_cle_entreprise', 'N/A'))
                st.write("**📌 Preuve technique retenue :**", analyse.get('preuve_technique_citee', 'N/A'))
                st.write("**💪 Points forts :**", ", ".join(analyse.get('points_forts', [])))
                st.link_button("🚀 Voir l'offre & Postuler", item.get('url'))

                if st.button("✅ Marquer comme postulée", key=f"postule_{item.get('id')}"):
                    for o in offres:
                        if o.get('id') == item.get('id'):
                            o['statut'] = 'postulee'
                    if sauvegarder_historique_sur_github(offres):
                        st.cache_data.clear()
                        st.success("Offre marquée comme postulée ✅")
                        st.rerun()
                    else:
                        st.error("⚠️ Échec de la sauvegarde sur GitHub — vérifie le secret GITHUB_TOKEN.")

            with col2:
                st.write("**📝 Lettre de motivation générée :**")
                st.text_area(
                    label="Lettre",
                    value=analyse.get('lettre_motivation', ''),
                    height=180,
                    key=item.get('id')
                )
