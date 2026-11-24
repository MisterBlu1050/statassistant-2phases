# Protocole Scientifique Préenregistré — Corpus Musical Francophone V2 (1985–2024) — Version 1.4

- **Statut** : Préenregistrement **v1.4** — version strictement corrective prête pour décision de dépôt sur **OSF Registries** et autorisation du tirage (`SEED_V2 = 20261124`) — **aucun tirage aléatoire effectué**
- **Historique intégral conservé** : `protocole_preenregistre_v2.md` (v1.0), `protocole_preenregistre_v2_1.md` (v1.1), `protocole_preenregistre_v2_2.md` (v1.2), `protocole_preenregistre_v2_3.md` (v1.3)
- **Stabilité des paramètres confirmatoires** : **aucune modification** du SESOI ($\pm 3{,}0$ points sur 39 ans), de l'effectif confirmatoire ($N = 2\,000$ hors pilote), du critère principal unique (`MATTR_100_Surface`) ni des hypothèses préspécifiées.
- **Branche Git** : `feature/corpus-scientifique-v2`
- **Date de révision** : 24 novembre 2026

### Journal des 4 corrections strictes (v1.3 → v1.4)
1. **Audit des pages atypiques amont** (`2015-12-05` et `2016-02-27`) : vérification HTML directe confirmant **0 erreur de parser** (`missed by ROW_RE = 0`) ; les pages amont de `lescharts.com` omettent elles-mêmes 65 rangs le `2015-12-05` (dont 3 dans le Top 50 : #21, #43, #46) et 32 rangs le `2016-02-27` (dont 1 dans le Top 50 : #50). Au total, seules **6 semaines sur 2 121** présentent au moins un rang manquant dans le Top 50 ; toutes sont tracées dans `weeks_inventory_1985_2024.csv` (`Missing_Top50_Ranks`, `Missing_Total_Ranks`).
2. **Datation exacte du cadre Top 50 harmonisé (`First_Top50_Week` / `Top50_Block_5Y`)** : `compile_sampling_frame_1985_2024.py` calcule désormais la première semaine d'entrée **dans le Top 50** (rangs $\le 50$) indépendamment d'une éventuelle entrée préalable en positions #51–#200. **65 œuvres Top 50** ont ainsi été reclassées dans leur véritable bloc quinquennal.
3. **Exclusion du pilote 100 % reproductible (zéro chemin local Windows)** : le manifeste des 131 chansons pilotes est versionné dans le dépôt (`data/sampling_frame_v2/pilot_manifest_131.csv`, `SHA-256 : 240af2081ae2911488e4979449889768e0422645f72940f7fe57d65032847044`), avec vérification obligatoire des 131 lignes et journal d'appariement complet dans `data/sampling_frame_v2/pilot_matching_audit.csv` (**100 / 131** titres pilotes appariés et exclus du tirage confirmatoire).
4. **Comparaison appariée REML vs WLS-CR1 directement sur le cadre Top 50 corrigé** (`scripts/simulate_power_v2_4.py`) : sur les **mêmes 2 000 échantillons simulés** tirés dans le vrai fichier compilé (`First_Top50_Year`, `Top50_Block_5Y`, `Artist_Slug` réels, hors pilote), la puissance REML atteint **88,4 %** (IC Wilson 95 % : **[86,9 % ; 89,7 %]**) contre **71,25 %** pour WLS-CR1.

---

## 1. Effectifs consolidés du cadre harmonisé Top 50 (`Top50_Block_5Y`, v1.4)

| Bloc quinquennal (`Top50_Block_5Y`) | Œuvres Top 50 uniques (toutes langues, v1.4) | Écart vs v1.3 (`First_Year`) |
| :--- | :---: | :---: |
| **1985–1989** | 941 | 0 |
| **1990–1994** | 1 045 | 0 |
| **1995–1999** | 1 121 | −6 |
| **2000–2004** | 1 241 | +2 |
| **2005–2009** | 1 160 | +1 |
| **2010–2014** | 1 105 | −34 |
| **2015–2019** | 1 697 | +14 |
| **2020–2024** | 1 989 | +23 |
| **Total Top 50 constant** | **10 299** | **65 œuvres reclassées** |

### Empreintes SHA-256 figées (v1.4 — `data/sampling_frame_v2/`)
- `pilot_manifest_131.csv` : `240af2081ae2911488e4979449889768e0422645f72940f7fe57d65032847044`
- `weeks_inventory_1985_2024.csv` : `1ead136b19fd4f695f401226acfea6d4db9bf0e92f8238309dfec57ad8ab7ef8`
- `sampling_frame_works_1985_2024.csv` : `8210ccd1d2534410781fdf055b3f9464939635ec94f1abd8ad9cc48c36f3e277`
- `pilot_matching_audit.csv` : `2ec87229b242c0845f2dcb3d61abdf628b64f5139aec095683219c167a206242`

---

## 2. Puissance appariée REML vs WLS-CR1 sur le cadre réel corrigé (`scripts/simulate_power_v2_4.py`)

Tirages sans remise de 250 titres par bloc (`Top50_Block_5Y`, $N = 2\,000$ hors pilote) utilisant les **années réelles (`First_Top50_Year`)** et les **grappes d'artistes réelles (`Artist_Slug`, $\bar{m} \approx 1{,}44$ titres/artiste, $1\,389$ artistes distincts en moyenne)**, pour $\text{SESOI} = \pm 3{,}0$ points sur 39 ans ($\alpha = 0{,}05$ bilatéral, réestimation REML des variances à chaque réplication) :

| Scénario ($\Delta_{39} = \pm 3{,}0$ pts, $N = 2\,000$) | Réps | $\bar{m}$ réel | $\text{DEFF}_{\text{Kish}}$ | **Puissance REML (Principal)** | **IC Wilson 95 % REML** | Puissance WLS-CR1 (Secondaire) | IC Wilson 95 % WLS-CR1 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Principal ($\text{ICC}_{\text{REML}} = 0{,}3703$)** | **2 000** | **1,440** | **1,069** | **88,4 %** | **[86,9 % ; 89,7 %]** | 71,25 % | [69,2 % ; 73,2 %] |
| Sensibilité ICC bas ($0{,}30$) | 1 000 | 1,439 | 1,069 | **89,0 %** | [86,9 % ; 90,8 %] | 73,8 % | [71,0 % ; 76,4 %] |
| Sensibilité ICC haut ($0{,}45$) | 1 000 | 1,438 | 1,069 | **88,8 %** | [86,7 % ; 90,6 %] | 70,6 % | [67,7 % ; 73,3 %] |

---

## 3. Rappel du dispositif confirmatoire inchangé (v1.3 → v1.4)

- **Critère confirmatoire unique ($\alpha = 0{,}05$ bilatéral, hors pilote `In_Pilot = Non`)** : pente temporelle $\beta_1$ de `MATTR_100_Surface` dans le modèle linéaire mixte REML $Y_i = \beta_0 + \beta_1 T_i + u_{a(i)} + \varepsilon_i$ ($T_i = \text{First\_Top50\_Year}_i - 2004{,}5$) sur l'échantillon stratifié ($N = 2\,000$, 250/bloc) du cadre harmonisé Top 50 constant (`1985–2024`), accompagné du test d'équivalence **TOST** contre $[-3{,}0 ; +3{,}0]$ points.
- **Famille secondaire (Holm-Bonferroni)** : WLS pondéré CR1 (Top 50 constant et Top 50→200), modèle ajusté $T \times G$ (support observé 1991–2024 pour le rap), `MATTR_100_Lemmes`, `MATTR_100_NoRepeat`, `MTLD_Surface`, `Sophistication_Lexicale` (`Lexique383`), `Taux_Repetition_Pct`, `Ratio_Compression_Zlib`.
- **Non-réponse en 3 catégories distinctes** (A. non francophone confirmé hors LRCLIB / B. francophone absent de LRCLIB / C. transcription inexploitable) + sensibilité MNAR (*tipping-point*), triage linguistique calibré sur 100 titres annotés, double implémentation indépendante de `MATTR`/`MTLD` et audit manuel de 30 transcriptions.
- **Prochaine étape conditionnée à l'approbation** : dépôt figé de cette **v1.4** sur **OSF Registries**, puis déclenchement du tirage reproductible avec la graine **`SEED_V2 = 20261124`**.
