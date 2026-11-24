# Protocole Scientifique Préenregistré — Corpus Musical Francophone V2 (1985–2024)

- **Statut** : Préenregistrement v1.0 (antérieur à toute collecte de données V2)
- **Branche Git** : `feature/corpus-scientifique-v2`
- **Date de rédaction** : 24 novembre 2026
- **Graine aléatoire préspécifiée** : `SEED_V2 = 20261124`
- **Périmètre** : 40 années civiles complètes (**1985–2024**, bornes incluses)

---

## 1. Question de recherche et périmètre conceptuel

### 1.1 Question principale
> **« Entre 1985 et 2024, observe-t-on une diminution statistiquement étayée de la diversité et de la sophistication lexicales dans les paroles des chansons populaires francophones classées en France, indépendamment de l'évolution de la part des genres musicaux et de l'effet propre aux artistes ? »**

### 1.2 Questions secondaires préspécifiées
1. **Effet intra-genre vs effet de composition** : l'évolution temporelle diffère-t-elle entre les grands genres musicaux (interaction $T_i \times G_i$) ? En particulier, sur la fenêtre où le rap francophone est présent dans les classements (1991–2024), sa trajectoire diffère-t-elle de celle de la variété/pop et du rock/électro ?
2. **Rôle des refrains (structure vs vocabulaire)** : une éventuelle évolution de la diversité lexicale « entendue » (paroles intégrales) persiste-t-elle lorsqu'on supprime les répétitions identiques de vers/sections (*diversité de composition*) ?
3. **Formes de surface vs lemmes** : les résultats convergent-ils entre formes fléchies et lemmes (`spaCy`) ?

### 1.3 Borne conceptuelle (validité de construit)
Cette étude mesure la **diversité lexicale**, la **sophistication fréquentielle du vocabulaire** et la **répétitivité structurelle**. Elle **ne mesure pas** la valeur esthétique, la complexité syntaxique profonde ni la richesse des figures de style (qui exigeraient une annotation humaine). De même, l'argot, le verlan, les néologismes et les emprunts ne sont **pas** codés comme des formes d'appauvrissement.

---

## 2. Population cible, base de sondage et règle de représentativité

> **Principe méthodologique fondamental** : un échantillon **équilibré entre décennies** n'est **pas** automatiquement représentatif. La représentativité dépend exclusivement de l'adéquation entre la **population cible**, la **base de sondage** et la **procédure de tirage (ou de pondération)**.

### 2.1 Définition de la population cible
- **Population cible** : l'ensemble des chansons populaires **majoritairement en langue française** ($\ge 85\%$ de tokens francophones) ayant figuré dans les classements officiels de singles / titres les plus populaires en France entre le **1er janvier 1985** et le **31 décembre 2024** (40 années civiles, le Top 50 français ayant débuté le 4 novembre 1984).
- **Ce que cette population n'est pas** : elle ne représente ni la totalité de la production discographique française non classée (underground, chanson d'auteur hors classements), ni la langue française parlée ou écrite en général.

### 2.2 Base de sondage documentée
- **Unité statistique** : une œuvre musicale unique (couple artiste principal + titre canonique, version studio originale, sans doublon de remix/live/réédition).
- **Construction préalable de la base** : constitution et archivage d'une liste annuelle documentée des titres francophones classés en France (classements SNEP / Top Singles / Top 50 annuel 1985–2024, en documentant explicitement les ruptures méthodologiques des classements : ventes physiques 1985–2004, téléchargements 2005–2013, streaming intégré à partir de 2014–2016).
- **Transparence en cas de couverture partielle** : si la base annuelle complète n'est pas intégralement accessible publiquement pour certaines années, le taux de couverture exact par année et par source sera archivé dans `sampling_frame_manifest.csv` et rapporté comme limite de validité externe.

