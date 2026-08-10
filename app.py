import os
import streamlit as st

from src.historique import (
    JOURS_RETENTION_MAX,
    charger_historique,
    formater_date_affichage,
    sauvegarder_historique,
    separer_recentes_obsoletes,
)

st.set_page_config(
    page_title="MatchCraft AI",
    page_icon="💼",
    layout="wide"
)

# ==========================================
# CHARGEMENT & BARRE DE FILTRES
# ==========================================
offres_brutes = charger_historique()

st.title("💼 MatchCraft AI — Tableau de bord")
st.markdown("Explore et gère tes opportunités qualifiées par l'IA (stages & alternances Data Science, Analytics, ML, LLM, AI Engineering).")

# --- CONTRÔLES DE RECHERCHE ET TRI ---
with st.container():
    col_search, col_source, col_sort = st.columns([2, 1, 1])

    search_query = col_search.text_input(
        "🔍 Rechercher (Entreprise, Titre, Compétence...)",
        placeholder="Ex: Sephora, Python, NLP..."
    )

    sources = ["Toutes"] + sorted({o.get("source", "Inconnue") for o in offres_brutes})
    selected_source = col_source.selectbox("🌐 Provenance", sources)

    sort_option = col_sort.selectbox(
        "🔀 Trier par",
        ["Plus récents d'abord", "Plus anciens d'abord", "Meilleur score IA"]
    )

# --- APPLICATION DES FILTRES ---
offres_filtrees = offres_brutes.copy()

if search_query:
    q = search_query.lower()
    offres_filtrees = [
        o for o in offres_filtrees
        if q in o.get("title", "").lower()
        or q in o.get("company", "").lower()
        or q in str(o.get("analyse", {})).lower()
    ]

if selected_source != "Toutes":
    offres_filtrees = [o for o in offres_filtrees if o.get("source", "Inconnue") == selected_source]

if sort_option == "Plus récents d'abord":
    offres_filtrees.sort(key=lambda x: x.get("date_ajout", ""), reverse=True)
elif sort_option == "Plus anciens d'abord":
    offres_filtrees.sort(key=lambda x: x.get("date_ajout", ""), reverse=False)
elif sort_option == "Meilleur score IA":
    offres_filtrees.sort(key=lambda x: x.get("analyse", {}).get("score_adequation", 0), reverse=True)

st.divider()

# ==========================================
# ONGLETS DE L'APPLICATION
# ==========================================
tab_offres, tab_sources, tab_gestion = st.tabs([
    f"Offres Qualifiées ({len(offres_filtrees)})",
    "Provenance & Stats",
    "⚙️ Gestion & Purge"
])

