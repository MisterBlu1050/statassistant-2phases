# Protocole Scientifique Préenregistré — Corpus Musical Francophone V2 (1985–2024) — Version 1.1

- **Statut** : Préenregistrement **v1.1** (corrige la v1.0 archivée dans `docs/protocole_preenregistre_v2.md` avant toute collecte V2)
- **Branche Git** : `feature/corpus-scientifique-v2`
- **Date de révision** : 24 novembre 2026
- **Graine aléatoire préspécifiée** : `SEED_V2 = 20261124`
- **Périmètre temporel** : **40 années civiles complètes (1985–2024)**, soit un écart de **39 ans** entre bornes ($2024 - 1985 = 39$).
- **Trace d'antériorité** : ce protocole a été élaboré à la suite de l'étude pilote exploratoire de 131 chansons (`corpus_musical_reel.csv` v3). Les règles d'indépendance confirmatoire vis-à-vis du pilote sont définies en section 2.4.
- **Dépôt recommandé avant collecte** : figer cette version 1.1 sur **OSF Registries** (horodatage immuable) avant le premier tirage.

### Journal des révisions (v1.0 → v1.1)
1. **Correction bloquante du calcul de puissance** : recalcul exact sur un écart de **39 ans** ($3.0 / 39 \approx 0.0769$ pt/an, $r \approx 0.077$) via simulation Monte Carlo du modèle mixte (`scripts/simulate_power_v2.py`), portant l'effectif confirmatoire cible à **$N = 2\,000$ chansons** (puissance simulée $\approx 85.5\%$ pour le SESOI de $3.0$ points).
2. **Définition précise de la base de sondage** : choix explicite de la population exhaustive des **titres classés au moins une semaine** dans le Top 50 / Top Singles hebdomadaire français (1985–2024), avec documentation des ruptures de profondeur (Top 50 → Top 100 → Top 200) et analyse de sensibilité à profondeur constante Top 50.
3. **Clarification de l'estimand principal et de la multiplicité** : **1 seul critère principal confirmatoire** (`MATTR_100_Surface`, tendance marginale sur la population cible), critères secondaires (`MATTR_100_Lemmes`, `MATTR_100_NoRepeat`, `MTLD_Surface`, `Sophistication_Lexicale`, `Taux_Repetition_Pct`, `Ratio_Compression_Zlib`) contrôlés par **Holm-Bonferroni**.
4. **Validation linguistique sans biais d'argot** : remplacement du filtre dictionnairique de 85 % par un classifieur de langue sur texte complet + revue humaine de la zone grise, afin de ne jamais exclure l'argot, le verlan ou les néologismes.
5. **Indépendance confirmatoire vis-à-vis du pilote** : exclusion des 131 chansons pilotes de l'analyse confirmatoire principale (avec analyse de sensibilité sur le tirage complet).
6. **Traçabilité de l'ICC et des outils** : documentation de l'estimateur d'ICC (`ICC_ANOVA = 0.344` vs `ICC_REML ≈ 0.370`) et gel des versions des ressources linguistiques (`environment_lock.json`).

---

## 1. Question de recherche et périmètre conceptuel

### 1.1 Question principale confirmatoire
> **« Entre 1985 et 2024, observe-t-on une diminution statistiquement étayée de la diversité lexicale (`MATTR_100_Surface`) dans les paroles des chansons populaires francophones ayant figuré au moins une semaine dans les classements hebdomadaires officiels en France, en tenant compte de la dépendance entre chansons d'un même artiste ? »**

### 1.2 Questions secondaires préspécifiées (contrôlées par Holm-Bonferroni)
1. **Composition vs trajectoires intra-genre** : la tendance persiste-t-elle à composition de genre constante, et diffère-t-elle selon le genre musical (interaction $T_i \times G_i$) sur leur support temporel observé (notamment 1991–2024 pour la comparaison incluant le rap) ?
2. **Formes de surface vs lemmes** : les conclusions convergent-elles sur `MATTR_100_Lemmes` ?
3. **Structure des refrains** : les conclusions persistent-elles après suppression des vers dupliqués (`MATTR_100_NoRepeat`) ?
4. **Indicateurs complémentaires** : évolution de `MTLD_Surface`, `Sophistication_Lexicale`, `Taux_Repetition_Pct` et `Ratio_Compression_Zlib`.

