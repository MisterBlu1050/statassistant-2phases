# Protocole Scientifique Préenregistré — Corpus Musical Francophone V2 (1985–2024) — Version 1.2

- **Statut** : Préenregistrement **v1.2** (prêt pour revue finale et dépôt figé sur **OSF Registries** avant tout tirage aléatoire)
- **Historique conservé intact** : `docs/protocole_preenregistre_v2.md` (v1.0), `docs/protocole_preenregistre_v2_1.md` (v1.1)
- **Branche Git** : `feature/corpus-scientifique-v2`
- **Date de révision** : 24 novembre 2026
- **Graine aléatoire préspécifiée** : `SEED_V2 = 20261124`
- **Périmètre temporel** : **40 années civiles complètes (1985–2024)**, soit un écart de **39 ans** entre bornes ($2024 - 1985 = 39$).

### Journal des révisions (v1.1 → v1.2)
1. **Simulateur de puissance corrigé (`scripts/simulate_power_v2.py` v1.2)** :
   - Allocation temporelle **exactement stratifiée** ($250$ chansons dans chacun des 8 blocs quinquennaux = $12{,}5\%$ par bloc, $2{,}5\%$ par année, zéro empilement sur 2024).
   - **Réestimation REML exacte** des composantes de variance ($\hat{\sigma}_u^2, \hat{\sigma}_e^2$) à **chaque réplication** (et test $t$ à $k - 2$ degrés de liberté), sans jamais supposer les variances connues.
   - **2 000 réplications Monte Carlo** pour le scénario principal avec **IC binomial de Wilson à 95 %** + grille de sensibilité sur $\text{ICC} \in \{0{,}30 ; 0{,}370 ; 0{,}45\}$, taille de grappe $\bar{m} \in \{1{,}8 ; 2{,}5\}$ et effectif $N \in \{1\,600 ; 2\,000 ; 2\,400\}$.
   - Calcul REML exact de l'ICC pilote confirmé : $\text{ICC}_{\text{REML}} = 0{,}3703$ (vs $\text{ICC}_{\text{ANOVA}} = 0{,}3438$).
