# Protocole Scientifique Préenregistré — Corpus Musical Francophone V2 (1985–2024) — Version 1.3

- **Statut** : Préenregistrement **v1.3** (fondé sur la compilation exhaustive de la base de sondage 1985–2024 — **aucun tirage aléatoire effectué**)
- **Historique intégral conservé** : `protocole_preenregistre_v2.md` (v1.0), `protocole_preenregistre_v2_1.md` (v1.1), `protocole_preenregistre_v2_2.md` (v1.2)
- **Branche Git** : `feature/corpus-scientifique-v2`
- **Date de révision** : 24 novembre 2026
- **Graine aléatoire préspécifiée** : `SEED_V2 = 20261124`

### Journal des révisions (v1.2 → v1.3)
1. **Base de sondage exhaustive compilée et auditée** (`data/sampling_frame_v2/`) : **2 121 semaines officielles** (100 % HTTP 200, **3 semaines manquantes** documentées sur 40 ans : 1993-09-11, 2005-03-05, 2012-11-03), **20 809 œuvres canoniques uniques**, **9 135 artistes**, transitions de profondeur datées à la semaine près (`1998-03-07` → Top 100 ; `2012-02-18` → Top 200), et **100 / 131 titres pilotes** appariés dans la base.
2. **Simulation directe de l'estimateur pondéré WLS-CR1 sur la base réelle** (`scripts/simulate_power_v2_3.py`, 2 000 réplications) :
   - Sur le cadre complet `Top 50 → Top 200` avec tirage égal 250/bloc, la variation d'un facteur 5,6× des tailles de strates ($N_1 = 941$ vs $N_8 = 5\,273$) induit un **facteur de Kish $\text{DEFF}_{\text{poids}} = 1{,}414$**, ramenant la puissance réelle de WLS-CR1 à **69,1 %** (IC 95 % : [67,0 % ; 71,1 %]) pour $N = 2\,000$ et $\Delta_{39} = 3{,}0$ pts.
   - Sur le **cadre harmonisé Top 50 constant**, les tailles de strates sont homogènes ($941$ à $1\,966$, $\text{DEFF}_{\text{poids}} = 1{,}065$), la puissance WLS-CR1 atteint **71,0 %** (72,9 % en proportionnel), et la puissance REML atteint **83,9 %** (IC 95 % : [82,2 % ; 85,5 %]).
   - **Alignement estimand ↔ simulateur** : le protocole v1.3 aligne explicitement l'**estimand confirmatoire principal** sur le modèle **REML stratifié sur le cadre harmonisé Top 50 constant** ($N = 2\,000$, 250/bloc, puissance simulée **83,9 %**), et conserve l'**estimateur pondéré WLS-CR1 sur le cadre complet Top 50→200** comme analyse populationnelle secondaire avec sa puissance réelle documentée (**69,1 %** à $N = 2\,000$).
3. **Taxonomie rigoureuse de la non-réponse LRCLIB (3 catégories distinctes)** + vérification linguistique par sources externes hors LRCLIB + analyse de sensibilité aux données manquantes (MNAR / bornes de sensibilité).

---

## 1. Base de sondage réelle compilée (1985–2024, sans tirage)

Les fichiers auditables et leurs empreintes SHA-256 figurent dans `data/sampling_frame_v2/` :
- `weeks_inventory_1985_2024.csv` (`2 121` semaines, `SHA-256 : 38708b1427a188f0149ce2c848fe574cafd988ea0e71abcc9dac1063fb75aac0`)
- `sampling_frame_works_1985_2024.csv` (`20 809` œuvres canoniques, `SHA-256 : a7d8a7c55371ca846c7df6bbdee620641a7ac5a891f1fb7df7e1840e7bdd8c04`)

| Bloc quinquennal | Œuvres distinctes (toutes langues, Top 50→200) | Œuvres distinctes (**Top 50 constant**, toutes langues) | Profondeur officielle |
| :--- | :---: | :---: | :--- |
| **1985–1989** | 941 | 941 | Top 50 |
| **1990–1994** | 1 045 | 1 045 | Top 50 |
| **1995–1999** | 1 455 | 1 127 | Top 50 → Top 100 *(07/03/1998)* |
| **2000–2004** | 2 024 | 1 239 | Top 100 |
| **2005–2009** | 1 489 | 1 159 | Top 100 |
| **2010–2014** | 3 437 | 1 139 | Top 100 → Top 200 *(18/02/2012)* |
| **2015–2019** | 5 145 | 1 683 | Top 200 |
| **2020–2024** | 5 273 | 1 966 | Top 200 |
| **Total** | **20 809** *(9 135 artistes)* | **10 299** | **3 semaines absentes / 40 ans** |

---

## 2. Puissance comparée sur la base réelle (`scripts/simulate_power_v2_3.py`)

Simulation Monte Carlo directe sur les strates réelles, années réelles (`First_Year`) et grappes d'artistes réelles (`Artist_Slug`) de `sampling_frame_works_1985_2024.csv` (hors titres pilotes, $\text{SESOI} = \pm 3{,}0$ pts sur 39 ans, $\text{ICC}_{\text{REML}} = 0{,}3703$, $\text{SD} = 11{,}5103$, $\alpha = 0{,}05$ bilatéral) :

