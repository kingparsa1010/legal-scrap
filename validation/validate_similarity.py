import csv
import sys
from scanner.similarity import TrademarkSimilarityEngine


def main(path: str) -> int:
    with open(path, encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        print("No labeled examples. Add professionally reviewed rows first.")
        return 2
    engine = TrademarkSimilarityEngine()
    scored = [(engine.calculate_similarity(r["candidate"], r["target"]), int(r["label"])) for r in rows]
    print("threshold,precision,recall,false_positives,false_negatives")
    for threshold in range(60, 96, 5):
        tp = sum(score >= threshold and label == 1 for score, label in scored)
        fp = sum(score >= threshold and label == 0 for score, label in scored)
        fn = sum(score < threshold and label == 1 for score, label in scored)
        precision = tp / (tp + fp) if tp + fp else 0
        recall = tp / (tp + fn) if tp + fn else 0
        print(f"{threshold},{precision:.3f},{recall:.3f},{fp},{fn}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
