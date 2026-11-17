# Résultats

| Modèle | Stratégie | n | Exactitude | IC 95 % | Faux | Sans réponse | Erreur exec | Timeout | s/item |
|---|---|---|---|---|---|---|---|---|---|
| Qwen/Qwen2.5-0.5B-Instruct | direct | 200 | 0.040 | [0.020, 0.077] | 192 | 0 | 0 | 0 | 0.739 |
| Qwen/Qwen2.5-0.5B-Instruct | cot | 200 | 0.425 | [0.358, 0.494] | 115 | 0 | 0 | 0 | 2.534 |
| Qwen/Qwen2.5-0.5B-Instruct | sc | 200 | 0.490 | [0.422, 0.559] | 102 | 0 | 0 | 0 | 7.193 |
| Qwen/Qwen2.5-0.5B-Instruct | pot | 200 | 0.080 | [0.050, 0.126] | 26 | 146 | 12 | 0 | 1.272 |
| Qwen/Qwen2.5-0.5B-Instruct | pot_lenient | 200 | 0.330 | [0.269, 0.398] | 118 | 4 | 12 | 0 | 1.272 |
| Qwen/Qwen2.5-1.5B-Instruct | direct | 200 | 0.160 | [0.116, 0.217] | 168 | 0 | 0 | 0 | 0.263 |
| Qwen/Qwen2.5-1.5B-Instruct | cot | 200 | 0.705 | [0.638, 0.764] | 59 | 0 | 0 | 0 | 5.727 |
| Qwen/Qwen2.5-1.5B-Instruct | sc | 200 | 0.740 | [0.675, 0.796] | 52 | 0 | 0 | 0 | 14.363 |
| Qwen/Qwen2.5-1.5B-Instruct | pot | 200 | 0.420 | [0.354, 0.489] | 35 | 76 | 5 | 0 | 3.211 |
| Qwen/Qwen2.5-1.5B-Instruct | pot_lenient | 200 | 0.620 | [0.551, 0.684] | 68 | 3 | 5 | 0 | 3.211 |

## Tests de McNemar exacts (appariés)

| Modèle | Comparaison | A seul correct | B seul correct | p-valeur |
|---|---|---|---|---|
| Qwen/Qwen2.5-0.5B-Instruct | cot vs direct | 80 | 3 | 0.0000 |
| Qwen/Qwen2.5-0.5B-Instruct | sc vs cot | 29 | 16 | 0.0725 |
| Qwen/Qwen2.5-0.5B-Instruct | pot vs cot | 6 | 75 | 0.0000 |
| Qwen/Qwen2.5-0.5B-Instruct | pot vs sc | 3 | 85 | 0.0000 |
| Qwen/Qwen2.5-0.5B-Instruct | pot_lenient vs cot | 22 | 41 | 0.0226 |
| Qwen/Qwen2.5-0.5B-Instruct | pot_lenient vs sc | 16 | 48 | 0.0001 |
| Qwen/Qwen2.5-1.5B-Instruct | cot vs direct | 116 | 7 | 0.0000 |
| Qwen/Qwen2.5-1.5B-Instruct | sc vs cot | 21 | 14 | 0.3105 |
| Qwen/Qwen2.5-1.5B-Instruct | pot vs cot | 14 | 71 | 0.0000 |
| Qwen/Qwen2.5-1.5B-Instruct | pot vs sc | 6 | 70 | 0.0000 |
| Qwen/Qwen2.5-1.5B-Instruct | pot_lenient vs cot | 18 | 35 | 0.0270 |
| Qwen/Qwen2.5-1.5B-Instruct | pot_lenient vs sc | 10 | 34 | 0.0004 |