### 1.3 Borne conceptuelle (validité de construit)
L'étude quantifie la **diversité lexicale**, la **répétitivité structurelle** et (à titre secondaire) la **sophistication fréquentielle**. Elle **ne mesure pas** la valeur littéraire, la complexité syntaxique ni les figures de style. L'argot, le verlan, les néologismes et les emprunts intégrés ne sont **jamais** assimilés à un appauvrissement.

---

## 2. Population cible, base de sondage et échantillonnage

> **Principe fondamental** : un échantillon équilibré entre périodes **n'est pas** automatiquement représentatif. La représentativité découle de la population cible, de la base de sondage et de la procédure de tirage et de pondération.

### 2.1 Population cible et base de sondage (hebdomadaire, 1985–2024)
- **Population cible** : l'ensemble des œuvres musicales uniques (version studio originale), majoritairement en langue française, ayant figuré **au moins une semaine** dans le classement officiel hebdomadaire des singles en France (SNEP / Top 50 / Top Singles) entre le **1er janvier 1985** et le **31 décembre 2024**.
- **Ruptures méthodologiques documentées** :
  - **Profondeur du classement** : Top 50 (1985–1997), Top 100 (1998–2011), Top 200 (2012–2024). Pour neutraliser ce changement d'ouverture, une **analyse de sensibilité à profondeur harmonisée Top 50** sur l'ensemble des 40 années (1985–2024) est préspécifiée.
  - **Modes de consommation SNEP** : ventes physiques (1985–2004), intégration des téléchargements (2005–2013), intégration du streaming (à partir de 2014–2016) et révision SNEP des écoutes financées par la publicité (juillet 2024).
- **Distinction base vs paroles manquantes** : les titres absents de la base de sondage et les titres tirés dont les paroles sont indisponibles sur LRCLIB sont comptabilisés séparément dans `sampling_frame_manifest.csv` et `missing_lyrics_log.csv`. Le taux de non-réponse LRCLIB par période et par genre sera analysé pour quantifier tout biais de disponibilité.

### 2.2 Tirage stratifié et pondération
- **Stratification** : 8 strates temporelles de 5 ans (1985–1989, ..., 2020–2024), avec tirage aléatoire sans remise (graine `SEED_V2 = 20261124`) de **$n_h = 250$ titres analysables par bloc de 5 ans** ($N = 2\,000$ titres au total), accompagné d'une **liste de réserve ordonnée** tirée avec la même graine pour remplacer uniquement les titres inéligibles (ex. non francophones ou paroles introuvables), chaque remplacement étant journalisé.
- **Poids de sondage** : $w_h = N_h / n_h$ calculés à partir des effectifs réels $N_h$ de la base de sondage dans chaque strate.
- **Absence d'extrapolation artificielle** : le rap francophone étant absent ou marginal en 1985–1989, aucune cellule vide n'est comblée artificiellement ; toute comparaison incluant le rap est restreinte à son support observé (**1991–2024**).

### 2.3 Dimensionnement et simulation de puissance (`scripts/simulate_power_v2.py`)
- **Paramètres pilotes vérifiés** ($N = 130$ sur `MATTR_100`) : $M = 60.132$, $SD = 11.510$.
  - Estimateur ANOVA à effets aléatoires : $\text{ICC}_{\text{ANOVA}} = 0.344$ ($k = 87$ artistes, $\bar{m} = 1.49$).
  - Estimateur REML de contrôle : $\text{ICC}_{\text{REML}} \approx 0.370$.
