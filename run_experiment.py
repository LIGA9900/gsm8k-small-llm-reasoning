#!/usr/bin/env python3
"""Évaluation de stratégies de raisonnement sur de petits modèles de langage.

Stratégies : direct, cot (chaîne de pensée), sc (auto-cohérence), pot (programme de pensée),
extract (lister les données avant de résoudre), extract_check (extract + relecture, exploratoire),
extract_quote (recopier mot pour mot les phrases contenant des nombres avant de résoudre).
« all » = les quatre premières (comme dans l'étude initiale).
Jeux de données : gsm8k (Hugging Face), toy (10 problèmes locaux), ou un fichier .jsonl
avec les champs "question" et "answer".
Découpages de gsm8k (--split) :
    old : les 200 problèmes de test de l'étude initiale (défaut)
    dev : 100 problèmes de la partie entraînement, pour régler les consignes
    new : 300 problèmes de test NEUFS (différents des 200 de « old »), pour l'évaluation finale

Exemples :
    python run_experiment.py --model Qwen/Qwen2.5-1.5B-Instruct --strategy all --n 200
    python run_experiment.py --model Qwen/Qwen2.5-1.5B-Instruct --split dev --strategy cot,extract --out results_dev
    python run_experiment.py --model mock --dataset toy --strategy all --out /tmp/test_results
"""
import argparse
import json
import math
import random
import re
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

DEFAULT_STRATEGIES = ["direct", "cot", "sc", "pot"]
STRATEGIES = DEFAULT_STRATEGIES + ["extract", "extract_check", "extract_quote"]
SPLIT_DEFAULTS = {"old": (200, 0), "dev": (100, 1), "new": (300, 0)}  # (n, graine du mélange)

TOY = [
    ("Tom has 5 apples and buys 3 more bags with 4 apples each. How many apples does he have now?", 17),
    ("A train travels 60 km per hour for 3 hours. How many kilometers does it travel?", 180),
    ("Sara had 50 dollars. She spent 18 dollars on a book and 12 dollars on lunch. How many dollars are left?", 20),
    ("A box holds 8 pencils. How many pencils are there in 7 boxes?", 56),
    ("There are 24 students and half of them are girls. 3 girls wear glasses. How many girls do not wear glasses?", 9),
    ("A shirt costs 20 dollars and is discounted by 25 percent. What is the new price in dollars?", 15),
    ("Mia reads 12 pages per day. How many pages does she read in 2 weeks?", 168),
    ("A farmer has 3 fields with 15 cows each and sells 10 cows. How many cows remain?", 35),
    ("Jake runs 4 km on Monday, Wednesday and Friday of each week. How many kilometers does he run in 4 weeks?", 48),
    ("A recipe needs 3 eggs for 12 cookies. How many eggs are needed for 60 cookies?", 15),
]

NUM_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?")
FINAL_RE = re.compile(r"final answer[^0-9\-]*(-?\d[\d,]*(?:\.\d+)?)", re.IGNORECASE)
CODE_RE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)


# ---------------------------------------------------------------- données
def to_number(s):
    try:
        return float(s.replace(",", ""))
    except (ValueError, AttributeError):
        return None


def load_data(name, n, seed, split="old"):
    if name == "toy":
        items = [{"id": i, "question": q, "gold": float(a)} for i, (q, a) in enumerate(TOY)]
    elif name == "gsm8k":
        from datasets import load_dataset
        ds = load_dataset("openai/gsm8k", "main", split="train" if split == "dev" else "test")
        items = []
        for i, row in enumerate(ds):
            gold = to_number(row["answer"].split("####")[-1].strip())
            items.append({"id": i, "question": row["question"], "gold": gold})
    else:
        items = []
        with open(name, encoding="utf-8") as f:
            for i, line in enumerate(f):
                row = json.loads(line)
                gold = row["answer"] if isinstance(row["answer"], (int, float)) else to_number(str(row["answer"]))
                items.append({"id": i, "question": row["question"], "gold": float(gold)})
    rng = random.Random(seed)
    rng.shuffle(items)
    if split == "new":
        # Les 200 premiers (mélange de graine 0) sont ceux de l'étude initiale : on les saute.
        return items[200:200 + n]
    return items[:n] if n else items