2. **Effectif confirmatoire défini hors pilote** : **$N = 2\,000$** désigne l'effectif **confirmatoire effectivement analysable hors les 131 chansons du pilote** (`In_Pilot = False`), soit 250 titres confirmatoires hors pilote par bloc quinquennal.
3. **Règles rigoureuses de tirage, non-réponse et pondération** : probabilités d'inclusion initiales $\pi_h = n_h^{\text{tirés}} / N_h$, ajustement explicite des poids pour non-réponse LRCLIB ($w_{h,\text{adj}}$), et **estimateur pondéré cohérent avec l'estimand populationnel** (moindres carrés pondérés / GEE pondéré par grappe d'artiste + bootstrap stratifié par grappe respectant les 8 strates).
4. **Calibration du triage linguistique** : les scores du classifieur de langue ne sont **pas** interprétés comme un « pourcentage de mots français », mais comme des **scores de triage calibrés sur un échantillon annoté humainement** (incluant argot, verlan et titres multilingues).
5. **Comparabilité historique SNEP** : mention explicite des évolutions des modes de consommation agrégés par le SNEP (ventes physiques, téléchargements, streaming, règle streaming financé par la publicité de juillet 2024) dans l'interprétation de la population cible.

---

## 1. Question principale, estimands et multiplicité

### 1.1 Question principale confirmatoire (1 seul test principal, $\alpha = 0{,}05$)
> **« Entre 1985 et 2024, observe-t-on une diminution statistiquement étayée de la diversité lexicale (`MATTR_100_Surface`) dans les paroles des chansons populaires francophones ayant figuré au moins une semaine dans les classements hebdomadaires officiels en France, en tenant compte des poids de sondage et de la dépendance entre chansons d'un même artiste ? »**

### 1.2 Estimands explicitement distingués
- **Estimand principal confirmatoire (unique)** : pente temporelle marginale pondérée $\beta_{\text{pop}}$ de `MATTR_100_Surface` sur la population cible des titres francophones classés (1985–2024), estimée sur l'échantillon confirmatoire **hors pilote** (`In_Pilot = False`, $N = 2\,000$).
- **Estimands secondaires (famille corrigée par Holm-Bonferroni)** :
  1. **Tendance à composition de genre constante et trajectoires intra-genre** : modèle mixte $Y_i = \beta_0 + \beta_1 T_i + \beta_2 G_i + \beta_3 (T_i \times G_i) + u_{a(i)} + \varepsilon_i$ (sans extrapolation du rap avant son support observé 1991–2024).
  2. **Critères lexicaux et structurels secondaires** : `MATTR_100_Lemmes`, `MATTR_100_NoRepeat`, `MTLD_Surface` (avec `MTLD_ZeroFactor_Flag`), `Sophistication_Lexicale` (`Lexique383`, avec réserve de registre), `Taux_Repetition_Pct`, `Ratio_Compression_Zlib`.

---

## 2. Population cible, base de sondage et règles de tirage

### 2.1 Base de sondage documentée (voir `docs/inventaire_base_sondage_1985_2024.md`)
- **Population cible** : œuvres musicales uniques (version studio originale), majoritairement en langue française, classées **au moins une semaine** dans le classement officiel hebdomadaire français (SNEP / Top Singles, archivé semaine par semaine sur `lescharts.com`, **40/40 années vérifiées**).
- **Ruptures de profondeur et de méthodologie SNEP** :
  - Profondeur vérifiée : **Top 50** (1985–1997), **Top 100** (1998–2011), **Top 200** (2012–2024). Une **analyse de sensibilité à profondeur constante Top 50** sur l'ensemble des 40 ans est préspécifiée.
  - Les changements de périmètre de consommation SNEP (ventes physiques → téléchargements → streaming → règle streaming financé par la publicité de juillet 2024) modifient la nature commerciale du classement au fil du temps et constituent une limite structurelle assumée de la comparabilité historique.

### 2.2 Procédure de tirage stratifié, réserve et ajustement des poids
1. **Exclusion préalable des 131 titres pilotes** : avant tirage confirmatoire, les œuvres présentes dans le corpus pilote ($N = 131$) sont étiquetées `In_Pilot = True` dans la base de sondage afin que l'échantillon confirmatoire atteigne **exactement $N = 2\,000$ titres analysables hors pilote** (`250` par bloc quinquennal). Un tirage parallèle inclut le pilote pour l'analyse de sensibilité.
2. **Tirage sans remise avec liste de réserve ordonnée** : dans chaque strate $h \in \{1, \dots, 8\}$ d'effectif éligible $N_h$, on tire aléatoirement (graine `SEED_V2 = 20261124`) une permutation complète des titres éligibles. Les premiers titres sont évalués dans l'ordre exact de la permutation jusqu'à obtenir $n_h = 250$ titres **analysables** (francophones validés, $\ge 100$ tokens, paroles LRCLIB disponibles et non corrompues).
3. **Suivi de la non-réponse et pondération ajustée** :
   - Soit $n_h^{\text{évalués}}$ le nombre de titres de la base parcourus dans la strate $h$, $n_h^{\text{éligibles}}$ ceux qui appartiennent effectivement à la population cible francophone, et $n_h^{\text{observés}} = 250$ ceux disposant de paroles exploitables sur LRCLIB.
   - Taux de réponse LRCLIB estimé par strate : $\hat{r}_h = n_h^{\text{observés}} / n_h^{\text{éligibles}}$.
   - Effectif estimé de la population francophone dans la strate : $\hat{N}_h^{\text{FR}} = N_h^{\text{total}} \times (n_h^{\text{éligibles}} / n_h^{\text{évalués}})$.
   - **Poids final ajusté pour non-réponse** : $w_{h,\text{adj}} = \hat{N}_h^{\text{FR}} / n_h^{\text{observés}}$ (documenté dans `sampling_weights_v2.csv`). Tout écart marqué de $\hat{r}_h$ entre périodes sera rapporté comme risque potentiel de biais de non-réponse.

---

## 3. Puissance simulée par REML stratifié (`scripts/simulate_power_v2.py` v1.2)

Paramètres empiriques du pilote ($N = 130$ sur `MATTR_100`) : $M = 60{,}132$, $SD = 11{,}5103$, $\text{ICC}_{\text{ANOVA}} = 0{,}3438$, **$\text{ICC}_{\text{REML}} = 0{,}3703$**.  
Allocation vérifiée par le simulateur : **12,50 % exactement dans chacun des 8 blocs quinquennaux** et **2,50 % sur l'année 2024 seule**. Réestimation REML des variances à chaque réplication, test $t$ bilatéral ($\alpha = 0{,}05$) sur $\text{SESOI} = \pm 3{,}0$ points sur 39 ans ($\beta = 0{,}0769$ pt/an) :

| Scénario | $N$ (par bloc) | $\text{ICC}_{\text{vrai}}$ | $\bar{m}$ (titres/artiste) | Réplications | Puissance REML | IC Wilson 95 % |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Principal (pilote REML)** | **2 000 (250)** | **0,3703** | **1,8** | **2 000** | **83,9 %** | **[82,2 % ; 85,5 %]** |
| Sensibilité ICC bas | 2 000 (250) | 0,3000 | 1,8 | 1 000 | 86,3 % | [84,0 % ; 88,3 %] |
| Sensibilité ICC haut | 2 000 (250) | 0,4500 | 1,8 | 1 000 | 81,3 % | [78,8 % ; 83,6 %] |
| Sensibilité grappes denses | 2 000 (250) | 0,3703 | 2,5 | 1 000 | 77,8 % | [75,1 % ; 80,3 %] |
| Effectif réduit | 1 600 (200) | 0,3703 | 1,8 | 1 000 | 75,2 % | [72,4 % ; 77,8 %] |
| Effectif étendu | 2 400 (300) | 0,3703 | 1,8 | 1 000 | 90,0 % | [88,0 % ; 91,7 %] |

---

## 4. Triage linguistique calibré (sans biais d'argot)

- Les probabilités renvoyées par le classifieur automatique de langue (`lingua-py` ou `fasttext`, version figée dans `environment_lock.json`) sont des **scores de triage** et **non** des pourcentages de mots français.
- **Calibration préalable** : avant filtrage de la base, le classifieur sera calibré sur un **échantillon annoté humainement de 100 titres** couvrant explicitement du rap argotique/verlan, de la chanson française classique, des titres bilingues et des titres étrangers, afin de fixer empiriquement les deux seuils de triage ($\tau_{\text{haut}}$ pour inclusion directe, $\tau_{\text{bas}}$ pour exclusion directe, et revue humaine systématique entre $\tau_{\text{bas}}$ et $\tau_{\text{haut}}$).
- **Sensibilité linguistique** : comparaison entre corpus incluant les titres bilingues majoritairement francophones validés manuellement et corpus strictement monolingue.

---

## 5. Modélisation statistique cohérente avec l'estimand pondéré

### 5.1 Estimateur principal (populationnel pondéré + grappes d'artistes)
Pour estimer la tendance marginale populationnelle $\beta_{\text{pop}}$ en respectant simultanément les **poids de sondage $w_{h,\text{adj}}$** et le **regroupement par artiste** :
1. **Estimateur principal** : régression pondérée par $w_{h,\text{adj}}$ (`WLS` / `GEE` pondéré échangeable par artiste) avec **variance sandwich robuste aux grappes d'artistes** (CR2/LZ) **et** **bootstrap stratifié par grappe d'artiste** ($B = 2\,000$ tirages respectant la stratification par bloc quinquennal).
2. **Estimateur mixte REML compagnon (non pondéré sur l'échantillon stratifié)** : $Y_i = \beta_0 + \beta_{\text{strat}} T_i + u_{a(i)} + \varepsilon_i$ (REML), rapporté en parallèle afin de distinguer explicitement la tendance pondérée par la taille des strates de la tendance à poids égal par période.
3. **Test d'équivalence (TOST)** : si $p \ge 0{,}05$, l'absence de baisse substantielle n'est retenue **que si** l'IC à $90\%$ de $39 \times \hat{\beta}_{\text{pop}}$ est entièrement inclus dans $[-3{,}0 ; +3{,}0]$ points.

### 5.2 Analyses secondaires et de sensibilité préspécifiées
- Modèle ajusté $Y_i = \beta_0 + \beta_1 T_i + \beta_2 G_i + \beta_3(T_i \times G_i) + u_{a(i)} + \varepsilon_i$ (support commun 1991–2024 pour le rap + pentes intra-genre).
- Profondeur harmonisée **Top 50 constant** sur 1985–2024.
- Splines cubiques naturelles ($df = 3, 4$) pour non-linéarité.
- Sous-échantillon **1 titre max par artiste** (graine `SEED_V2`).
- Datation alternative (`Annee_Publication` vs `Annee_Classement`) et inclusion des chevauchements pilotes (`In_Pilot = True`).

---

## 6. Validation indépendante et publication immuable

1. **Double implémentation indépendante** de `MATTR`, `MTLD`, répétition et compressibilité `zlib` (`verify_independent_metrics.py`, tolérance $\le 10^{-6}$).
2. **Audit manuel stratifié** de $n = 30$ transcriptions LRCLIB contre éditions officielles / livrets.
3. **Publication immuable** : répertoire versionné `data/corpus_v2.0/`, manifeste SHA-256 canonique sans horodatage (`manifest_v2.0.json`) distinct du journal d'ingestion append-only (`ingestion_log.jsonl`), aucune parole protégée redistribuée.
