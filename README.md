# MatchCraft AI

**Un pipeline LLM qui scanne en continu les offres de stage et d'alternance en France (Data Science, Analytics, ML, LLM, AI Engineering) et rédige, pour chaque offre pertinente, une lettre de motivation personnalisée — ancrée dans des preuves réelles, jamais générique.**

Développé par [Kossi Noumagno](https://www.linkedin.com/in/kossi-noumagno), étudiant en Master 2 Ingénierie Mathématique & Data Science à l'Université de Haute-Alsace.

---

## Pourquoi ce projet

Chercher un stage ou une alternance, c'est répéter la même corvée des dizaines de fois : parcourir plusieurs jobboards, ouvrir chaque offre, évaluer si elle correspond à son profil, puis réécrire une lettre de motivation adaptée à chaque entreprise. C'est long, répétitif, et le résultat est souvent une lettre plus générique que ce qu'on voudrait.

MatchCraft AI automatise cette chaîne de bout en bout : veille multi-sources, filtrage par pertinence, puis rédaction d'une lettre construite à partir de preuves vérifiables (CV, portfolio, projets GitHub) — jamais un projet inventé, jamais une compétence non étayée.

---

## Sommaire

- [Ce que fait le projet](#ce-que-fait-le-projet)
- [Architecture](#architecture)
- [Stack technique](#stack-technique)
- [Installation](#installation)
- [Configuration](#configuration)
- [Utilisation](#utilisation)
- [Automatisation](#automatisation)
- [Sources de données](#sources-de-données)
- [Limites connues](#limites-connues)
- [Roadmap & contribution](#roadmap--contribution)
- [Licence](#licence)

---

## Ce que fait le projet

1. **Collecte** des offres de stage et d'alternance sur plusieurs sources (jobboards agrégés + portails carrière de grands groupes), filtrées sur les domaines Data Science, Analytics, Machine Learning, LLM et AI Engineering.
2. **Pré-filtrage strict** : une offre n'est retenue que si elle correspond à la fois à un type de contrat ciblé (stage/alternance) et à un domaine technique ciblé, avec un matching par mots entiers pour éviter les faux positifs (ex : "ML" ne doit pas matcher dans "HTML").
3. **Matching intelligent** : pour chaque offre retenue, un LLM identifie l'enjeu métier réel de l'entreprise et sélectionne, parmi les projets du candidat, les deux plus pertinents à mettre en avant.
4. **Rédaction sur mesure** : génération d'une lettre de motivation complète, structurée, avec preuves techniques chiffrées — jamais de formule générique ("passionné depuis toujours", "candidat idéal"...).
5. **Auto-critique** : une seconde passe LLM note la lettre sur sa spécificité et la qualité des preuves citées ; en dessous d'un seuil, la lettre est régénérée avec un retour ciblé sur ce qui manquait.
6. **Restitution** : un tableau de bord Streamlit présente les offres qualifiées, leur score de correspondance, et la lettre générée — prête à copier.
7. **Automatisation complète** : le pipeline tourne plusieurs fois par jour via un cron GitHub Actions, sans intervention manuelle.

---

## Architecture

```
MatchCraft-AI/
├── .github/workflows/
│   └── agent_cron.yml          # Automatisation (cron GitHub Actions)
├── data/
│   ├── cv.pdf                  # CV du candidat (à fournir)
│   ├── portfolio.html          # Portfolio du candidat (à fournir)
│   ├── historique.json         # Offres qualifiées (généré)
│   └── offres_rejetees.json    # Offres déjà évaluées et écartées (généré)
├── src/
│   ├── agent.py                 # Matching + rédaction + auto-critique (LLM)
│   ├── scraper.py               # Collecte JobSpy (LinkedIn/Indeed/Google/Glassdoor) + Welcome to the Jungle
│   ├── company_scraper.py       # Collecte directe sur les portails carrière de grands groupes
│   ├── parser.py                # Lecture du CV (PDF) et du portfolio (HTML)
│   ├── github_parser.py         # Lecture des repos publics GitHub (README inclus)
│   └── historique.py            # Gestion et purge de l'historique des offres
├── app.py                       # Tableau de bord Streamlit
├── main.py                      # Point d'entrée du pipeline complet
└── requirements.txt
```

### Le pipeline LLM (`src/agent.py`)

Un point de vocabulaire volontairement précis : ce pipeline **n'est pas un agent autonome**. C'est une séquence fixe d'appels LLM orchestrée par du code Python déterministe — le modèle ne décide jamais lui-même d'appeler un outil ou de changer d'approche, c'est le code qui contrôle chaque étape :

```
Offre + Dossier candidat
        │
        ▼
┌───────────────────┐
│  1. Matching       │  Identifie l'enjeu métier de l'offre, sélectionne
│                    │  les 2 projets les plus pertinents du candidat
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  2. Rédaction      │  Génère la lettre complète, preuves techniques
│                    │  chiffrées, vocabulaire métier de l'offre
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  3. Auto-critique  │  Note /10 : absence de formules creuses,
│                    │  adaptation réelle à l'offre
└───────────────────┘
        │
   score < seuil ?
    │         │
   oui        non
    │         │
    ▼         ▼
Régénération   Lettre finale
avec retour
ciblé
```

---

## Stack technique

- **Langage** : Python 3.10
- **LLM** : [Groq](https://console.groq.com) (inférence rapide, tier gratuit exploitable) — vérifier la disponibilité des modèles au moment du déploiement, Groq déprécie régulièrement certains modèles avec un délai de préavis court
- **Collecte** : [JobSpy](https://github.com/speedyapply/JobSpy) (LinkedIn, Indeed, Google, Glassdoor), API interne Welcome to the Jungle, endpoints carrière publics de grands groupes
- **Traitement** : Pandas, BeautifulSoup, pypdf
- **Interface** : Streamlit
- **Automatisation** : GitHub Actions (cron)

---

## Installation

Prérequis : **Python 3.10**.

```bash
git clone https://github.com/Dave-kossi/MatchCraft-AI.git
cd MatchCraft-AI
python -m venv venv
source venv/bin/activate      # Windows : venv\Scripts\activate
pip install -r requirements.txt
```

---

## Configuration

### 1. Clé API Groq

Créer un compte sur [console.groq.com](https://console.groq.com), générer une clé API, puis créer un fichier `.env` à la racine :
```
GROQ_API_KEY=ta_clé_ici
```

### 2. Token GitHub (recommandé)

Sans token, l'API GitHub est limitée à 60 requêtes/heure. Avec un [Personal Access Token](https://github.com/settings/tokens) (scope `public_repo`), la limite passe à 5000 requêtes/heure :
```
GITHUB_TOKEN=ton_token_ici
```

### 3. Documents du candidat

Placer dans `data/` :
- `cv.pdf` — CV au format PDF texte (pas une image scannée)
- `portfolio.html` — export HTML du portfolio

### 4. Profil GitHub

Dans `main.py`, remplacer le nom d'utilisateur par le tien :
```python
github_texte = lire_profil_github("ton-username-github")
```

### 5. Cibles de recherche

Dans `src/scraper.py` : ajuster `SEARCH_TERMS` (intitulés recherchés, stage et alternance) et `CITIES` (villes ciblées).

Dans `main.py` : ajuster `MOTS_CLES_DOMAINE` (domaines techniques), `MOTS_CLES_CONTRAT` (types de contrat acceptés) et `SEUIL_SCORE_MIN` (score minimum de rétention, 0-100).

---

## Utilisation

Lancer une collecte + analyse complète :
```bash
python main.py
```

Lancer le tableau de bord :
```bash
streamlit run app.py
```

---

## Automatisation

Le workflow `.github/workflows/agent_cron.yml` exécute `main.py` plusieurs fois par jour et commit les résultats.

Pour l'activer sur un fork :
1. **Settings → Secrets and variables → Actions** : ajouter `GROQ_API_KEY` (le secret `GITHUB_TOKEN` est fourni automatiquement par GitHub Actions, rien à configurer manuellement).
2. **Settings → Actions → General → Workflow permissions** : activer "Read and write permissions", sinon le commit automatique des résultats échoue.
3. Connecter le repo à [Streamlit Community Cloud](https://streamlit.io/cloud) pour héberger gratuitement le tableau de bord.

---

## Sources de données

**Actives** :
- JobSpy — LinkedIn, Indeed, Google, Glassdoor
- BNP Paribas (portail carrière, endpoint direct)

**En pause** (code conservé, diagnostic déjà posé, désactivées du pipeline actif après échec constaté) :
- Welcome to the Jungle — réponses HTTP 202 systématiques (probable protection anti-bot)
- Airbus — échec de résolution DNS de l'ancien endpoint
- Thales — payload Workday obsolète (400)
- Société Générale — endpoint changé (404)

**Backlog à compléter** (`src/company_scraper.py` → `SOURCES_A_INTEGRER`) : une vingtaine d'entreprises réparties en Banque (Crédit Agricole, BPCE/Natixis, Crédit Mutuel, La Banque Postale), Assurance (AXA, Allianz France, Generali France, Covéa, MAIF, Groupama), Énergie (TotalEnergies, ENGIE, EDF/Enedis, Veolia, Suez) et Industrie (Renault, Safran, Dassault Systèmes, Alstom, Saint-Gobain, Schneider Electric, Michelin, Air Liquide). Chaque entrée liste l'URL du portail carrière ; l'ajout d'une source active nécessite d'identifier son endpoint JSON interne (F12 → onglet Réseau → Fetch/XHR) et d'écrire une fonction `_requete_xxx()` sur le modèle de celle de BNP Paribas. C'est la contribution la plus utile et la plus accessible pour un premier pull request.

---

## Limites connues

- Plusieurs sources utilisent des endpoints internes non documentés officiellement (Welcome to the Jungle, portails carrière des grands groupes) : ils peuvent changer sans préavis et casser la collecte pour cette source spécifiquement.
- LinkedIn, Indeed et Glassdoor limitent activement le scraping automatisé ; des recherches trop fréquentes peuvent être temporairement bloquées, en particulier depuis une IP cloud partagée (ex : runners GitHub Actions).
- Le nom d'utilisateur GitHub et les chemins CV/portfolio sont actuellement en dur dans `main.py` — les sortir dans un fichier de configuration est une amélioration prévue.
- L'extraction de texte PDF ne fonctionne que sur un CV en PDF texte, pas une image scannée.
- Ce pipeline **n'est pas un système agentique** au sens strict (voir [Architecture](#architecture)) — le vocabulaire est choisi pour rester exact.

---

## Roadmap & contribution

- [ ] Compléter le backlog de sources grands groupes (voir [Sources de données](#sources-de-données))
- [ ] Sortir la configuration candidat (GitHub, CV, portfolio) d'un fichier dédié plutôt que du code source
- [ ] Réparer ou remplacer les sources actuellement en pause
- [ ] Étendre la couverture géographique / linguistique au-delà de la France

Les contributions sont bienvenues : fork, branche, pull request avec une description claire du changement. Le backlog de sources ci-dessus est le point d'entrée le plus simple pour une première contribution.

---

## Licence

MIT — utilisation, modification et redistribution libres, y compris à des fins commerciales, sous réserve de conserver la mention de licence. *(à confirmer par le mainteneur avant publication du repo)*

---

<p align="center">
  <a href="https://www.linkedin.com/in/kossi-noumagno">LinkedIn</a> ·
  <a href="https://github.com/Dave-kossi">GitHub</a> ·
  <a href="https://dave-kossi.github.io/kossi-NOUMAGNO/">Portfolio</a>
</p>
