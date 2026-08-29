# C data contract

## Verified facts

- The official baseline raw row is `(date, user_id, video_id, author_id, tab, duration_ms, long_view)` at positions `0..6`; types are `int, str, str, str, str, float, int`.
- Source order is log `4_08_to_4_21` followed by log `4_22_to_5_08`; rows are never sorted or deduplicated.
- Development ends on `20220428`: train `20220408–20220421`, validation `20220422–20220428`.
- The official evaluator uses `long_view`, GAUC, and nDCG@5. C must not use test metrics to choose experiments.
- `ablation_features.py` actually builds 5, 8, and 13 fields although one comment says “13 fields”; its `item` mode adds 3 item fields to the five baseline fields, not four.
- The provided baseline README says broad static features have no stable gain. A pure user-side first-order feature is constant within a user and cannot change within-user ranking.

## Contract

- `src.data.contracts.RawInteraction` is the named version of the official seven-position tuple and preserves numeric indexes.
- `load_dev_splits()` returns only train and validation by default. There is no development API that returns a test score.
- Source CSV files remain immutable. `tools/audit_data.py` only reads them.
- `data_manifest.json` records SHA-256, header, count, date range, labels, missing rate, and duplicate candidates. No undeclared candidate is silently called a primary key.

## Feature governance

Every feature must be registered with source columns, fit split, time availability, dtype, dimension, and missing strategy.

- Vocabularies, duration buckets, normalizers, and aggregate statistics fit **train only**.
- A history feature may use events strictly before the current impression only.
- `20220428` is the maximum permitted development date.
- Prioritize user×item/author crosses, time-safe user history, and user grouping needed by pairwise/listwise training. Do not spend iterations on broad static features alone.

## Unverified hypotheses

- Whether strict time-safe history improves validation.
- Whether item/author crosses improve validation.
- Whether pairwise/listwise training improves over the official FM.

These are hypotheses for A/D to test on train/validation only, not facts or C-selected final experiments.

## Interfaces for B and D

- B calls `tools/audit_data.py --data-dir <path>` before an autonomous run and stores `results/data_audit/` with its run log.
- D receives `dict[str, list[RawInteraction]]` from `load_dev_splits(data_dir)` and must preserve list order until prediction rows have been aligned.
- Any new feature requires a `FeatureSpec` entry and `validate_registry()` before it is used.
