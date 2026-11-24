# Protocole Scientifique Préenregistré — Corpus Musical Francophone V2 (1985–2024) — Version 1.4 (Consolidée pré-OSF)

- **Statut** : Préenregistrement **v1.4 consolidé** — prêt pour dépôt figé sur **OSF Registries** et autorisation du tirage confirmatoire (`SEED_V2 = 20261124`) — **aucun tirage aléatoire effectué**
- **Historique intégral conservé** : `protocole_preenregistre_v2.md` (v1.0), `protocole_preenregistre_v2_1.md` (v1.1), `protocole_preenregistre_v2_2.md` (v1.2), `protocole_preenregistre_v2_3.md` (v1.3)
- **Stabilité des paramètres confirmatoires** : **aucune modification** du SESOI ($\pm 3{,}0$ points sur 39 ans), de l'effectif confirmatoire ($N = 2\,000$ hors pilote), du critère principal unique (`MATTR_100_Surface`) ni des hypothèses préspécifiées.
- **Branche Git** : `feature/corpus-scientifique-v2`
- **Date de consolidation** : 24 novembre 2026

### Journal des corrections ciblées (v1.3 → v1.4 consolidée)
1. **Résolution exhaustive des 131 chansons pilotes (`pilot_crosswalk_131.csv`)** : zéro chemin Windows ; table de correspondance explicite couvrant **100 % des 131 titres pilotes** (`100` `MATCH_CONFIRMED_EXACT` + `12` `MATCH_CONFIRMED_ALIAS` collaborations/titres étendus/variantes + `19` `ABSENT_CONFIRMED`), garantissant l'exclusion des **112 œuvres pilotes** présentes dans la base (`In_Pilot = Oui`).
2. **Suppression des 36 doublons fantômes du 1er janvier et de la fuite 1984** : vérification systématique de `<link rel="canonical">` sur `lescharts.com` (où `/singles/YYYY-01-01` pointait vers la dernière semaine de décembre `YYYY-1`). L'inventaire canonique compte exactement **2 085 semaines officielles** (100 % HTTP 200), **20 806 œuvres uniques** (**10 296** dans le cadre Top 50 constant ; 3 titres classés uniquement le `1984-12-29` retirés), et **6 semaines sur 2 085** avec au moins un rang Top 50 manquant en amont (`2015-12-05` : 3 rangs Top 50 manquants ; `2016-02-27` : 1 rang Top 50 manquant — 0 erreur de parser).
3. **Datation exacte du cadre Top 50 (`First_Top50_Week` / `Top50_Block_5Y`)** : **65 œuvres Top 50** reclassées dans leur véritable bloc quinquennal d'entrée au Top 50.
4. **Calibration sous l'hypothèse nulle ($\Delta_{39} = 0$, erreur de type I) et puissance appariée REML vs WLS-CR1** (`scripts/simulate_power_v2_4.py`, 2 000 réplications sur le cadre Top 50 décontaminé) :
   - **Sous $H_0$ ($\Delta_{39} = 0$)** : taux de faux positifs **REML = 5,45 %** (IC Wilson 95 % : **[4,54 % ; 6,53 %]**, conforme au nominal 5 %) vs **WLS-CR1 = 6,25 %** (IC 95 % : [5,27 % ; 7,40 %], léger sur-rejet connu du sandwich CR1 qui conforte l'usage du bootstrap stratifié par grappe en secondaire et de REML en principal).
   - **Sous $H_1$ ($\Delta_{39} = \pm 3{,}0$ pts)** : puissance **REML = 86,1 %** (IC Wilson 95 % : **[84,5 % ; 87,6 %]**) contre **69,65 %** pour WLS-CR1.

---

## 1. Effectifs consolidés du cadre harmonisé Top 50 (`Top50_Block_5Y`, v1.4 consolidée)

| Bloc quinquennal (`Top50_Block_5Y`) | Œuvres Top 50 uniques (toutes langues, canonique 1985–2024) |
| :--- | :---: |
| **1985–1989** | 938 |
| **1990–1994** | 1 045 |
| **1995–1999** | 1 121 |
| **2000–2004** | 1 241 |
| **2005–2009** | 1 160 |
| **2010–2014** | 1 105 |
| **2015–2019** | 1 697 |
| **2020–2024** | 1 989 |
| **Total Top 50 constant** | **10 296** *(112 pilotes exclus ; 20 806 œuvres totales ; 9 133 artistes)* |

### Empreintes SHA-256 figées (`data/sampling_frame_v2/`)
- `pilot_crosswalk_131.csv` : `e2d174833d5a9a350aa95325de82b617cd23ad11aefc041705ceefd540c65190`
- `weeks_inventory_1985_2024.csv` : `c8a34373915eac2a429c810f868c57591d1dfb09f2fce51dc872a58b4e505bed`
- `sampling_frame_works_1985_2024.csv` : `668a448dac68299cc5431868d21f983f3dfb5904de8d857b1de070a5efc2f115`
- `pilot_matching_audit.csv` : `db8969363c2a2b587cf301f042b798f21314916e253856243c62db3f3f2aa1b1`

---

## 2. Calibration $H_0$ et puissance appariée REML vs WLS-CR1 (`scripts/simulate_power_v2_4.py`)

Tirages sans remise de 250 titres par bloc (`Top50_Block_5Y`, $N = 2\,000$ hors 112 pilotes) utilisant `First_Top50_Year` et `Artist_Slug` réels ($\bar{m} = 1{,}440$, $1\,389$ artistes/échantillon, $\alpha = 0{,}05$ bilatéral, réestimation REML à chaque réplication) :

| Scénario ($N = 2\,000$) | $\Delta_{39}$ | $\text{ICC}_{\text{vrai}}$ | Réps | **REML (Principal)** | **IC Wilson 95 % REML** | WLS-CR1 (Secondaire) | IC Wilson 95 % WLS-CR1 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Calibration $H_0$ (erreur type I)** | **0,0** | **0,3703** | **2 000** | **5,45 %** | **[4,54 % ; 6,53 %]** | 6,25 % | [5,27 % ; 7,40 %] |
| **Puissance principale ($H_1$)** | **3,0** | **0,3703** | **2 000** | **86,1 %** | **[84,5 % ; 87,6 %]** | 69,65 % | [67,6 % ; 71,6 %] |
| Sensibilité ICC bas | 3,0 | 0,3000 | 1 000 | **88,9 %** | [86,8 % ; 90,7 %] | 73,9 % | [71,1 % ; 76,5 %] |
| Sensibilité ICC haut | 3,0 | 0,4500 | 1 000 | **87,0 %** | [84,8 % ; 88,9 %] | 67,3 % | [64,3 % ; 70,1 %] |

---

## 3. Dispositif confirmatoire, portée de l'estimand et règle d'insuffisance d'effectif

- **Critère confirmatoire unique ($\alpha = 0{,}05$ bilatéral, hors 112 pilotes dont 96 en Top 50)** : pente temporelle $\beta_1$ de `MATTR_100_Surface` dans le modèle mixte REML $Y_i = \beta_0 + \beta_1 T_i + u_{a(i)} + \varepsilon_i$ ($T_i = \text{First\_Top50\_Year}_i - 2004{,}5$) sur l'échantillon stratifié ($N = 2\,000$, 250/bloc) du cadre harmonisé Top 50 constant (`1985–2024`), + test d'équivalence **TOST** contre $[-3{,}0 ; +3{,}0]$ points.
- **Portée explicite de l'estimand principal** : le modèle REML non pondéré sur 250 chansons par bloc quinquennal estime une **tendance temporelle dans un échantillon équilibré entre périodes** (cadre harmonisé Top 50 constant, 1985–2024). Il **ne doit pas** être présenté comme estimant automatiquement la tendance pondérée par les effectifs inégaux de l'ensemble des œuvres classées — cette estimation populationnelle pondérée relève de l'analyse secondaire **WLS-CR1**, dont la calibration sera vérifiée par rééchantillonnage stratifié par grappe avant toute conclusion inférentielle (taux de faux positifs CR1 observé à 6,25 %, IC 95 % : [5,27 % ; 7,40 %]).
- **Règle d'insuffisance d'effectif (épuisement d'une strate)** : la première strate (`1985–1989`) compte **928 œuvres candidates toutes langues** après exclusion des 10 titres pilotes Top 50 (rendement minimal requis $\ge 26{,}9\%$ pour atteindre 250 chansons exploitables). Si une strate s'épuise avant d'atteindre 250 chansons exploitables, **l'effectif réellement obtenu sera déclaré intégralement, sans aucun remplacement opportuniste par une autre période ni modification du SESOI** ; la puissance effective sera alors réévaluée sur les effectifs obtenus et les limites confirmatoires seront explicitement rapportées.
- **Famille secondaire (Holm-Bonferroni)** : WLS pondéré CR1 (Top 50 constant et Top 50→200) + bootstrap stratifié par grappe, modèle ajusté $T \times G$ (support observé 1991–2024 pour le rap), `MATTR_100_Lemmes`, `MATTR_100_NoRepeat`, `MTLD_Surface`, `Sophistication_Lexicale` (`Lexique383`), `Taux_Repetition_Pct`, `Ratio_Compression_Zlib`.
- **Journal d'exclusion exhaustif (zéro suppression silencieuse)** : chaque titre évalué reçoit l'une des 4 catégories mutuellement exclusives : (1) titre du pilote (`In_Pilot = Oui`), (2) non francophone confirmé hors LRCLIB, (3) francophone confirmé mais paroles introuvables sur LRCLIB, (4) transcription inexploitable / $< 100$ mots — avec sensibilité MNAR, triage linguistique calibré sur 100 titres annotés, double implémentation indépendante et audit manuel de 30 transcriptions.
- **Étape de gel et de tirage** : dépôt figé de cette **v1.4** sur **OSF Registries**, puis exécution du tirage reproductible (`scripts/draw_stratified_sample_v2.py --osf-registration-id <ID_OSF>`) avec la graine **`SEED_V2 = 20261124`**.
