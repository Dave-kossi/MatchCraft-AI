import streamlit as st
from src.historique import (
    charger_historique,
    purger_historique,
    sauvegarder_historique,
    supprimer_offre_par_id,
)

st.set_page_config(
    page_title="MatchCraft AI — Dashboard",
    page_icon="💼",
    layout="wide"
)

# Purge automatique silencieuse lors du chargement
historique = purger_historique(jours_max=2)

st.title("💼 MatchCraft AI — Gestionnaire de Candidatures")

# Barre latérale
st.sidebar.header("⚙️ Actions & Filtres")

if st.sidebar.button("🧹 Purger les offres expirées (> 2 jours)"):
    historique = purger_historique(jours_max=2)
    st.sidebar.success("Purge effectuée !")
    st.rerun()

# Métriques
col1, col2, col3 = st.columns(3)
col1.metric("Total des offres", len(historique))
col2.metric("À postuler", sum(1 for o in historique if o.get("statut") == "A postuler"))
col3.metric("Postulées / Entretiens", sum(1 for o in historique if o.get("statut") in ["Postulé", "Entretien"]))

st.divider()

if not historique:
    st.info("Aucune offre disponible pour le moment.")
else:
    for idx, offre in enumerate(historique):
        titre = offre.get("title", "Titre non spécifié")
        entreprise = offre.get("company", "Entreprise inconnue")
        score = offre.get("score_adequation", 0)

        with st.expander(f"📌 {titre} — {entreprise} | Score : {score}%"):
            c1, c2 = st.columns([3, 1])

            with c1:
                st.markdown(f"**🎯 Besoin clé :** {offre.get('besoin_cle_entreprise', 'N/A')}")
                st.markdown(f"**🛠️ Preuve technique :** {offre.get('preuve_technique_citee', 'Aucune')}")
                if offre.get("url"):
                    st.markdown(f"🔗 [Voir la fiche de poste]({offre.get('url')})")

            with c2:
                statuts = ["A postuler", "Postulé", "Entretien", "Refusé"]
                statut_courant = offre.get("statut", "A postuler")
                index_statut = statuts.index(statut_courant) if statut_courant in statuts else 0

                nouveau_statut = st.selectbox(
                    "Statut :",
                    statuts,
                    index=index_statut,
                    key=f"select_statut_{idx}"
                )

                if nouveau_statut != statut_courant:
                    historique[idx]["statut"] = nouveau_statut
                    sauvegarder_historique(historique)
                    st.success("Statut mis à jour !")
                    st.rerun()

                if st.button("❌ Supprimer", key=f"btn_del_{idx}"):
                    supprimer_offre_par_id(offre.get("id"))
                    st.warning("Offre supprimée !")
                    st.rerun()

            st.subheader("✉️ Lettre de Motivation")
            st.text_area(
                label="Lettre générée",
                value=offre.get("lettre_motivation", ""),
                height=250,
                key=f"txt_lettre_{idx}"
            )
