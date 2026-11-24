# Inventaire Vérifiable de la Base de Sondage Hebdomadaire (1985–2024)

- **Statut** : Inventaire préalable **sans tirage aléatoire** (Livrable 2 — Phase A)
- **Date d'audit** : 24 novembre 2026
- **Source vérifiée** : Archives hebdomadaires officielles des singles en France (SNEP / Hung Medien, `https://lescharts.com/singles/YYYY-MM-DD`)
- **Preuve machine-readable** : `docs/sampling_frame_inventory_1985_2024.json` (générée par `scripts/inventory_sampling_frame.py`)

---

## 1. Couverture annuelle et profondeur exacte de classement (40 / 40 années)

Le sondage d'une semaine représentative (début juillet) pour chacune des **40 années civiles de 1985 à 2024** confirme une **couverture de 40 / 40 années (0 année manquante)**, avec **3 régimes historiques de profondeur** clairement identifiés :

| Régime de profondeur | Période exacte vérifiée | Nombre d'années | Entrées classées / semaine | Remarque méthodologique |
| :--- | :--- | :---: | :---: | :--- |
| **Top 50** | **1985 – 1997** | 13 ans | 50 *(51 en 1985)* | Période historique du Top 50 ventes physiques |
| **Top 100** | **1998 – 2011** | 14 ans | 100 *(99 en 2007)* | Doublement de profondeur + intégration des téléchargements |
| **Top 200** | **2012 – 2024** | 13 ans | 200 *(199 en 2012)* | Quadruplement de profondeur + intégration du streaming (et règle SNEP juillet 2024) |
| **Total** | **1985 – 2024** | **40 ans** | **50 → 200** | **0 année manquante** |

> [!IMPORTANT]
> Ce passage mesuré de **Top 50 → Top 100 → Top 200** justifie pleinement l'inclusion dans le Protocole v1.2 de l'**analyse de sensibilité à profondeur constante Top 50** sur l'ensemble des 40 années (1985–2024).

---

## 2. Test de faisabilité sur la strate la plus étroite (`1985–1989`, Top 50)

Pour vérifier avant collecte si l'objectif de **250 chansons francophones confirmatoires par bloc quinquennal** ($N = 2\,000$ total) est accessible même dans la strate la plus étroite (`1985–1989`, Top 50) :

- **Mesure empirique sur 1985** (12 semaines mensuelles sondées sur 52, 12/12 réussies) : **198 œuvres distinctes** (toutes langues confondues) recensées sur seulement 12 semaines.
- **Projection prudente sur 52 semaines/an × 5 ans (`1985–1989`)** :
  - Estimation basse du nombre d'œuvres distinctes toutes langues sur 1985–1989 : **~1 100 à 1 350 titres uniques**.
  - En supposant une part francophone de ~45–55 % dans le Top 50 des années 1985–1989 : **~500 à 700 œuvres francophones distinctes** dans ce seul bloc quinquennal.
- **Verdict de faisabilité préliminaire** :
  - La base de sondage hebdomadaire permet a priori d'atteindre les **250 titres confirmatoires hors pilote** dans chacun des 8 blocs quinquennaux (y compris `1985–1989`), **sous réserve** que le taux de disponibilité exploitable sur LRCLIB dans le bloc `1985–1989` dépasse ~50 % (ce qui sera mesuré exactement lors de la compilation intégrale de la base de sondage, sans biais silencieux).

---

## 3. Étapes suivantes (conditionnées au feu vert sur Protocole v1.2)

1. **Validation de la v1.2** et dépôt figé sur **OSF Registries**.
2. **Compilation exhaustive de la base de sondage** (`sampling_frame_1985_2024.csv` : ensemble des semaines 1985–2024 dédupliquées par œuvre unique `/chanson/...`, avec année de première entrée, meilleur rang atteint pour le filtre Top 50 constant, et taille exacte $N_h$ de chaque strate).
3. **Calibration humaine du classifieur de langue** (100 titres annotés couvrant argot/verlan/bilingue).
4. **Tirage aléatoire stratifié reproductible** (`SEED_V2 = 20261124`) de $N = 2\,000$ titres confirmatoires hors pilote + journalisation des paroles manquantes LRCLIB.
