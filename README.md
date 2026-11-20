# Raisonnement des petits modèles de langage : comparaison de stratégies sur GSM8K

Étude reproductible : quelle stratégie améliore le plus le raisonnement mathématique de petits modèles (Qwen2.5-0.5B et 1.5B-Instruct) ?

Stratégies comparées :
- `direct` : réponse sans explication
- `cot` : chaîne de pensée (raisonnement étape par étape)
- `sc` : auto-cohérence (5 échantillons, vote majoritaire, température 0,7)
- `pot` : programme de pensée (le modèle écrit un programme Python qui est exécuté)

## Protocole
- Données : 200 problèmes du jeu de test GSM8K, tirés avec une graine fixe (0), identiques pour toutes les stratégies.
- Mesures : exactitude avec intervalle de confiance de Wilson à 95 %, tests de McNemar exacts appariés.
- Limites de génération : 512 jetons (128 en mode `direct`).
- Matériel : GPU gratuit de Google Colab (T4).

## Résultats (exactitude sur 200 problèmes)

| Stratégie | Qwen2.5-0.5B | Qwen2.5-1.5B |
|---|---|---|
| direct | 4,0 % | 16,0 % |
| cot | 42,5 % | 70,5 % |
| sc | 49,0 % | 74,0 % |
| pot (strict) | 8,0 % | 42,0 % |
| pot (indulgent) | 33,0 % | 62,0 % |

Tests de McNemar (p-valeurs) :
- `cot` meilleur que `direct` : p < 0,0001 pour les deux modèles.
- `sc` contre `cot` : p = 0,0725 (0,5B) et p = 0,3105 (1,5B). Le gain n'est **pas** significatif, pour environ 2,5 fois plus de temps de calcul.
- `pot` contre `cot` : `cot` est meilleur, p < 0,0001.

### Note sur `pot`
Le score « strict » exige que le programme du modèle définisse une variable `answer`. Beaucoup de programmes ne le font pas (146/200 pour le 0,5B, 76/200 pour le 1,5B). Le score « indulgent » reprend alors le dernier nombre affiché. **Cette règle indulgente a été choisie après avoir vu les résultats stricts** ; les deux scores sont donc rapportés.

## Analyse des erreurs
50 des 59 erreurs de `cot` (Qwen 1,5B) ont été classées à la main (fichier `erreurs_cot_1.5B_classe.csv`) :

| Catégorie | Nombre |
|---|---|
| A. Lecture de l'énoncé (information ignorée ou mal comprise) | 21 |
| B. Logique (mauvais raisonnement) | 20 |
| C. Calcul | 7 |
| D. Format (réponse coupée) | 1 |
| E. Donnée douteuse (exclue) | 1 |

La classification est subjective (une seule personne). Les 50 erreurs sont les premières dans l'ordre mélangé du fichier, pas un échantillon aléatoire des 59.

## Limites
- Un seul jeu de données, 200 problèmes, deux petits modèles : les résultats sont un point de départ, pas des conclusions générales.
- Quelques réponses sont coupées par la limite de 512 jetons.
- Au moins une donnée de référence est incohérente avec son énoncé (id 952).

## Reproduire
```bash
pip install -r requirements.txt
python run_experiment.py --model Qwen/Qwen2.5-1.5B-Instruct --strategy all --n 200 --out results_v2
python analyze.py --results results_v2
```
Le mode `pot` exécute du code généré par le modèle : à lancer dans Colab, pas sur un ordinateur personnel.

## Contenu
- `run_experiment.py` : lance les expériences
- `analyze.py` : statistiques, tests et graphique
- `results_v2/` : résultats bruts (`.jsonl`), `summary.md`, `summary.csv`, `accuracy.png`
- `erreurs_cot_1.5B_classe.csv` : analyse manuelle des erreurs
- - `PROTOCOLE.md` : protocole de l'étude 2, écrit avant le test final, avec les résultats
- `results_new/` : résultats bruts de l'étude 2 (300 problèmes, `.jsonl`)

## Auteur
Mohamed Fouad Akorédé LIGALI, Licence en informatique de gestion (ENEAM, Bénin).
## Étude 2 : « lister les données » aide-t-il ? (résultat négatif)

Évaluation finale sur 300 problèmes neufs du jeu de test GSM8K, avec un protocole écrit avant le test (voir `PROTOCOLE.md`). Modèle : Qwen2.5-1.5B-Instruct.

| Stratégie | Exactitude | IC 95 % |
|---|---|---|
| cot | 71,3 % | [66,0 ; 76,2] |
| extract_quote | 70,7 % | [65,3 ; 75,5] |

Test de McNemar exact : p = 0,91. **Aucun effet détectable** : recopier les phrases contenant des nombres avant de résoudre n'améliore pas l'exactitude de ce modèle, et la méthode est plus lente. Les résultats bruts sont dans `results_new/`.
