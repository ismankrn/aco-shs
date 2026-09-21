"""Run one (dataset, method, target-ratio) configuration over multiple seeds.

Each seed does: stratified 70/30 split -> apply sampling to the TRAIN split
only -> fit Gradient Boosting -> evaluate on the untouched test split ->
append one row to results/runs.csv.

Examples:
    python scripts/run_experiment.py --dataset nr --method baseline --seeds 0 1 2 3 4
    python scripts/run_experiment.py --dataset nr --method shs-aco-smote \
        --target-ratio 1.25 --fitness f1 --seeds 0 1 2 3 4
    # reproduce thesis behavior on NR (absolute target, legacy ACO rules):
    python scripts/run_experiment.py --dataset nr --method shs-aco-smote \
        --target-count 1500 --legacy --no-stratified --seeds 42
"""

import argparse
import sys
import time
from pathlib import Path

import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shs import (ACOUndersampler, combined_hybrid, evaluate, load_dataset,
                 oversample, ratio_to_target, shs_rus, synthetic_pool)

OVERSAMPLERS = ("ros", "smote", "adasyn")
METHODS = (["baseline", "smote-enn", "smote-tomek"]
           + list(OVERSAMPLERS)
           + [f"shs-rus-{o}" for o in OVERSAMPLERS]
           + [f"shs-aco-{o}" for o in OVERSAMPLERS])


def apply_method(method, X_tr, y_tr, n_target, seed, args):
    model = GradientBoostingClassifier(random_state=seed)
    if method == "baseline":
        return X_tr, y_tr
    if method in OVERSAMPLERS:
        # classic oversampling: minority up to the majority count
        n_majority = int((y_tr != 1).sum())
        return oversample(X_tr, y_tr, method, n_majority, random_state=seed)
    if method in ("smote-enn", "smote-tomek"):
        return combined_hybrid(X_tr, y_tr, method, random_state=seed)
    if method.startswith("shs-rus-"):
        return shs_rus(X_tr, y_tr, method.removeprefix("shs-rus-"), n_target,
                       random_state=seed)
    if method.startswith("shs-aco-"):
        pool_X, pool_y = synthetic_pool(X_tr, y_tr, method.removeprefix("shs-aco-"),
                                        n_target, random_state=seed)
        aco = ACOUndersampler(
            init_pheromone=args.init_pheromone, rho=args.rho,
            n_ants=args.ants, max_iter=args.iters, max_idle=args.max_idle,
            cv=args.cv, fitness=args.fitness,
            stratified=args.stratified, replacement=not args.no_replacement,
            legacy_pheromone=args.legacy, random_state=seed, verbose=args.verbose)
        return aco.fit_resample(X_tr, y_tr, pool_X, pool_y, model)
    raise ValueError(method)


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dataset", required=True)
    p.add_argument("--method", required=True, choices=METHODS)
    p.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2, 3, 4])
    tgt = p.add_mutually_exclusive_group()
    tgt.add_argument("--target-ratio", type=float, default=1.25,
                     help="minority target as ratio of majority count (SHS only)")
    tgt.add_argument("--target-count", type=int,
                     help="absolute minority target (thesis-style, SHS only)")
    p.add_argument("--fitness", default="f1", choices=["f1", "gmean", "bas"])
    p.add_argument("--init-pheromone", type=float, default=0.3)
    p.add_argument("--rho", type=float, default=0.8)
    p.add_argument("--ants", type=int, default=20)
    p.add_argument("--iters", type=int, default=10)
    p.add_argument("--max-idle", type=int, default=5)
    p.add_argument("--cv", type=int, default=5)
    p.add_argument("--legacy", action="store_true",
                   help="reproduce the thesis pheromone-update rule")
    p.add_argument("--no-stratified", dest="stratified", action="store_false",
                   help="plain KFold fitness CV (thesis behavior)")
    p.add_argument("--no-replacement", action="store_true",
                   help="ant selection without replacement")
    p.add_argument("--data-dir", default="data/raw")
    p.add_argument("--out", default="results/runs.csv")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    X, y = load_dataset(args.dataset, args.data_dir)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for seed in args.seeds:
        X_tr, X_te, y_tr, y_te = train_test_split(
            X, y, test_size=0.30, stratify=y, random_state=seed)
        n_target = (args.target_count if args.target_count
                    else ratio_to_target(y_tr, args.target_ratio))
        t0 = time.time()
        X_bal, y_bal = apply_method(args.method, X_tr, y_tr, n_target, seed, args)
        model = GradientBoostingClassifier(random_state=seed)
        model.fit(X_bal, y_bal)
        runtime = time.time() - t0

        m = evaluate(y_te, model.predict(X_te), model.predict_proba(X_te)[:, 1])
        row = {"dataset": args.dataset, "method": args.method, "seed": seed,
               "target": n_target if args.method.startswith("shs") else "",
               "fitness_fn": args.fitness if args.method.startswith("shs-aco") else "",
               "legacy": args.legacy, "stratified": args.stratified,
               "runtime_s": round(runtime, 2), **m}
        rows.append(row)
        print(f"[{args.dataset}/{args.method}] seed={seed} "
              f"F1={m['f1']:.4f} G-Mean={m['gmean']:.4f} BAS={m['bas']:.4f} "
              f"AUPRC={m['auprc']:.4f} ({runtime:.1f}s)")

    df = pd.DataFrame(rows)
    header = not out_path.exists()
    df.to_csv(out_path, mode="a", header=header, index=False)
    print(f"Appended {len(df)} rows to {out_path}")


if __name__ == "__main__":
    main()
