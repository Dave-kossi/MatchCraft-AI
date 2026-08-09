# 💼 MatchCraft AI

Un agent autonome qui scanne automatiquement le web à la recherche de **stages et alternances** en **Data Science, Analytics, Machine Learning, LLM et AI Engineering**, puis rédige pour chaque offre pertinente une **lettre de motivation personnalisée**, ancrée dans ton CV, ton portfolio et tes projets GitHub.

L'objectif : éviter à un étudiant ou un jeune diplômé de perdre des heures à scroller sur plusieurs sites d'offres, puis à réécrire une lettre de motivation générique pour chaque entreprise.

---

## Sommaire

- [Comment ça marche](#comment-ça-marche)
- [Architecture du projet](#architecture-du-projet)
- [Installation](#installation)
- [Configuration](#configuration)
- [Utilisation en local](#utilisation-en-local)
- [Automatisation avec GitHub Actions](#automatisation-avec-github-actions)
- [Tableau de bord Streamlit](#tableau-de-bord-streamlit)
- [Personnaliser le projet](#personnaliser-le-projet)
- [Limites connues](#limites-connues)
- [Contribuer](#contribuer)
- [Licence](#licence)

---

## Comment ça marche

Le pipeline s'exécute en 4 grandes étapes :

1. **Collecte** (`src/scraper.py`, `src/company_scraper.py`) — recherche des offres de stage et d'alternance sur plusieurs sources : JobSpy (LinkedIn, Indeed, Google), Welcome to the Jungle, Stage.fr, et directement sur les portails carrière de grands groupes (Airbus, Thales, Société Générale, BNP Paribas, Eiffage).
2. **Filtrage** (`main.py`) — ne conserve que les offres qui sont à la fois un stage/alternance ET dans le domaine Data Science / Analytics / ML / LLM / AI Engineering.
3. **Analyse & rédaction** (`src/agent.py`) — pour chaque offre retenue, un LLM (via l'API Groq) :
   - extrait les besoins explicites et implicites de l'entreprise,
   - rédige une lettre de motivation complète en s'appuyant sur ton CV, ton portfolio et tes repos GitHub (README inclus),
   - s'auto-évalue sur la spécificité et la véracité des preuves citées, et se corrige une fois si le résultat est jugé trop générique ou peu fiable.
4. **Restitution** (`app.py`) — un tableau de bord Streamlit affiche les offres qualifiées avec leur score de correspondance, le besoin clé identifié, et la lettre générée, prête à copier.

Le tout tourne automatiquement plusieurs fois par jour via un cron GitHub Actions — pas besoin de garder un ordinateur allumé.

---

## Architecture du projet

```
MatchCraft-AI/
├── .github/
│   └── workflows/
│       └── agent_cron.yml       # Automatisation (cron GitHub Actions)
├── data/
│   ├── cv.pdf                   # Ton CV (à fournir)
│   ├── portfolio.html           # Ton portfolio (à fournir)
│   ├── historique.json          # Offres qualifiées (généré automatiquement)
│   └── offres_rejetees.json     # Offres déjà évaluées et écartées (généré automatiquement)
├── src/
│   ├── agent.py                 # Extraction des besoins + rédaction + auto-critique (LLM)
│   ├── scraper.py               # Collecte JobSpy / Welcome to the Jungle / Stage.fr
│   ├── company_scraper.py       # Collecte directe sur les portails carrière des grands groupes
│   ├── parser.py                # Lecture du CV (PDF) et du portfolio (HTML)
│   ├── github_parser.py         # Lecture des repos publics GitHub (README inclus)
│   └── historique.py            # Gestion et purge de l'historique des offres
├── app.py                       # Tableau de bord Streamlit
├── main.py                      # Point d'entrée du pipeline complet
└── requirements.txt
```

---

## Installation

Prérequis : **Python 3.10**.

```bash
git clone https://github.com/<ton-compte>/MatchCraft-AI.git
cd MatchCraft-AI
python -m venv venv
source venv/bin/activate      # Windows : venv\Scripts\activate
pip install -r requirements.txt
```

---

## Configuration

### 1. Clé API Groq

Le projet utilise [Groq](https://console.groq.com) pour la génération de texte (gratuit avec des limites généreuses au moment de l'écriture).

- Crée un compte sur [console.groq.com](https://console.groq.com) et génère une clé API.
- En local, crée un fichier `.env` à la racine du projet :
  ```
  GROQ_API_KEY=ta_clé_ici
  ```

### 2. Token GitHub (recommandé)

Sans token, l'API GitHub est limitée à 60 requêtes/heure et le pipeline peut échouer silencieusement si tu as plusieurs projets à analyser. Avec un token, la limite passe à 5000 requêtes/heure.

- Génère un [Personal Access Token](https://github.com/settings/tokens) avec le scope `public_repo` (aucun scope supplémentaire n'est nécessaire).
- Ajoute-le à ton `.env` :
  ```
  GITHUB_TOKEN=ton_token_ici
  ```

### 3. Tes documents personnels

Place dans `data/` :
- `cv.pdf` — ton CV au format PDF (texte, pas une image scannée)
- `portfolio.html` — export HTML de ton portfolio

### 4. Ton profil GitHub

Dans `main.py`, remplace le nom d'utilisateur en dur par le tien :

```python
github_texte = lire_profil_github("ton-username-github")
```

> 💡 Une prochaine amélioration prévue est de sortir cette valeur (ainsi que les chemins CV/portfolio) dans un fichier de configuration séparé, pour éviter d'avoir à toucher au code source. Voir [Limites connues](#limites-connues).

### 5. Cibler tes propres mots-clés et villes

Dans `src/scraper.py`, ajuste :
- `SEARCH_TERMS` — les intitulés de poste recherchés (stage **et** alternance)
- `CITIES` — les villes ciblées

Dans `main.py`, ajuste si besoin :
- `MOTS_CLES_DOMAINE` — les domaines techniques ciblés
- `MOTS_CLES_CONTRAT` — les types de contrat acceptés (stage, alternance...)
- `SEUIL_SCORE_MIN` — le score minimum (0-100) pour qu'une offre soit retenue

---

## Utilisation en local

Lancer une collecte + analyse complète :

```bash
python main.py
```

Lancer le tableau de bord :

```bash
streamlit run app.py
```

---

## Automatisation avec GitHub Actions

Le fichier `.github/workflows/agent_cron.yml` exécute `main.py` automatiquement plusieurs fois par jour et commit les résultats dans `data/`.

Pour l'activer sur ton propre fork/repo :

1. Va dans **Settings → Secrets and variables → Actions** de ton repo.
2. Ajoute les secrets :
   - `GROQ_API_KEY`
   - `GITHUB_TOKEN` n'a **rien à ajouter manuellement** — GitHub Actions en fournit un automatiquement (`secrets.GITHUB_TOKEN`), déjà référencé dans le workflow.
3. Vérifie que les permissions d'écriture sont actives : **Settings → Actions → General → Workflow permissions → Read and write permissions**.
4. Le cron tourne selon le planning défini dans `agent_cron.yml` (modifiable si tu veux une fréquence différente).

Pour héberger le tableau de bord gratuitement, connecte le repo à [Streamlit Community Cloud](https://streamlit.io/cloud) et pointe-le vers `app.py`.

---

## Tableau de bord Streamlit

- **Offres Qualifiées** — liste des offres retenues, avec la lettre générée prête à copier, filtrable par mot-clé et par source.
- **Provenance & Stats** — répartition des offres par plateforme.
- **Gestion & Purge** — purge manuelle des offres anciennes, ou réinitialisation complète de la base.

Par défaut, les offres sont conservées 2 jours (`JOURS_RETENTION_MAX` dans `src/historique.py`) — ajuste cette valeur si tu veux garder un historique plus long.

---

## Personnaliser le projet

Quelques pistes pour adapter l'agent à ton propre profil ou domaine :

- **Changer le domaine ciblé** (ex: cybersécurité, DevOps) : modifie `MOTS_CLES_DOMAINE` dans `main.py` et les `SEARCH_TERMS` dans `src/scraper.py`.
- **Ajouter une entreprise cible** : dans `src/company_scraper.py`, ajoute une fonction `_config_nom_entreprise()` suivant le même modèle que les entrées existantes, et référence-la dans `CONFIGS_REST_SIMPLE`.
- **Changer le fournisseur LLM** : `src/agent.py` est isolé du reste du pipeline — remplacer Groq par un autre fournisseur ne nécessite de toucher que ce fichier.
- **Ajuster le ton de la lettre** : le prompt système dans `analyser_et_rediger()` (`src/agent.py`) contrôle entièrement le style et la structure de la lettre générée.

---

## Limites connues

- Certaines sources (Welcome to the Jungle, Eiffage, Airbus, Société Générale, BNP Paribas, Thales) utilisent des points d'accès internes non documentés officiellement. Ils peuvent changer sans préavis et casser la collecte pour cette source — un contributeur qui constate 0 résultat sur une source doit d'abord vérifier si son endpoint a changé.
- LinkedIn et Indeed limitent activement le scraping automatisé ; des recherches trop fréquentes ou trop rapprochées peuvent être temporairement bloquées.
- Le nom d'utilisateur GitHub et les chemins CV/portfolio sont actuellement en dur dans `main.py` — les sortir dans un fichier de configuration (`config.yaml` ou variables d'environnement) est une amélioration prévue pour simplifier l'usage par d'autres personnes.
- L'extraction de texte PDF ne fonctionne que sur des CV en PDF texte (pas une image scannée).

---

## Contribuer

Les contributions sont bienvenues, en particulier :
- Ajout de nouvelles sources d'offres (autres grands groupes, autres jobboards)
- Passage des chemins/identifiants en dur vers un fichier de configuration
- Tests automatisés sur le filtrage et le parsing
- Traduction/internationalisation pour un usage hors de France

Pour contribuer : fork le repo, crée une branche, ouvre une pull request avec une description claire du changement.