# ------------------------------------------
# ONGLET 1 : LES OFFRES
# ------------------------------------------
with tab_offres:
    if not offres_filtrees:
        st.info("Aucune offre ne correspond à tes critères actuels.")
    else:
        for idx, item in enumerate(offres_filtrees):
            analyse = item.get("analyse", {})
            score = analyse.get("score_adequation", 0)
            source = item.get("source", "Source inconnue")
            date_affichee = formater_date_affichage(item.get("date_ajout"))
            cv_pdf_path = item.get("cv_pdf_path")

            badge_score = "🟢" if score >= 80 else "🟠"
            item_id = item.get("id")

            with st.expander(f"{badge_score} **{item.get('title')}** — {item.get('company')} | {score}% Match ({source})"):
                c1, c2, c3 = st.columns(3)
                c1.caption(f"📅 Ajoutée le : **{date_affichee}**")
                c2.caption(f"🌐 Source : **{source}**")
                c3.markdown(f"🔗 [Ouvrir l'offre sur le site]({item.get('url')})")

                st.markdown("---")

                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    st.markdown("**Besoin clé :**")
                    st.write(analyse.get("besoin_cle_entreprise", "Non précisé"))
                    st.markdown("**Preuve technique :**")
                    st.write(analyse.get("preuve_technique_citee", "Non précisée"))

                with col_b2:
                    st.markdown("**💪 Points forts :**")
                    pts = analyse.get("points_forts", [])
                    if isinstance(pts, list):
                        for p in pts:
                            st.write(f"- {p}")
                    else:
                        st.write(pts)

                st.markdown("---")
                
                # --- ACTIONABLE OUTPUTS : CV PDF & LETTRE ---
                col_act_cv, col_act_lettre = st.columns([1, 2])
                
                with col_act_cv:
                    st.markdown("### 📄 CV Optimisé")
                    if cv_pdf_path and os.path.exists(cv_pdf_path):
                        with open(cv_pdf_path, "rb") as pdf_file:
                            st.download_button(
                                label="📥 Télécharger le CV (PDF)",
                                data=pdf_file,
                                file_name=os.path.basename(cv_pdf_path),
                                mime="application/pdf",
                                key=f"dl_cv_{item_id}_{idx}",
                                use_container_width=True
                            )
                    else:
                        st.caption("⚠️ Aucun fichier CV généré pour cette offre.")

                with col_act_lettre:
                    st.markdown("### ✉️ Lettre de motivation")
                    lettre_texte = analyse.get("lettre_motivation", "Lettre non disponible.")
                    st.info(lettre_texte)

                st.markdown("---")

                # Suppression sécurisée
                if item_id and st.button("🗑️ Supprimer cette offre", key=f"del_{item_id}_{idx}"):
                    nouvelles_offres = [o for o in offres_brutes if o.get('id') != item_id]
                    sauvegarder_historique(nouvelles_offres)
                    st.success("Offre retirée de la base de données.")
                    st.rerun()
                elif not item_id:
                    st.caption("⚠️ Cette entrée n'a pas d'identifiant valide — suppression désactivée par sécurité.")

# ------------------------------------------
# ONGLET 2 : STATISTIQUES DE PROVENANCE
# ------------------------------------------
with tab_sources:
    st.header("Statistiques par plateforme")
    if offres_brutes:
        counts = {}
        for o in offres_brutes:
            s = o.get("source", "Autre")
            counts[s] = counts.get(s, 0) + 1

        cols = st.columns(max(len(counts), 1))
        for idx, (src_name, count) in enumerate(counts.items()):
            cols[idx].metric(f"Offres {src_name}", count)
    else:
        st.write("Aucune offre disponible en mémoire.")

# ------------------------------------------
# ONGLET 3 : CENTRE DE PURGE
# ------------------------------------------
with tab_gestion:
    st.header("⚙️ Centre de maintenance & Purge mémoire")
    st.write("Utilise ces options pour libérer la mémoire JSON et ne garder que les données récentes.")

    offres_recentes, offres_obsoletes = separer_recentes_obsoletes(offres_brutes, JOURS_RETENTION_MAX)

    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Stock total en base", len(offres_brutes))
    col_m2.metric(f"Moins de {JOURS_RETENTION_MAX} jours", len(offres_recentes))
    col_m3.metric("Obsolètes", len(offres_obsoletes))

    st.markdown("---")

    col_act1, col_act2 = st.columns(2)

    with col_act1:
        st.subheader(f"🧹 Purge programmée ({JOURS_RETENTION_MAX} jours)")
        st.caption(f"Supprime immédiatement les offres datant de plus de {JOURS_RETENTION_MAX * 24} heures.")
        if st.button("Purger les offres obsolètes", type="primary", use_container_width=True):
            sauvegarder_historique(offres_recentes)
            st.success(f"Purge réussie : {len(offres_obsoletes)} offre(s) supprimée(s) !")
            st.rerun()

    with col_act2:
        st.subheader("⚠️ Réinitialisation complète")
        st.caption("Vide totalement la base de données JSON.")
        with st.popover("Vider l'historique complet"):
            st.warning("Attention : cette action effacera absolument toutes les offres en mémoire.")
            if st.button("Confirmer l'effacement total", use_container_width=True):
                sauvegarder_historique([])
                st.success("La base de données a été réinitialisée.")
                st.rerun()
