# Garde-fous scientifiques — Action 2

## Principe

Les tests statistiques restent déterministes (Phase 1). La Phase 2 ne reçoit que
les résumés et les diagnostics agrégés. Le logiciel n'infère **jamais** qu'une
collection est représentative simplement parce que ses calculs sont exacts.

## Déclarations méthodologiques (facultatives mais recommandées)

Chaque plan envoyé à `/api/phase1/run` peut inclure :

```json
{
  "mode": "reg",
  "y": "MATTR_50",
  "xs": ["Annee"],
  "alpha": 0.05,
  "language": "fr",
  "question": "La diversité lexicale évolue-t-elle dans le temps ?",
  "study_design": {
    "sampling_method": "non_probabilistic_purposive_selection",
    "representative": false,
    "cluster_column": "Artiste"
  }
}
```

La colonne `cluster_column` doit exister dans le tableau **de Phase 1**, à défaut
de quoi l'indépendance reste non vérifiée. Le fichier analytique du corpus musical
ne contient pas les artistes : une jointure locale, contrôlée et conforme à la
politique de confidentialité, serait nécessaire pour tester la dépendance par artiste.

Les seules valeurs d'échantillonnage reconnues dans le sceau analytique sont
`unknown`, `probability`, `simple_random`, `stratified_random`, `cluster_random`,
`systematic_random`, `non_probabilistic_purposive_selection`, `purposive`,
`convenience`, `quota` et `volunteer`.

## Comportement sans métadonnées

- `representativeness_unverified` : plan de sondage inconnu, aucune généralisation.
- `independence_unverified` : absence de variable de grappe exploitable, aucune indépendance certifiée.
- `lexical_scope_only` : les indicateurs MATTR/MTLD sont lexicaux, non linguistiques au sens global.
- `non_significance_not_equivalence` : un résultat non significatif n'établit pas l'équivalence.
- `structural_mattr_missing` : les textes trop courts exclus de MATTR-100 sont explicitement comptés.
- `temporal_composition_shift` : changement significatif de composition descriptive entre
  périodes (distance de variation totale >= 0,15), sans prétendre démontrer une causalité.

**Important :** ces alertes ne réparent ni le biais de sélection du corpus, ni
la non-indépendance. Elles rendent ces limites visibles et traçables.
La méthode de sondage, les dates de publication et les métriques doivent encore
être validées indépendamment des calculs.

## Vérifications

Exécuter `python -m pytest -q`. La suite comporte des tests synthétiques
pour le planificateur, l'échantillonnage, l'indépendance, la confusion temporelle,
MATTR-100, les petits groupes et les interprétations non significatives.

Le sceau `sha256_analysis_json` intègre désormais une version contrôlée
des déclarations `study_design`. Aucune valeur individuelle n'y figure.