# ---------------------------------------------------------------- prompts
def build_prompt(strategy, question):
    if strategy == "direct":
        return (f"Solve this math problem. Give only the final numeric answer, with no explanation, "
                f"in the format 'Final answer: <number>'.\n\nProblem: {question}")
    if strategy in ("cot", "sc"):
        return (f"Solve this math problem step by step. End your response with a line of the form "
                f"'Final answer: <number>'.\n\nProblem: {question}")
    if strategy == "pot":
        return (f"Write a Python program that solves this math problem. Store the final numeric result "
                f"in a variable named `answer`. Output only the code inside a ```python block.\n\n"
                f"Problem: {question}")
    if strategy == "extract":
        return (f"Solve this math problem. First write 'Question:' followed by what is being asked, "
                f"then 'Data:' followed by a list of every number and fact given in the problem. "
                f"Then solve step by step using these data. End your response with a line of the form "
                f"'Final answer: <number>'.\n\nProblem: {question}")
    if strategy == "extract_check":
        return (f"Solve this math problem. First write 'Question:' followed by what is being asked, "
                f"then 'Data:' followed by a list of every number and fact given in the problem. "
                f"Then solve step by step using these data. Before the final answer, re-read the problem "
                f"and check that you used every piece of data and answered the question that was asked. "
                f"End your response with a line of the form 'Final answer: <number>'.\n\nProblem: {question}")
    if strategy == "extract_quote":
        return (f"Solve this math problem. First, under the heading 'Quoted facts:', copy every sentence of the "
                f"problem that contains a number, exactly as written, without changing or computing anything. "
                f"Then, under 'Question:', restate what is being asked. Then solve step by step, using only "
                f"the quoted facts. End your response with a line of the form "
                f"'Final answer: <number>'.\n\nProblem: {question}")
    raise ValueError(strategy)


# ---------------------------------------------------------------- extraction
def extract_number(text):
    m = FINAL_RE.search(text)
    if m:
        return to_number(m.group(1))
    nums = NUM_RE.findall(text)
    return to_number(nums[-1]) if nums else None


def extract_code(text):
    blocks = CODE_RE.findall(text)
    if blocks:
        return blocks[0]
    return text if "answer" in text else None


def _limit_resources():
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (1 << 30, 1 << 30))
        resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
    except Exception:
        pass


def run_code(code, timeout=8):
    """Exécute le code généré dans un sous-processus isolé.

    Retourne (strict, indulgent, type_erreur, repli_utilisé) :
    - strict : valeur de la variable `answer` (règle fixée à l'avance) ;
    - indulgent : `answer` si elle existe, sinon le dernier nombre affiché ;
    - repli_utilisé : True si `answer` manquait et que le dernier nombre affiché a servi.
    """
    if not code:
        return None, None, "no_answer", False
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "prog.py"
        path.write_text(code + "\ntry:\n    print('__ANSWER__', answer)\nexcept NameError:\n    pass\n",
                        encoding="utf-8")
        kwargs = {}
        if sys.platform != "win32":
            kwargs["preexec_fn"] = _limit_resources
        try:
            r = subprocess.run([sys.executable, str(path)], capture_output=True, text=True,
                               timeout=timeout, cwd=d, **kwargs)
        except subprocess.TimeoutExpired:
            return None, None, "timeout", False
        if r.returncode != 0:
            return None, None, "exec_error", False
        m = re.search(r"__ANSWER__\s+(.+)", r.stdout)
        if m:
            val = to_number(m.group(1).strip().rstrip("."))
            return val, val, ("ok" if val is not None else "no_answer"), False
        nums = NUM_RE.findall(r.stdout)
        lenient = to_number(nums[-1]) if nums else None
        return None, lenient, "no_answer", lenient is not None


def is_correct(pred, gold):
    return pred is not None and gold is not None and math.isclose(pred, gold, rel_tol=1e-4, abs_tol=1e-4)


# ---------------------------------------------------------------- modèles
class HFModel:
    def __init__(self, name):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(name)
        self.tok.padding_side = "left"
        if self.tok.pad_token is None:
            self.tok.pad_token = self.tok.eos_token
        self.model = AutoModelForCausalLM.from_pretrained(name, torch_dtype="auto", device_map="auto")
        self.model.eval()

    def generate(self, prompts, items, strategy, max_new_tokens, temperature, k):
        texts = [self.tok.apply_chat_template([{"role": "user", "content": p}], tokenize=False,
                                              add_generation_prompt=True) for p in prompts]
        enc = self.tok(texts, return_tensors="pt", padding=True).to(self.model.device)
        kw = dict(max_new_tokens=max_new_tokens, do_sample=temperature > 0,
                  num_return_sequences=k, pad_token_id=self.tok.pad_token_id)
        if temperature > 0:
            kw.update(temperature=temperature, top_p=0.95)
        with self.torch.no_grad():
            out = self.model.generate(**enc, **kw)
        out = out[:, enc["input_ids"].shape[1]:]
        dec = self.tok.batch_decode(out, skip_special_tokens=True)
        return [dec[i * k:(i + 1) * k] for i in range(len(prompts))]


class MockModel:
    """Faux modèle déterministe pour tester la chaîne de traitement sans GPU."""
    P = {"direct": 0.4, "cot": 0.6, "sc": 0.6, "pot": 0.75, "extract": 0.65, "extract_check": 0.65, "extract_quote": 0.65}

    def __init__(self, seed=0):
        self.rng = random.Random(seed)

    def _value(self, item, strategy):
        gold = item["gold"]
        return gold if self.rng.random() < self.P[strategy] else gold + self.rng.choice([-3, -1, 1, 2, 10])

    def generate(self, prompts, items, strategy, max_new_tokens, temperature, k):
        outs = []
        for it in items:
            row = []
            for _ in range(k):
                v = self._value(it, strategy)
                if strategy == "pot":
                    r = self.rng.random()
                    if r < 0.08:
                        row.append("```python\nanswer = 1 / 0\n```")
                    elif r < 0.12:
                        row.append("I cannot write code for this.")
                    elif r < 0.45:
                        row.append(f"```python\nresult = {v:g}\nprint(result)\n```")
                    else:
                        row.append(f"```python\nanswer = {v:g}\n```")
                elif strategy == "direct":
                    row.append(f"Final answer: {v:g}")
                else:
                    row.append(f"Step 1: reason about the problem.\nStep 2: compute.\nFinal answer: {v:g}")
            outs.append(row)
        return outs