### 2.3 Plan d'échantillonnage stratifié (graine figée `SEED_V2 = 20261124`)
- **Stratification** : par **période** (8 blocs de 5 ans : 1985–1989, 1990–1994, ..., 2020–2024) et, lorsque les effectifs de la base le permettent, par **genre musical** (règles de classification explicites fondées sur taxonomie externe vérifiable : Discogs / MusicBrainz, et non codage ad hoc).
- **Absence d'invention artificielle** : le rap francophone étant absent ou quasi absent des classements 1985–1989, aucune cellule vide ne sera comblée artificiellement ; l'analyse comparative incluant le rap sera conduite sur la fenêtre commune **1991–2024** en analyse de sensibilité préspécifiée.
- **Pondération** : les analyses descriptives de tendance globale sur la population cible seront estimées à la fois **non pondérées** (sur l'échantillon stratifié) et **pondérées par la part réelle de chaque strate dans la base de sondage** ($w_h = N_h / n_h$), afin de ne pas confondre équilibre de tirage et représentativité démographique des classements.

---

## 3. Calcul de puissance (fondé sur les paramètres empiriques du corpus pilote)

Les paramètres de variance et de corrélation intra-classe par artiste proviennent du corpus pilote vérifié ($N = 131$, v3) :
- `MATTR_100` ($n = 130$) : $M = 60.13$, $SD = 11.51$.
- `MTLD` ($n = 131$) : $M = 45.50$, $SD = 28.28$.
- **Corrélation intra-classe par artiste (`ICC`)** sur `MATTR_100` ($k = 87$ artistes, $\bar{m} = 1.49$ titres/artiste) : **$\text{ICC} = 0.344$** ($\text{DEFF} = 1.17$). Cette ICC élevée confirme empiriquement qu'un modèle ignorant l'effet artiste sous-estime les erreurs standards.

### Dimensionnement cible
- **Plus petit effet scientifiquement pertinent (SESOI)** préspécifié : une variation de **$\pm 3.0$ points de `MATTR_100` sur 40 ans** ($\pm 0.075$ pt/an, soit $\approx 0.26\,SD$ sur 40 ans ; corrélation partielle équivalente $|r| \approx 0.13$).
- Pour détecter $|r| = 0.13$ à $\alpha = 0.05$ (bilatéral) avec une puissance de **$80\%$** ($N_{\text{eff}} \approx 462$) à **$90\%$** ($N_{\text{eff}} \approx 618$), ajusté pour un effet de plan par artiste $\text{DEFF} \approx 1.30$ ($\bar{m} \approx 1.85$ titres/artiste) :
  - **Cible minimale** : **$N = 600$ chansons** (puissance $\ge 80\%$ sur le SESOI).
  - **Cible recommandée** : **$N = 800$ chansons** ($\approx 100$ titres par bloc de 5 ans, puissance $\ge 90\%$ sur le SESOI, et marge pour exclusions post-collecte).

---

## 4. Critères d'inclusion, d'exclusion et règle de datation

### 4.1 Critères d'inclusion
1. Présence attestée dans la base de sondage des classements français (1985–2024).
2. Version studio originale identifiée par identifiant canonique (`LRCLIB_ID` + métadonnées vérifiées sans caractère de contrôle).
3. Langue majoritairement française : $\ge 85\%$ de tokens reconnus comme français (vérification automatique reproductible + revue manuelle des cas limites entre $75\%$ et $90\%$).
4. Longueur minimale : $\ge 100$ tokens alphabétiques pour l'indicateur principal `MATTR_100` (les titres de $50$ à $99$ tokens sont conservés dans un registre séparé pour `MATTR_50` et analyse de sensibilité, jamais mélangés silencieusement dans `MATTR_100`).

### 4.2 Critères d'exclusion (journalisés dans `exclusion_log.csv`)
- Morceaux instrumentaux ou $< 50$ tokens.
- Doublons d'une même œuvre (live, acoustique, remix, radio edit, réédition) : seule la première version studio classée est retenue.
- Transcriptions manifestement corrompues, incomplètes ou contenant des balises de raccourci non développées (`[Refrain x3]`) non vérifiables.
- Chansons dont la proportion de français est $< 85\%$.

### 4.3 Règle unique de datation
- **Variable principale de temps (`Annee_Classement`)** : année de première entrée dans le classement français (1985–2024), alignée sur la population cible des chansons diffusées/classées en France.
- **Variable secondaire (`Annee_Publication`)** : année de première publication commerciale enregistrée (tous territoires francophones confondus), conservée pour analyse de sensibilité.

---

## 5. Opérationnalisation des variables linguistiques

### 5.1 Prétraitement et tokenisation (déterministe, versionné)
- Normalisation Unicode **NFC** + canonicalisation des apostrophes typographiques (`’`, `‘`, `ʼ`, `` ` `` → `'`).
- Expression régulière incluant les ligatures françaises : `[A-Za-zÀ-ÖØ-öø-ÿŒœŸ]+(?:'[A-Za-zÀ-ÖØ-öø-ÿŒœŸ]+)?` en minuscules.
- **Politique des nombres** : exclus de la tokenisation lexicale principale ; un compteur séparé `Nb_Tokens_Numeriques` est conservé pour transparence.

### 5.2 Batterie d'indicateurs (doubles mesures systématiques)

| Rôle | Variable | Définition | Version(s) calculée(s) |
| :--- | :--- | :--- | :--- |
| **Principal** | `MATTR_100_Surface` | Moving-Average TTR sur fenêtre fixe de 100 mots ($\times 100$), NA structurel si $N < 100$ | Intégrale **et** sans vers répétés (`_NoRepeat`) |
| **Principal (co-critère)** | `MATTR_100_Lemmes` | Même calcul sur les lemmes (`spaCy fr_core_news_sm`, version figée) | Intégrale **et** sans vers répétés (`_NoRepeat`) |
| **Secondaire** | `MTLD_Surface` / `MTLD_Lemmes` | MTLD bidirectionnel (seuil 0.72), avec indicateur `MTLD_ZeroFactor_Flag` si aucun facteur complet n'est atteint | Intégrale **et** `_NoRepeat` |
| **Secondaire** | `Sophistication_Lexicale` | Fréquence lexicale inverse moyenne (log-fréquence inversée) des lemmes dans un lexique français de référence (Lexique3) | Sur lemmes hors mots-outils |
| **Secondaire** | `Taux_Repetition_Pct` | $(1 - \text{vers uniques} / \text{vers totaux}) \times 100$ sur lignes $\ge 2$ tokens | Paroles intégrales |
| **Secondaire** | `Ratio_Compression_Zlib` | Taille compressée (`zlib`) / taille brute normalisée (indicateur indépendant de la tokenisation, référence *PLOS ONE*) | Paroles intégrales |
| **Descriptif** | `MATTR_50`, `Longueur_Mots`, `Mots_Uniques`, `Longueur_Moyenne_Mot` | Descriptifs complémentaires (couverture 100 % des titres $\ge 50$ mots pour `MATTR_50`) | Intégrale |

---

## 6. Hypothèses et plan d'analyse statistique préspécifié

### 6.1 Modèle principal (modèle linéaire mixte hiérarchique)
Sur les chansons $i = 1, \dots, N$ regroupées par artiste principal $a(i)$ :

$$Y_i = \beta_0 + \beta_1 T_i + \beta_2 G_i + \beta_3 (T_i \times G_i) + u_{a(i)} + \varepsilon_i$$

avec :
- $Y_i$ : `MATTR_100_Surface` (puis `MATTR_100_Lemmes` en co-critère principal),
- $T_i = \text{Annee}_i - 2005$ : année centrée,
- $G_i$ : genre musical (codage par effets / *sum contrasts* afin que $\beta_1$ représente la pente moyenne ajustée des genres),
- $u_{a(i)} \sim \mathcal{N}(0, \sigma_u^2)$ : intercept aléatoire par artiste (modèle estimé par REML/ML avec `statsmodels.MixedLM` / `lme4`),
- $\varepsilon_i \sim \mathcal{N}(0, \sigma^2)$ : résidu individuel.

### 6.2 Tests d'hypothèses et test d'équivalence (TOST)
- **$H_0$** : $\beta_1 = 0$ (aucune tendance linéaire ajustée de la diversité lexicale entre 1985 et 2024).
- **$H_1$** : $\beta_1 \ne 0$ (seuil $\alpha = 0.05$, bilatéral).
- **Test d'équivalence (TOST)** : si $p \ge 0.05$, **aucune conclusion d'absence de baisse ne sera tirée** sans vérifier si l'intervalle de confiance à $90\%$ de $40 \times \beta_1$ est entièrement contenu dans $[-3.0, +3.0]$ points de `MATTR_100` (SESOI).
- **Comparaisons multiples** : correction de **Holm-Bonferroni** sur la famille des indicateurs secondaires.

### 6.3 Analyses de sensibilité préspécifiées
1. **Sensibilité non linéaire** : remplacement de $\beta_1 T_i$ par une spline cubique naturelle ($df = 3$ ou $4$) comparée par test du rapport de vraisemblance (LRT / AIC).
2. **Sensibilité 1 titre par artiste** : sous-échantillonnage aléatoire (graine `SEED_V2`) limité à 1 titre maximum par artiste principal.
3. **Sensibilité fenêtre Rap (1991–2024)** : restriction aux 34 années où les 3 genres coexistent dans les classements.
4. **Sensibilité refrains** : ré-estimation du modèle principal sur `MATTR_100_NoRepeat`.
5. **Sensibilité pondération** : estimation pondérée par les poids de strate $w_h = N_h / n_h$ de la base de sondage.

---

## 7. Validation scientifique indépendante et gouvernance des artefacts

1. **Deuxième implémentation indépendante** : un script indépendant (`verify_independent_metrics.py`) recalculera `MATTR`, `MTLD`, le taux de répétition et la compressibilité sans importer le code de construction, et vérifiera la concordance exacte (tolérance $\le 10^{-6}$) sur des vecteurs synthétiques de référence et sur les textes collectés.
2. **Audit manuel des transcriptions** : tirage aléatoire stratifié de **$n = 30$ chansons** (graine `SEED_V2`) dont les paroles LRCLIB seront comparées manuellement à une édition officielle/livret (mesure du taux d'erreur de transcription et de l'écart sur `MATTR_100`).
3. **Publication versionnée immuable** : chaque version du corpus est écrite dans un répertoire immuable (`data/corpus_v2.0/`), validée intégralement avant activation, avec :
   - un **manifeste scientifique figé** (`manifest_v2.0.json`, empreintes SHA-256 des contenus canoniques sans horodatage),
   - un **journal d'ingestion séparé** (`ingestion_log.jsonl`, append-only, horodaté UTC),
   - **zéro parole protégée redistribuée** dans le dépôt public (seules les métriques dérivées, empreintes `Lyrics_SHA256` et identifiants `LRCLIB_ID` sont versionnés).
4. **Rôle de StatAssistant** : StatAssistant exécutera les vérifications de garde-fous, les comparaisons descriptives et les contrôles de cohérence, tandis que le modèle mixte hiérarchique ($u_{a(i)}$) et le TOST seront exécutés par un script statistique auditable dédié (StatAssistant ne prenant pas encore en charge nativement les modèles mixtes hiérarchiques).
