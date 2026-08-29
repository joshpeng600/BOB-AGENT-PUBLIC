# Repository guardrails

- Treat `starter/evaluate.py`, `starter/data.py`, `starter/submit.py`, and
  `starter/baseline_scores.json` as protected official files.
- Preserve `.gitattributes`; protected text uses canonical LF across platforms.
- Do not change the evaluation label, data split, GAUC, nDCG@5, or primary-score
  definitions.
- Model, training, and feature work belongs outside E's evaluation tooling.
- Test scoring is denied unless `tools/final_approval.py` verifies a frozen full
  commit SHA, a clean worktree, matching protected hashes, and explicit human
  approval.
- Do not weaken a prediction or audit check merely to make a test pass.
- Run `python3 -m unittest discover -s tests -v` before requesting review.