# ---------------------------------------------------------------- évaluation
def score(strategy, item, gens):
    rec = {"outputs": gens}
    if strategy == "sc":
        preds = [extract_number(g) for g in gens]
        valid = [round(p, 4) for p in preds if p is not None]
        if valid:
            pred, votes = Counter(valid).most_common(1)[0]
            rec.update(pred=pred, agreement=votes / len(gens), preds=preds)
            rec["error_type"] = "ok"
        else:
            rec.update(pred=None, agreement=0.0, preds=preds, error_type="no_answer")
    elif strategy == "pot":
        strict, lenient, err, fallback = run_code(extract_code(gens[0]))
        rec.update(pred=strict, error_type=err, pred_lenient=lenient, fallback_used=fallback)
        rec["correct_lenient"] = is_correct(lenient, item["gold"])
    else:
        pred = extract_number(gens[0])
        rec.update(pred=pred, error_type="ok" if pred is not None else "no_answer")
    rec["correct"] = is_correct(rec["pred"], item["gold"])
    if rec["error_type"] == "ok" and not rec["correct"]:
        rec["error_type"] = "wrong"
    return rec


def load_done(path):
    done = set()
    if path.exists():
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    done.add(json.loads(line)["id"])
                except Exception:
                    pass
    return done


def run_strategy(lm, items, strategy, args, out_path, model_name):
    done = load_done(out_path)
    todo = [it for it in items if it["id"] not in done]
    print(f"[{strategy}] {len(done)} déjà faits, {len(todo)} à faire")
    with open(out_path, "a", encoding="utf-8") as f:
        for i in range(0, len(todo), args.batch_size):
            batch = todo[i:i + args.batch_size]
            prompts = [build_prompt(strategy, it["question"]) for it in batch]
            t0 = time.time()
            if strategy == "sc":
                gens = lm.generate(prompts, batch, strategy, args.max_new_tokens, args.temperature, args.samples)
            elif strategy == "direct":
                gens = lm.generate(prompts, batch, strategy, args.direct_max_tokens, 0.0, 1)
            else:
                gens = lm.generate(prompts, batch, strategy, args.max_new_tokens, 0.0, 1)
            latency = (time.time() - t0) / len(batch)
            for it, g in zip(batch, gens):
                rec = {"id": it["id"], "model": model_name, "strategy": strategy, "split": args.split,
                       "question": it["question"], "gold": it["gold"], "latency": latency}
                rec.update(score(strategy, it, g))
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            print(f"[{strategy}] {min(i + args.batch_size, len(todo))}/{len(todo)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    ap.add_argument("--strategy", default="all",
                    help="direct,cot,sc,pot,extract,extract_check ou all (= direct,cot,sc,pot)")
    ap.add_argument("--dataset", default="gsm8k", help="gsm8k, toy ou chemin .jsonl")
    ap.add_argument("--split", default="old", choices=["old", "dev", "new"],
                    help="old = 200 problèmes initiaux, dev = 100 d'entraînement, new = 300 neufs")
    ap.add_argument("--n", type=int, default=None, help="nombre de problèmes (défaut selon --split)")
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--max-new-tokens", type=int, default=512)
    ap.add_argument("--direct-max-tokens", type=int, default=128, help="longueur max de la réponse en mode direct")
    ap.add_argument("--samples", type=int, default=5, help="échantillons pour sc")
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="results")
    args = ap.parse_args()

    strategies = DEFAULT_STRATEGIES if args.strategy == "all" else args.strategy.split(",")
    for s in strategies:
        if s not in STRATEGIES:
            sys.exit(f"Stratégie inconnue : {s}")

    default_n, data_seed = SPLIT_DEFAULTS[args.split]
    if args.split == "old":
        data_seed = args.seed  # comportement d'origine
    if args.n is None:
        args.n = default_n
    random.seed(args.seed)
    items = load_data(args.dataset, args.n, data_seed, args.split)
    if args.model == "mock":
        lm = MockModel(args.seed)
    else:
        from transformers import set_seed
        set_seed(args.seed)
        lm = HFModel(args.model)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = args.model.replace("/", "_")
    for s in strategies:
        run_strategy(lm, items, s, args, out_dir / f"{slug}__{s}.jsonl", args.model)
    print("Terminé. Lance ensuite : python analyze.py --results", args.out)


if __name__ == "__main__":
    main()