| Plan et estimateur | $N$ | $\text{DEFF}_{\text{Kish}}$ | $\bar{m}$ réel | Réplications | Puissance simulée | IC Wilson 95 % |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **REML stratifié (250/bloc, Top 50 constant) — Principal** | **2 000** | **1,000** | **~1,44–1,8** | **2 000** | **83,9 %** | **[82,2 % ; 85,5 %]** |
| WLS pondéré CR1 (Top 50 constant, 250/bloc) | 2 000 | 1,065 | 1,441 | 2 000 | 71,0 % | [69,0 % ; 73,0 %] |
| WLS pondéré CR1 (Top 50 constant, proportionnel) | 2 000 | 1,000 | 1,456 | 2 000 | 72,9 % | [70,9 % ; 74,8 %] |
| WLS pondéré CR1 (Top 50→200, 250/bloc) | 2 000 | 1,414 | 1,371 | 2 000 | 69,1 % | [67,0 % ; 71,1 %] |
| WLS pondéré CR1 (Top 50→200, 350/bloc) | 2 800 | 1,414 | 1,467 | 1 000 | 79,9 % | [77,3 % ; 82,3 %] |

> **Conséquence méthodologique clé** : la chute de puissance de WLS-CR1 (69,1 %) sur le cadre complet Top 50→200 est directement causée par la dispersion des poids ($\text{DEFF}_{\text{Kish}} = 1{,}414$) induite par le quadruplement artificiel de la profondeur du classement (50 → 200). Fixer le **cadre harmonisé Top 50 constant (1985–2024)** avec l'**estimateur REML à intercept aléatoire artiste** comme **analyse confirmatoire principale** garantit à la fois :
> 1. une comparabilité historique de profondeur constante (Top 50 de 1985 à 2024),
> 2. une adéquation exacte entre l'estimateur confirmatoire et la simulation de puissance ($\ge 83\%$),
> 3. la préservation de l'analyse pondérée WLS-CR1 (Top 50 constant et Top 50→200) comme analyse de robustesse populationnelle explicite.

---

## 3. Gestion rigoureuse des 3 catégories de non-réponse / paroles manquantes

Lors de l'évaluation de chaque titre tiré de la base de sondage, les cas sans métriques exploitables **ne sont jamais fusionnés** ; ils sont codés en **3 catégories mutuellement exclusives** dans `disposition_log.csv` :

1. **Catégorie A — Hors population cible (non francophone confirmé)** : langue vérifiée indépendamment de LRCLIB (par titre + métadonnées MusicBrainz / Discogs / Deezer, et écoute/extrait si ambigu). **Exclu du dénominateur de non-réponse** (ajuste uniquement $\hat{N}_h^{\text{FR}}$).
2. **Catégorie B — Non-réponse de source (francophone confirmé mais absent de LRCLIB)** : langue française confirmée hors LRCLIB (artiste/titre/métadonnées MusicBrainz/Discogs), mais aucune transcription sur LRCLIB. Comptabilisé dans le **taux de non-réponse $\hat{r}_h$ par période et par genre**.
3. **Catégorie C — Transcription inexploitable (francophone présent sur LRCLIB mais corrompu/abrégé ou $< 100$ mots)** : conservé dans `exclusion_log.csv` (et dans `MATTR_50` si $50 \le N < 100$).

### Analyse de sensibilité aux données manquantes (MNAR)
Si le taux de non-réponse de Catégorie B diffère de plus de 10 points entre périodes (ex. taux de paroles manquantes plus élevé en 1985–1989 qu'en 2020–2024), une **analyse de sensibilité par décalage (tipping-point / pattern-mixture)** évaluera quel écart moyen de `MATTR_100` chez les titres manquants serait nécessaire pour renverser la conclusion confirmatoire.

---

## 4. Plan confirmatoire, calibration linguistique et validation indépendante

- **Critère confirmatoire unique ($\alpha = 0{,}05$ bilatéral, hors pilote `In_Pilot = False`)** : pente temporelle $\beta_1$ de `MATTR_100_Surface` dans le modèle linéaire mixte REML $Y_i = \beta_0 + \beta_1 T_i + u_{a(i)} + \varepsilon_i$ sur l'échantillon stratifié ($N = 2\,000$, 250/bloc) du **cadre harmonisé Top 50 constant (1985–2024)**.
- **Test d'équivalence (TOST)** : si $p \ge 0{,}05$, équivalence déclarée uniquement si l'IC à 90 % de $39 \times \hat{\beta}_1$ est entièrement inclus dans $[-3{,}0 ; +3{,}0]$ points.
- **Famille secondaire (Holm-Bonferroni)** : estimateur pondéré WLS-CR1 (Top 50 constant et Top 50→200), modèle ajusté $T \times G$ (support commun 1991–2024 pour le rap), `MATTR_100_Lemmes`, `MATTR_100_NoRepeat`, `MTLD_Surface`, `Sophistication_Lexicale` (`Lexique383`), `Taux_Repetition_Pct`, `Ratio_Compression_Zlib`.
- **Triage linguistique calibré** sur 100 titres annotés humainement (argot/verlan/bilingue/étranger), **double implémentation indépendante** de `MATTR`/`MTLD`, **audit manuel de 30 transcriptions**, et **dépôt OSF Registries** avant le premier tirage aléatoire (`SEED_V2 = 20261124`).
