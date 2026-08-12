import streamlit as st
from src.historique import (
    charger_historique,
    sauvegarder_historique,
    supprimer_offre_par_id,
    nettoyer_offres_obsoletes
)

st.set_page_config(
    page_title="MatchCraft AI — Dashboard",
    page_icon="💼",
    layout="wide"
)

# Nettoyage automatique unique au démarrage de la session Streamlit
if "nettoyage_effectue" not in st.session_state:
    nettoyer_offres_obsoletes(max_jours=2)
    st.session_state["nettoyage_effectue"] = True

st.title("💼 MatchCraft AI — Gestionnaire de Candidatures")

# Barre latérale : Actions globales
st.sidebar.header("⚙️ Actions & Filtres")

if st.sidebar.button("🧹 Lancer un nettoyage manuel (> 2 jours)"):
    nettoyer_offres_obsoletes(max_jours=2)
    st.sidebar.success("Nettoyage effectué et synchronisé !")
    st.rerun()

# Chargement des données
historique = charger_historique()

# Statistiques clés
col1, col2, col3 = st.columns(3)
col1.metric("Total des offres", len(historique))
col2.metric("À postuler", sum(1 for o in historique if o.get("statut") == "A postuler"))
col3.metric("Postulées / Entretiens", sum(1 for o in historique if o.get("statut") in ["Postulé", "Entretien"]))

st.divider()

# Affichage des cartes d'offres
if not historique:
    st.info("Aucune offre disponible dans l'historique.")
else:
    for idx, offre in enumerate(historique):
        with st.expander(
            f"📌 {offre.get('title', 'Titre non spécifié')} — {offre.get('company', 'Entreprise inconnue')} "
            f"| Score : {offre.get('score_adequation', 0)}%"
        ):
            col_info, col_actions = st.columns([3, 1])

            with col_info:
                st.markdown(f"**🎯 Besoin clé identifié :** {offre.get('besoin_cle_entreprise', 'N/A')}")
                st.markdown(f"**🛠️ Projets mis en valeur :** {offre.get('preuve_technique_citee', 'Aucun')}")
                
                points_forts = offre.get("points_forts", [])
                if points_forts:
                    st.markdown("**⭐ Points forts :** " + ", ".join(points_forts))

            with col_actions:
                # Gestion du statut de candidature
                statuts_possibles = ["A postuler", "Postulé", "Entretien", "Refusé"]
                statut_actuel = offre.get("statut", "A postuler")
                index_defaut = statuts_possibles.index(statut_actuel) if statut_actuel in statuts_possibles else 0

                nouveau_statut = st.selectbox(
                    "Statut :",
                    statuts_possibles,
                    index=index_defaut,
                    key=f"statut_select_{idx}"
                )

                if nouveau_statut != statut_actuel:
                    historique[idx]["statut"] = nouveau_statut
                    sauvegarder_historique(
                        historique,
                        synchroniser_github=True,
                        message_commit=f"Statut mis à jour : {offre.get('title')} -> {nouveau_statut}"
                    )
                    st.success("Statut mis à jour !")
                    st.rerun()

                # Bouton de suppression
                if st.button("❌ Supprimer", key=f"btn_suppr_{idx}"):
                    supprimer_offre_par_id(offre.get("id"))
                    st.warning("Offre supprimée !")
                    st.rerun()

            # Affichage de la lettre de motivation
            st.subheader("✉️ Lettre de Motivation Générée")
            lettre = offre.get("lettre_motivation", "Aucune lettre générée.")
            st.text_area(
                label="Contenu de la lettre",
                value=lettre,
                height=280,
                key=f"lettre_area_{idx}"
            )
