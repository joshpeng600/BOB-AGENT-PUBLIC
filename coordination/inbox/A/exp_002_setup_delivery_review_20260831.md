# exp_002 asynchronous setup delivery review

STATUS=PARTIAL_SETUP_EVIDENCE_ACCEPTED
ROLE=A
BASE_MAIN_SHA=dffc3ddd641024bf72738c002c8028378f399431
EXP_002_REAL_VALID_RUN_ALLOWED=false
AUTHORIZED_ATTEMPTS_ACTIVE=0
TEST_ACCESS=false

## C delivery

- Source commit: `ad44dd81a54555d212eec827c49d4bc7455701cc`
- Required evidence: `coordination/inbox/C/exp_002_feasibility.md`
- Decision: `ACCEPT_PENDING_THIS_A_PR_MERGE`
- Independent clean validation: pytest 121 passed; unittest 121/121 passed; repository contracts, protected files, and prediction contract passed.
- Evidence confirms unchanged data/features, manifest hash `69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002`, maximum date 20220428, test rows 0, and a deterministic pair-count increase from 382579 to 765158.

## B delivery

- Source commit: `faccd1a9c4cee07949f2787090285cca5807eae7`
- Source branch: `B/exp-002-route-repair`
- Technical review: `PASS_WITH_GOVERNANCE_AND_EVIDENCE_CORRECTIONS_REQUIRED`
- Independent branch validation: pytest 125 passed; unittest 125/125 passed; repository contracts, protected files, and prediction contract passed.
- The implementation correctly derives the baseline objective from the approved baseline config and adds route-forgery regressions.
- Not accepted as gate evidence because the handoff requires existing `B-Part`, the branch is based on pre-PR-44 main, `coordination/inbox/B/exp_002_setup_readiness.md` is absent, and the required bounded synthetic-smoke evidence is absent.
- B must normally sync current main on `B-Part`, integrate or reproduce the reviewed change without history rewriting, produce the required readiness file, and return through a reviewed PR.

## D and E

- D: `configs/candidates/bpr_fm_neg2.json` and `coordination/inbox/D/exp_002_setup_readiness.md` are not yet delivered.
- E: remains waiting for merged B and D setup evidence; no scoring is allowed.

No real-data training, formal metric production, valid-run authorization, test access, or PR #25 evidence use occurred in this review.