- **SESOI préspécifié** : **$\pm 3.0$ points de `MATTR_100` sur 39 ans** ($\beta_{\text{SESOI}} = 3 / 39 \approx 0.0769$ pt/an ; $r \approx 0.077$).
- **Puissance simulée** (400 réplications Monte Carlo du modèle à intercept aléatoire artiste, $\bar{m} = 1.8$, $\alpha = 0.05$ bilatéral, `scripts/simulate_power_v2.py`) :
  - $N = 800$ : $44.2\%$
  - $N = 1\,200$ : $60.0\%$
  - $N = 1\,600$ : $73.0\%$
  - **$N = 2\,000$ : $85.5\%$** *(cible retenue ; puissance légèrement moindre si $\text{ICC}_{\text{REML}} = 0.370$, vérifiée en simulation de sensibilité lors du Livrable 2)*.

### 2.4 Indépendance confirmatoire vis-à-vis du pilote ($N = 131$)
Les 131 chansons du corpus pilote ayant déjà été explorées pour élaborer ce protocole, tout titre du tirage V2 présent dans le pilote est explicitement marqué `In_Pilot = True`.
- **Analyse confirmatoire principale** : exécutée sur le sous-échantillon strictement indépendant (`In_Pilot = False`).
- **Analyse de sensibilité** : ré-estimation sur l'intégralité du tirage aléatoire (`In_Pilot` inclus) pour vérifier la stabilité des estimations.

---

## 3. Critères d'inclusion, validation linguistique et datation

### 3.1 Validation linguistique sans biais lexical
Afin de ne **jamais** exclure des chansons riches en argot, verlan, néologismes ou régionalismes :
1. **Détection de langue indépendante d'un dictionnaire fermé** : classification de langue sur le texte complet (modèle neuronal/n-grammes versionné, ex. `fasttext` / `lingua-py`), séparée du calcul des indicateurs lexicaux.
2. **Zone grise et contrôle humain** :
   - Score français $\ge 0.90$ : inclus automatiquement.
   - Score français $< 0.60$ : exclu automatiquement (journalisé).
   - Zone grise $[0.60, 0.90)$ (chansons bilingues, refrains anglais, argot dense) : **arbitrage humain documenté** selon la règle « majoritairement en français (coupletts/narration principale en français) ».
3. **Sensibilité linguistique** : comparaison entre corpus « français strict ($\ge 0.90$) » et corpus « français majoritaire (zone grise validée incluse) ».

### 3.2 Règle de datation et exclusions
- **Variable temporelle principale (`Annee_Classement`)** : année civile de première entrée dans le classement hebdomadaire français (1985–2024).
- **Variable temporelle secondaire (`Annee_Publication`)** : année de première publication commerciale enregistrée (tous territoires francophones), utilisée en sensibilité.
- **Exclusions journalisées (`exclusion_log.csv`)** : instrumentaux ou $< 50$ tokens ; doublons de version (live, remix, acoustique, réédition) ; transcriptions contenant des balises abrégées non développées (`[Refrain x3]`) ; textes $< 100$ tokens exclus de `MATTR_100` (NA structurel conservé pour `MATTR_50`).

---

## 4. Opérationnalisation des variables et ressources figées

