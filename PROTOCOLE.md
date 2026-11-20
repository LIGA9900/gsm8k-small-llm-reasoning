# Protocole : « lister les données » aide-t-il un petit modèle à raisonner ?

Document écrit le 19 novembre 2026, **avant** l'évaluation finale sur les 300 problèmes neufs.

## Question et hypothèse
Dans l'étude initiale, la majorité des erreurs de Qwen2.5-1.5B (chaîne de pensée) viennent d'une mauvaise lecture de l'énoncé ou d'un raisonnement faux (41 erreurs sur 50 classées à la main).
**Hypothèse :** demander au modèle d'expliciter les données de l'énoncé avant de résoudre améliore son exactitude par rapport à la chaîne de pensée simple (`cot`).

## Données
- **Réglage (dev)** : 100 problèmes de la partie *entraînement* de GSM8K (graine 1). Servent uniquement à choisir la formulation de la consigne.
- **Évaluation finale (new)** : 300 problèmes de la partie *test* de GSM8K, différents des 200 de l'étude initiale (graine 0, problèmes 201 à 500 après mélange).
- Modèle principal : Qwen2.5-1.5B-Instruct. Limite de génération : 768 jetons pour toutes les stratégies.

## Variantes de consigne
- `cot` : chaîne de pensée simple (référence).
- `extract` (version 1) : écrire la question puis la liste des données, puis résoudre.
- `extract_quote` (version 2) : recopier mot pour mot les phrases contenant des nombres, puis résoudre.
- Règle fixée à l'avance : au plus 3 versions de consigne sur le jeu de réglage. Deux ont été utilisées, la troisième ne l'est pas.

## Résultats sur le jeu de réglage (100 problèmes, Qwen2.5-1.5B)
| Stratégie | Exactitude | IC 95 % |
|---|---|---|
| cot | 84 % | [75,6 ; 89,9] |
| extract (v1) | 75 % | [65,7 ; 82,5] |
| extract_quote (v2) | 81 % | [72,2 ; 87,5] |

Tests de McNemar : extract contre cot, p = 0,078 ; extract_quote contre cot, p = 0,648 ; extract_quote contre extract, p = 0,210. **Aucune variante ne dépasse `cot` sur le jeu de réglage.**

Observations qualitatives :
- Avec `extract`, au moins 3 des 15 problèmes perdus viennent d'une donnée mal recopiée ou inventée dans la liste.
- Avec `extract_quote`, le modèle ne recopie pas fidèlement : la plupart des lignes « citées » sont reformulées (mesure grossière : environ une ligne sur cinq est identique à l'énoncé).
- Les erreurs restantes de `extract_quote` sont surtout des erreurs de raisonnement (par exemple « twice » interprété comme une division).
- Le jeu de réglage vient de la partie entraînement de GSM8K : le modèle l'a peut-être déjà vue. L'exactitude de `cot` y est de 84 %, contre 70,5 % sur le jeu de test initial.

## Décision (fixée avant l'évaluation finale)
La variante `extract_quote`, meilleure des deux sur le jeu de réglage, est figée telle quelle. L'évaluation finale compare `cot` et `extract_quote` sur les 300 problèmes neufs, avec le test de McNemar apparié. La variante `extract` (v1) pourra être ajoutée à titre exploratoire, et tous les résultats seront publiés, y compris négatifs.

## Critère de réussite
- Succès : gain d'au moins 3 points d'exactitude et p < 0,05.
- Sinon : on conclut que, pour ce modèle, la consigne ne montre pas d'effet détectable, et on le publie.
- Avec 300 problèmes, seul un gain d'environ 6 à 7 points est détectable de façon fiable.

## Limites connues
Un seul modèle principal, un seul jeu de données, une seule personne pour la classification manuelle des erreurs, et une consigne que le modèle ne suit pas fidèlement (version 2).
