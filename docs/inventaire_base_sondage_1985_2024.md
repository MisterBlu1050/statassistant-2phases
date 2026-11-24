# Inventaire Exhaustif de la Base de Sondage Hebdomadaire (1985–2024)

- **Statut** : Compilation exhaustive achevée **sans tirage aléatoire** et **sans téléchargement de paroles** (Livrable 2 — Phase A clôturée)
- **Date de compilation** : 24 novembre 2026
- **Source** : Archives hebdomadaires officielles des singles en France (SNEP / Hung Medien, `lescharts.com/singles/YYYY-MM-DD`)
- **Script reproductible** : `scripts/compile_sampling_frame_1985_2024.py`

---

## 1. Artefacts produits et empreintes SHA-256 (`data/sampling_frame_v2/`)

| Fichier | Contenu | Empreinte SHA-256 |
| :--- | :--- | :--- |
| `weeks_inventory_1985_2024.csv` | **2 121 semaines** (date, statut HTTP, lignes parsées, rang min/max, ex-aequo) | `38708b1427a188f0149ce2c848fe574cafd988ea0e71abcc9dac1063fb75aac0` |
| `sampling_frame_works_1985_2024.csv` | **20 809 œuvres canoniques uniques** (`/chanson/...`), **9 135 artistes**, `First_Week`, `Best_Rank`, `Eligible_Top50_Constant`, `In_Pilot` | `a7d8a7c55371ca846c7df6bbdee620641a7ac5a891f1fb7df7e1840e7bdd8c04` |
| `frame_summary_1985_2024.json` | Synthèse machine-readable des effectifs et transitions | *(versionné)* |
| `power_simulation_wls_real_frame.json` | Simulation Monte Carlo (2 000 réps) de WLS-CR1 sur la base réelle | *(versionné)* |

---

## 2. Couverture hebdomadaire et semaines manquantes (transparence complète)

- **Semaines compilées avec succès (HTTP 200)** : **2 121 / 2 121** (de 52 à 54 semaines par année civile sur 40 ans).
- **Semaines manquantes (écarts > 7 jours entre deux classements consécutifs)** : exactement **3 semaines absentes** sur 40 ans (couverture $\approx 99{,}86\%$) :
  1. `1993-09-04 → 1993-09-18` *(14 jours : semaine du 11/09/1993 absente)*
  2. `2005-02-27 → 2005-03-12` *(13 jours : semaine du 05/03/2005 absente)*
  3. `2012-10-27 → 2012-11-10` *(14 jours : semaine du 03/11/2012 absente)*
- **Transitions exactes de profondeur officielle** (vérifiées sur les rangs `<span class="rk">` du tableau, et non par comptage de liens) :
  - **Top 50** : `1985-01-01` → `1998-02-28` *(51 lignes en 1985-01-01 dues à un ex-aequo officiel au rang 50)*
  - **Top 100** : dès le **`1998-03-07`** → `2012-02-11` *(ponctuellement 98–99 lignes en 2000-11-04 et 2001-07-21)*
  - **Top 200** : dès le **`2012-02-18`** → `2024-12-28` *(167 lignes en 2016-02-27)*

---

## 3. Effectifs réels vérifiés des 8 strates quinquennales ($N_h$, toutes langues)

| Bloc quinquennal | Œuvres uniques (Top 50→200) | Œuvres uniques (Top 50 constant) | Ratio Top 50→200 / Top 50 |
| :--- | :---: | :---: | :---: |
| **1985–1989** | 941 | 941 | 1,00× |
| **1990–1994** | 1 045 | 1 045 | 1,00× |
| **1995–1999** | 1 455 | 1 127 | 1,29× |
| **2000–2004** | 2 024 | 1 239 | 1,63× |
| **2005–2009** | 1 489 | 1 159 | 1,28× |
| **2010–2014** | 3 437 | 1 139 | 3,02× |
| **2015–2019** | 5 145 | 1 683 | 3,06× |
| **2020–2024** | 5 273 | 1 966 | 2,68× |
| **Total** | **20 809** *(9 135 artistes, $\bar{m} = 2{,}278$)* | **10 299** | **2,02×** |

- **Recouvrement avec le pilote ($N = 131$)** : **100 / 131** titres pilotes retrouvés et marqués `In_Pilot = Oui` dans la base hebdomadaire (les 31 autres étant des titres d'albums/classiques non entrés dans le Top Singles hebdomadaire ou crédités différemment).
- **Point d'attention sur la strate `1985–1989`** : avec **941 œuvres uniques toutes langues**, atteindre 250 titres confirmatoires francophones sur LRCLIB exige qu'au moins ~27 % des 941 titres soient à la fois francophones et disponibles sur LRCLIB — ce qui est plausible mais proche de la limite haute si la part francophone est ~45–50 % et la disponibilité LRCLIB ~60 %. Ce taux sera mesuré exactement lors de la phase de calibration/collecte après dépôt OSF de la **v1.3**.