- **Environnement figé (`environment_lock.json`)** : versions exactes de Python, NumPy, SciPy, `statsmodels` (ou `lme4`), `spaCy` + `fr_core_news_sm`, `Lexique383` et du détecteur de langue consignées avant calcul.
- **Tokenisation** : NFC + apostrophes canonicalisées (`’`, `‘`, `ʼ`, `` ` `` → `'`) + regex `[A-Za-zÀ-ÖØ-öø-ÿŒœŸ]+(?:'[A-Za-zÀ-ÖØ-öø-ÿŒœŸ]+)?` en minuscules. Compteur séparé `Nb_Tokens_Numeriques`.
- **Procédure exacte `_NoRepeat`** : après normalisation NFC/apostrophes/minuscules, chaque ligne ($\ge 2$ tokens) n'est conservée qu'à sa **première occurrence** ; si le texte dédupliqué tombe sous 100 tokens, `MATTR_100_NoRepeat` est codé **NA structurel** (jamais basculé en TTR simple) et journalisé.
- **Limite de registre pour `Sophistication_Lexicale` (`Lexique383`)** : les fréquences de Lexique3 proviennent de livres et sous-titres de films ; l'argot musical récent y est sous-représenté. Cet indicateur est donc strictement **secondaire** et interprété avec cette réserve de registre.

---

## 5. Plan d'analyse statistique préspécifié

### 5.1 Estimand principal confirmatoire (1 seul test principal, $\alpha = 0.05$)
- **Variable réponse unique** : `MATTR_100_Surface` (sur l'échantillon confirmatoire `In_Pilot = False`).
- **Modèle principal (tendance marginale populationnelle)** :
  $$Y_i = \beta_0 + \beta_{\text{pop}} T_i + u_{a(i)} + \varepsilon_i$$
  avec $T_i = \text{Annee\_Classement}_i - 2004.5$ et $u_{a(i)} \sim \mathcal{N}(0, \sigma_u^2)$ (intercept aléatoire par artiste principal).
- **Prise en compte des poids de sondage $w_h = N_h / n_h$** : estimation par **bootstrap par grappe d'artiste pondéré** ($B = 2\,000$ tirages) et comparaison avec l'estimateur REML non pondéré afin de garantir une inférence valide sous plan stratifié + clustering artiste.
- **Test d'équivalence (TOST)** : si $p \ge 0.05$, l'absence de baisse substantielle n'est déclarée **que si** l'IC à $90\%$ de $39 \times \beta_{\text{pop}}$ est entièrement inclus dans $[-3.0, +3.0]$ points.

### 5.2 Estimands secondaires (correction Holm-Bonferroni sur la famille)
1. **Modèle ajusté pour le genre (tendance à composition constante + interactions)** :
   $$Y_i = \beta_0 + \beta_1 T_i + \beta_2 G_i + \beta_3 (T_i \times G_i) + u_{a(i)} + \varepsilon_i$$
   estimé d'abord sur le support complet (genres présents dès 1985), puis sur le support commun **1991–2024** incluant le rap, avec estimation séparée de la pente intra-genre pour chaque genre.
2. **Critères secondaires** : `MATTR_100_Lemmes`, `MATTR_100_NoRepeat`, `MTLD_Surface` (avec `MTLD_ZeroFactor_Flag`), `Sophistication_Lexicale`, `Taux_Repetition_Pct`, `Ratio_Compression_Zlib` — famille corrigée par **Holm-Bonferroni**.

### 5.3 Analyses de sensibilité préspécifiées
1. **Profondeur harmonisée Top 50** sur 1985–2024 (neutralisation de l'élargissement Top 50 → Top 100 → Top 200).
2. **Non-linéarité** : spline cubique naturelle ($df = 3, 4$) comparée au modèle linéaire (LRT / AIC).
3. **1 titre max par artiste** (tirage aléatoire, graine `SEED_V2`).
4. **Datation alternative** (`Annee_Publication` vs `Annee_Classement`).
5. **Seuil linguistique strict** (score français $\ge 0.90$ seul) et **inclusion des chevauchements pilotes** (`In_Pilot = True`).

---

## 6. Validation scientifique indépendante et publication immuable

1. **Deuxième implémentation indépendante** (`verify_independent_metrics.py`) recalculant `MATTR`, `MTLD`, répétition et compressibilité `zlib` sans importer le code de construction, validée sur vecteurs synthétiques externes et sur le corpus complet (tolérance $\le 10^{-6}$).
2. **Audit manuel stratifié** de $n = 30$ transcriptions LRCLIB (graine `SEED_V2`) contre éditions officielles / livrets.
3. **Publication immuable** : répertoire versionné (`data/corpus_v2.0/`), manifeste SHA-256 canonique sans horodatage (`manifest_v2.0.json`) distinct du journal d'ingestion horodaté append-only (`ingestion_log.jsonl`), aucune parole protégée redistribuée.
