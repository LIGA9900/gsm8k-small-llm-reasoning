# Raisonnement des petits modèles de langage : comparer des stratégies

Projet de recherche reproductible : quelle stratégie améliore le plus le raisonnement mathématique de petits modèles (0,5 à 3 milliards de paramètres) ?

Stratégies comparées : `direct`, `cot` (chaîne de pensée), `sc` (auto-cohérence), `pot` (programme de pensée).

## Lancer sur Google Colab (GPU gratuit)

```bash
pip install -r requirements.txt
python run_experiment.py --model Qwen/Qwen2.5-0.5B-Instruct --strategy all --n 200
python run_experiment.py --model Qwen/Qwen2.5-1.5B-Instruct --strategy all --n 200
python analyze.py --results results
```

Test rapide sans GPU : `python run_experiment.py --model mock --dataset toy --strategy all --out /tmp/test`

Le script reprend là où il s'est arrêté (fichiers `.jsonl` dans `results/`).
Le mode `pot` exécute du code généré par le modèle : lance-le dans Colab, pas sur ton ordinateur personnel.

## Protocole (à fixer avant de lancer les expériences)

- H1 : `cot` fait mieux que `direct`.
- H2 : `sc` fait mieux que `cot`.
- H3 : `pot` fait mieux que `cot` pour les plus petits modèles.
- Mêmes 200 problèmes (graine fixe) pour toutes les stratégies ; tests de McNemar appariés.
- Au moins 2 tailles de modèles, pour étudier l'effet de la taille.

## Pour dépasser la simple comparaison (contribution originale)

Choisis une question précise après avoir lu les articles : par exemple, quand l'auto-cohérence cesse d'aider (`agreement` dans les résultats), ou combiner `pot` et `sc` avec un vote sur les résultats exécutés.
Analyse les erreurs à la main (`results/error_samples.md`) et classe-les : lecture de l'énoncé, arithmétique, logique, format.

## Livrables

1. Dépôt GitHub avec ce code, `results/` et un README.
2. Rapport de 4 pages (`report.tex`) avec tableau, graphique et analyse d'erreurs.
3. Lien vers les deux dans ton CV et tes courriels aux professeurs.
