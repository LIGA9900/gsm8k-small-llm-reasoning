#!/usr/bin/env python3
"""Analyse des résultats : exactitude + IC de Wilson, test de McNemar exact, erreurs, graphique."""
import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

ORDER = ["direct", "cot", "sc", "pot", "pot_lenient", "extract", "extract_check", "extract_quote"]
PAIRS = [("cot", "direct"), ("sc", "cot"), ("pot", "cot"), ("pot", "sc"),
         ("pot_lenient", "cot"), ("pot_lenient", "sc"),
         ("extract", "cot"), ("extract_check", "cot"), ("extract_check", "extract"),
         ("extract_quote", "cot"), ("extract_quote", "extract")]


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def mcnemar_exact(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def load(results_dir):
    data = defaultdict(dict)
    for path in sorted(Path(results_dir).glob("*.jsonl")):
        with open(path, encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                data[(r["model"], r["strategy"])][r["id"]] = r
                if r["strategy"] == "pot" and "correct_lenient" in r:
                    v = dict(r)
                    v["strategy"] = "pot_lenient"
                    v["correct"] = r["correct_lenient"]
                    v["pred"] = r.get("pred_lenient")
                    if r["error_type"] in ("exec_error", "timeout"):
                        v["error_type"] = r["error_type"]
                    elif v["pred"] is None:
                        v["error_type"] = "no_answer"
                    else:
                        v["error_type"] = "ok" if v["correct"] else "wrong"
                    data[(r["model"], "pot_lenient")][r["id"]] = v
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results")
    args = ap.parse_args()
    res_dir = Path(args.results)
    data = load(res_dir)
    if not data:
        raise SystemExit("Aucun résultat trouvé.")

    rows = []
    for (model, strat), recs in sorted(data.items(), key=lambda x: (x[0][0], ORDER.index(x[0][1]))):
        n = len(recs)
        k = sum(1 for r in recs.values() if r["correct"])
        lo, hi = wilson(k, n)
        errs = defaultdict(int)
        for r in recs.values():
            errs[r["error_type"]] += 1
        lat = sum(r["latency"] for r in recs.values()) / n
        rows.append({"model": model, "strategy": strat, "n": n, "accuracy": round(k / n, 4),
                     "ci_low": round(lo, 4), "ci_high": round(hi, 4),
                     "wrong": errs["wrong"], "no_answer": errs["no_answer"],
                     "exec_error": errs["exec_error"], "timeout": errs["timeout"],
                     "sec_per_item": round(lat, 3)})

    with open(res_dir / "summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    md = ["# Résultats\n", "| Modèle | Stratégie | n | Exactitude | IC 95 % | Faux | Sans réponse | Erreur exec | Timeout | s/item |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['model']} | {r['strategy']} | {r['n']} | {r['accuracy']:.3f} | "
                  f"[{r['ci_low']:.3f}, {r['ci_high']:.3f}] | {r['wrong']} | {r['no_answer']} | "
                  f"{r['exec_error']} | {r['timeout']} | {r['sec_per_item']} |")

    md.append("\n## Tests de McNemar exacts (appariés)\n")
    md.append("| Modèle | Comparaison | A seul correct | B seul correct | p-valeur |")
    md.append("|---|---|---|---|---|")
    models = sorted({m for m, _ in data})
    for m in models:
        for a, b in PAIRS:
            if (m, a) in data and (m, b) in data:
                common = set(data[(m, a)]) & set(data[(m, b)])
                only_a = sum(1 for i in common if data[(m, a)][i]["correct"] and not data[(m, b)][i]["correct"])
                only_b = sum(1 for i in common if data[(m, b)][i]["correct"] and not data[(m, a)][i]["correct"])
                md.append(f"| {m} | {a} vs {b} | {only_a} | {only_b} | {mcnemar_exact(only_a, only_b):.4f} |")

    (res_dir / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    samples = ["# Exemples d'erreurs (analyse qualitative)\n"]
    for (model, strat), recs in sorted(data.items(), key=lambda x: (x[0][0], ORDER.index(x[0][1]))):
        wrong = [r for r in recs.values() if not r["correct"]][:5]
        samples.append(f"\n## {model} — {strat}\n")
        for r in wrong:
            out = (r["outputs"][0] if r["outputs"] else "")[:600].replace("\n", "\n> ")
            samples.append(f"**Q{r['id']}** (attendu {r['gold']}, obtenu {r['pred']}, type {r['error_type']})\n\n"
                           f"{r['question']}\n\n> {out}\n")
    (res_dir / "error_samples.md").write_text("\n".join(samples), encoding="utf-8")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(7, 4))
        width = 0.8 / max(1, len(models))
        for j, m in enumerate(models):
            xs, ys, err_lo, err_hi = [], [], [], []
            for i, s in enumerate(ORDER):
                row = next((r for r in rows if r["model"] == m and r["strategy"] == s), None)
                if row:
                    xs.append(i + j * width)
                    ys.append(row["accuracy"])
                    err_lo.append(row["accuracy"] - row["ci_low"])
                    err_hi.append(row["ci_high"] - row["accuracy"])
            ax.bar(xs, ys, width, yerr=[err_lo, err_hi], capsize=3, label=m.split("/")[-1])
        ax.set_xticks([i + width * (len(models) - 1) / 2 for i in range(len(ORDER))])
        ax.set_xticklabels(ORDER)
        ax.set_ylabel("Exactitude")
        ax.set_ylim(0, 1)
        ax.legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(res_dir / "accuracy.png", dpi=200)
    except ImportError:
        print("matplotlib absent : graphique ignoré.")

    print("\n".join(md))


if __name__ == "__main__":
    main()
