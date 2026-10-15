# Similarity validation

`labeled_examples.csv` is intentionally only a template. Do not treat generated
or guessed examples as legal ground truth. Add examples reviewed by a trademark
professional, then run:

```bash
python validation/validate_similarity.py validation/labeled_examples.csv
```

Use `label=1` for a confusingly similar pair and `label=0` for a non-match.
The command reports precision/recall for candidate thresholds; it does not alter
production settings automatically.
