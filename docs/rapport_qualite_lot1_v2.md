# Rapport de Contrôle Qualité — Corpus V2 — Lot 1 (`Draw_Order = 1..20`, 160 candidats)

- **Statut** : Contrôle qualité **Lot 1 achevé** (aucune analyse de la pente temporelle $\beta_1$ effectuée — respect strict de l'aveuglement confirmatoire)
- **Date** : 24 novembre 2026
- **Branche Git** : `feature/corpus-scientifique-v2`
- **Script reproductible** : `scripts/collect_corpus_v2.py --max-draw-order 20`
- **Environnement figé** : `data/corpus_v2_collect/environment_lock.json` (`simplemma 2.0.0`, `lingua-language-detector 2.1.1`)
- **Droit d'auteur** : **0 parole brute** stockée ou publiée (métriques dérivées + `Lyrics_SHA256` + `LRCLIB_ID` uniquement).

---

## 1. Bilan des décisions par strate (`N = 160` évaluations dans l'ordre exact `Draw_Order = 1..20`)

| Bloc quinquennal | Candidats totaux (hors pilote) | Évalués (Lot 1) | `INCLUDED` (FR exploitable) | `EXCLUDED_NON_FRENCH` | `LYRICS_MISSING_PENDING_LANG_VERIFY` | `PENDING_HUMAN_REVIEW` | Rendement observé | Projection sur la strate *(cible = 250)* |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1985–1989** | 928 | 20 | **8** | 10 | 2 | 0 | 40 % | **~371** |
| **1990–1994** | 1 037 | 20 | **6** | 9 | 5 | 0 | 30 % | **~311** |
| **1995–1999** | 1 112 | 20 | **5** | 14 | 1 | 0 | 25 % | **~278** |
| **2000–2004** | 1 228 | 20 | **7** | 7 | 6 | 0 | 35 % | **~430** |
| **2005–2009** | 1 155 | 20 | **6** | 10 | 4 | 0 | 30 % | **~346** |
| **2010–2014** | 1 095 | 20 | **6** | 13 | 1 | 0 | 30 % | **~328** |
| **2015–2019** | 1 678 | 20 | **17** | 3 | 0 | 0 | 85 % | **~1 426** |
| **2020–2024** | 1 967 | 20 | **14** | 5 | 1 | 0 | 70 % | **~1 377** |
| **Total Lot 1** | **10 200** | **160** | **69** | **71** | **20** | **0** | **43,1 %** | **8 / 8 strates > 250** |

---

## 2. Contrôles qualité vérifiés sur le Lot 1

1. **Précision d'appariement LRCLIB (`69 / 69` exacts)** : contrôle systématique de l'artiste et du titre retournés par LRCLIB pour les 69 titres `INCLUDED`. Les 8 écarts typographiques mineurs détectés sont tous des variations de ponctuation ou d'accents (`Oh! Mon bateau` vs `Oh, mon bateau !`, `O.C.B.` vs `O C B`, `Dis-moi` vs `Dis‐moi`, `RK & Maes` vs `RK/MAES`) — **0 erreur d'appariement**.
2. **Intégrité des métriques dérivées** :
   - **69 lignes** dans `corpus_v2_metrics.csv`, **0 NA inattendu** sur `MATTR_100_Surface`, **0 `MTLD_ZeroFactor_Flag = Oui`**.
   - **3 NA structurels** sur `MATTR_100_NoRepeat` (chansons dont le texte dédupliqué passe sous 100 mots : aucune bascule silencieuse en TTR simple).
3. **Taux de paroles manquantes LRCLIB (`20 / 160 = 12,5 %`)** : plus élevé entre 1990 et 2009 (`15–30 %`) qu'entre 2015 et 2024 (`0–5 %`), ce qui valide empiriquement l'importance de la **catégorisation séparée** (`LYRICS_MISSING_PENDING_LANG_VERIFY`, jamais classée arbitrairement en non francophone) et de l'**analyse de sensibilité MNAR** préenregistrée.
4. **Empreintes SHA-256 du Lot 1** :
   - `data/corpus_v2_collect/disposition_log.csv` : `a5fa0f81d17ca97a4d94d4a1cb2ff1cd760aa1b6c7fd1adeb715cd91df903542`
   - `data/corpus_v2_collect/corpus_v2_metrics.csv` : `7969bf60ab68e0e81f795b41e853aa5d3ecf37126b660c5eb62e99fabbb8f16d`

---

## 3. Décision opérationnelle

Le pipeline de collecte du Lot 1 est **propre, exact (0 erreur d'appariement sur 69 inclus) et projette d'atteindre les 250 titres confirmatoires dans les 8 strates** (strate la plus serrée : `1995–1999`, ~278 projetés). Il est prêt à poursuivre la collecte incrémentale dans l'ordre exact `Draw_Order = 21, 22, ...` jusqu'à atteindre `250 INCLUDED` par strate (ou épuisement documenté de la strate).
