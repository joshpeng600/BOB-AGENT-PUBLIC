你是 Track 2 团队的 A 智能体，负责规划、合同、治理、审批、协调与集成。本轮只修正 `exp_001` 的治理合同、协调状态和 B 交接规范；不实现 B runner，不修改 D 模型/训练科学逻辑，不重新做已完成的 bootstrap，不制造实验结果，不访问 test。

## 人工用户的明确指令

1. B 必须继续使用现有远端分支 `B-Part`，不得创建 `B-exp001-harness` 或其他新 B 分支。
2. A 创建 PR 后不得自行合并，由人工用户审核并合并。
3. 不得修改 `starter/` 下任何文件及官方评价定义。
4. 不得 force-push、rebase 共享分支或重写历史。
5. 不得删除、移动或自动提交用户现有的未跟踪文件，尤其是 `reports/bootstrap/Track2_B_exp001_execution_prompt.docx`；除非人工用户明确授权，否则把它排除在本 PR 之外。

## 已确认的当前进度

以下内容已完成，不得重复搭建：

- PR #3 已合并，最近确认的 `origin/main` 为 `ab0da74d91cb71606ae99f3b4d7874be28839e1c`；执行时必须重新 `git fetch origin` 并以实时完整 SHA 为准。
- canonical Starter 七文件已恢复，protected hashes 已固定并通过。
- 当前完整测试最近一次结果为 pytest 57 passed、unittest 57 passed；repository contracts、protected files、prediction contract 均通过。
- B bootstrap harness、D 的 `FactorizationMachine`/BPR/checkpoint、E 的 safe evaluation/final gate 已进入 main。
- C 的干净数据合同、审计结果、泄漏检查和 dev-dataset 工具已经在 main；不要求 C 重做完整 bootstrap。
- baseline 已有一次实际 valid 复现记录 `0.6015`，官方参考为 `0.6016`。本轮不重新运行 baseline。
- `exp_001` 已确定为 loss-only：pointwise BCE → same-user BPR；不新增特征、不换模型、不改官方 evaluator。

当前真实未完成项：

- `coordination/current_state.json` 仍引用旧 base SHA `195b2b719999d4160a7d1b178f67477e0150d1cf`，并保留已过时的 post-merge 动作。
- `tools/run_experiment.py` 仍产生旧字段 `exp_id/commit/dirty`；此项归 B，不由 A 修改。
- `tools/validate_contract.py` 仍验证旧合同；此项归 B，不由 A 修改。
- runner 尚未完整接入 D 的 canonical FM/BPR 接口；此项归 B。
- `contracts/run_manifest.template.json` 仍把 `executor_role` 写成 E。
- GitHub branch protection/required checks 是否真正成为门禁必须实时确认，不能仅凭 Actions 曾成功推断。
- 远端 `C-Part` 含被 Git 跟踪的 KuaiRand 数据和 `__pycache__`，约 203.5 MB；该分支不得合并。本轮只报告并请求人工处理，不自动删除远端分支或重写历史。

## 开始前

完整阅读：

- `AGENTS.md`
- `governance/`
- `contracts/`
- `coordination/current_state.json`
- `coordination/inbox/B/exp_001_handoff.json`
- `coordination/inbox/C/exp_001_handoff.json`
- `coordination/inbox/D/exp_001_handoff.json`
- `coordination/inbox/E/exp_001_handoff.json`
- `experiments/exp_001.json`
- `configs/approved/baseline_fm.json`
- `configs/candidates/bpr_fm.json`
- `docs/EVALUATION_CONTRACT.md`

然后执行只读核对：

```bash
git status --short --branch
git fetch origin
git rev-parse origin/main
git log -1 --oneline origin/main
git diff --stat origin/main...A-part
```

若位于现有 `A-part`，使用 merge 同步，不 rebase：

```bash
git switch A-part
git merge origin/main
```

保留所有用户未跟踪文件，提交时只显式 `git add` 本 Prompt 允许的文件。

## 本轮允许修改的范围

A 可修改：

- `AGENTS.md` 中与 SHA 语义、B/E 分工和阶段门槛直接相关的规则
- `governance/contract_fields.json`
- `governance/policy.json`
- `governance/runner_model_interface.json`
- `governance/manual_interventions.jsonl`（仅记录本次经人工明确授权的跨所有权治理调整）
- `contracts/*.template.json`
- `coordination/current_state.json`
- `coordination/inbox/A-E/exp_001_handoff.json`
- `experiments/exp_001.json`
- approved-config 中的治理元数据，不改变科学超参数
- `docs/EVALUATION_CONTRACT.md` 和 `.github/BRANCH_PROTECTION.md` 的合同说明
- 为使治理 CI 与新 schema 一致所必需的 `scripts/check_repository_contracts.py` 及其治理测试；若触及 B 所有权，必须在 manual intervention 中精确记录范围和原因

A 禁止修改：

- `starter/`
- `tools/run_experiment.py`
- `tools/validate_contract.py`
- `src/models/`
- `src/training/`
- C 的数据/特征实现
- E 的评分实现
- 任何真实数据、预测、checkpoint 或 artifacts

## 一、修正 Git SHA 语义，消除自引用

禁止要求“被提交文件内部的 SHA 等于包含该文件的当前 HEAD”，因为文件修改会产生新提交，无法自洽。

建立按合同类型区分的语义：

1. `approved_against_commit_sha`
   - 用于 experiment spec、approved config、current state 和 A→角色 handoff。
   - 表示 A 审批所依据的完整代码基线。
   - 必须是完整小写 40 位真实 SHA。
   - 必须是后续实现/运行提交的祖先，但不要求等于运行时 HEAD。

2. `implementation_commit_sha`
   - 用于 C/D proposal 在确有代码实现时指向被提议或被审核的实现提交。
   - 必须是完整小写 40 位真实 SHA。
   - 不得被当作最终运行产物 SHA。

3. `commit_sha`
   - 只用于 run manifest、预测/checkpoint provenance、metrics/evaluation evidence、final approval 等运行或评价证据。
   - 必须等于实际生产该证据时的 clean HEAD。

4. `baseline_experiment_id`
   - 只表示基线实验编号，不承载 Git SHA。

在 `governance/contract_fields.json` 中建立明确的 contract-type → SHA-field 映射。更新 `AGENTS.md`、相关模板、current state、experiment spec、approved baseline config 和 handoff。禁止 `exp_id/base_commit/commit/frozen_commit` 旧别名。

A 本轮只更新治理 schema 和静态 repository contract enforcement；`tools/validate_contract.py` 与 runner 的运行时实现要求写入 B handoff，由 B 完成。

## 二、明确 `exp_001` 的唯一标识来源

批准以下正式接口：

```text
python tools/run_experiment.py \
  --experiment-spec experiments/exp_001.json \
  --config configs/candidates/bpr_fm.json \
  ...
```

要求：

- B runner 必须接收 `--experiment-spec`。
- `experiment_id` 只能从状态为 `APPROVED_FOR_IMPLEMENTATION` 的 experiment spec 获取。
- 禁止从配置文件名、输出目录、分支名或缩写 SHA 推断 `experiment_id`。
- runner 必须验证 spec 的 `implementation_config` 与传入 config 路径一致。
- candidate config 只承载科学配置，不需要重复充当实验标识来源。

experiment spec 必须明确绑定：

- `experiment_id=exp_001`
- `approved_against_commit_sha=<实时 origin/main 完整 SHA>`
- approved baseline config
- candidate config
- `change_type=loss_only`
- `objective=same_user_bpr`
- allowed splits 为 train/valid
- maximum development date 为 `20220428`
- test access 为 false

更新 `governance/runner_model_interface.json`、`experiments/exp_001.json`、B handoff 和示例命令。A 只批准接口，不修改 runner 实现。

## 三、明确 B/E 角色证据

- B 负责训练和 valid-only runner 执行，因此 `run_manifest.executor_role` 必须固定为 `B`。
- E 负责 immutable predictions 的独立评价，因此 metrics/evaluation evidence 必须包含 `evaluator_role=E`。
- E 不负责修复 runner、训练、配置或候选输出。
- B 不能批准自己的科学结果；E 不能修改 B 的预测。

修正模板和合同说明中的冲突，但不改 E 的评分算法。

## 四、拆分三个门槛

不要用同一个“开工门槛”同时阻止代码实现和真实运行。

### 1. `IMPLEMENTATION_ALLOWED`

- A 的治理基线已在 main。
- protected hashes 正常。
- B 在现有 `B-Part` 同步 `origin/main`。
- 不加载真实数据，不访问 test。
- 即使真实数据尚未送达，也允许 B 修改 runner、validator 和测试。

### 2. `SYNTHETIC_SMOKE_ALLOWED`

- B 的实现代码已提交。
- 工作树 clean。
- canonical contracts、protected files 和 unit tests 通过。
- 只使用明确标记的 synthetic dev fixture。
- smoke 只证明接口可运行，不构成指标结论。

### 3. `REAL_VALID_RUN_ALLOWED`

- 本轮 A 治理 PR 已由人工合并。
- C 确认现有 dev 数据最大日期不超过 `20220428`，并补充 exp_001 所需的同用户正负 pair 可行性/覆盖率确认；不要求重做完整数据审计。
- B 的运行提交 frozen、完整 SHA、clean。
- baseline 与 exp_001 使用同一 B commit、同一 data hash、同一 features、同一 seed/预算，唯一研究变量为 objective。
- required checks 已强制执行；若因账户/仓库限制无法启用，必须有人工批准的替代治理记录。
- 仍然禁止任何 test 访问。

## 五、修正改进阈值

正式判断固定为：

```text
candidate_primary - baseline_primary > 0.002
```

若 baseline primary 为 `0.6016`，candidate primary 必须严格大于 `0.6036`。等于 `0.6036` 不算实际改进。

## 六、收紧自动重试

- runner 不得自动安装依赖或修改环境。
- 缺依赖必须生成失败 manifest 并停止，不属于可重试错误。
- 最多一次重试，只允许 governance policy 明确 allowlist 的暂时性基础设施故障。
- 重试必须使用完全相同的 commit、experiment spec、config hash、data hash、seed 和命令。
- policy violation、test access、泄漏、dirty worktree、protected hash mismatch、NaN/Inf、指标退化和科学失败绝不重试。

同步更新 `governance/policy.json`，移除把 dependency installation 当作自动修复的表述。

## 七、分支与 PR

- A 使用现有 `A-part` 完成本轮治理修正并创建 PR。
- A 不自行合并；最终 `MERGED=false`，交给人工用户。
- B handoff 必须写明继续使用现有 `B-Part`：

```bash
git fetch origin
git switch B-Part
git merge origin/main
```

- 禁止创建 `B-exp001-harness`。
- 禁止 force-push、共享分支 rebase 或历史重写。
- 提交时只显式 stage 本轮治理文件，不得使用可能带入未跟踪产物的宽泛 `git add .`。

## 八、GitHub 分支保护

核对 `main` 是否真正受保护，并确认以下四项是 required checks，而不仅是曾经运行成功：

- `protected-files / verify-protected-files`
- `unit-tests / tests`
- `prediction-contract / prediction-contract`
- `repository-contracts / contracts`

同时确认：

- require pull request before merging
- require branches up to date
- block force push
- block deletion
- no administrator bypass（若套餐支持）

若当前账户套餐或私有仓库限制导致无法启用：

- 不得擅自把仓库改为 public。
- 不得谎报已启用。
- 输出 `HUMAN_DECISION_REQUIRED`。
- 给出选择：升级/调整仓库权限，或由人工批准临时替代门禁并记录 manual intervention。

## 九、按当前实际进度更新 C/D/E/B 状态

- C：`PAIR_FEASIBILITY_CONFIRMATION_REQUESTED`。现有完整数据审计已完成；只补充 dev 数据可用性、最大日期、data hash、同用户正负 pair 可行性和覆盖率，不重做 bootstrap，不加新特征。
- D：`INTERFACE_CONFIRMATION_REQUESTED`。现有 FM/BPR/checkpoint 实现已存在；只确认 `FactorizationMachine` 构造参数、pointwise/BPR API、checkpoint state 和 pair/user coverage 输出。除非发现合同缺口，不重新实现模型，不修改评价。
- E：`WAIT_FOR_IMMUTABLE_B_OUTPUT`。当前不得开始正式评分，只能预审 manifest/evidence schema。
- B：`ACTION_REQUIRED_AFTER_A_PR_MERGE`。A PR 被人工合并后，在现有 `B-Part` 实现 runner/validator/tests。

`coordination/current_state.json` 应反映阶段门槛，而不是笼统写成所有角色 blocked。其 approved base 使用实时 `origin/main` 完整 SHA；移除已经完成的旧 post-merge 动作。

## 十、隔离远端 `C-Part` 风险

已知远端 `C-Part` 跟踪了不应进入 Git 的 KuaiRand 文件和 `__pycache__`。本轮 A 智能体：

- 不合并 `C-Part`。
- 不从该分支复制原始数据。
- 不自动删除远端分支。
- 不执行历史重写。
- 在最终回报中输出 `HUMAN_DECISION_REQUIRED` 子项，建议人工关闭相关 PR并确认后删除远端分支。
- 说明 C 的干净实现已经在 main，不需要通过合并污染分支来恢复代码。

## 十一、重新生成 B handoff

更新 `coordination/inbox/B/exp_001_handoff.json`，必须包含：

- `approved_against_commit_sha=<实时 main SHA>`
- `experiment_id=exp_001`
- `status=ACTION_REQUIRED_AFTER_A_PR_MERGE`
- 继续使用现有 `B-Part`
- `--experiment-spec experiments/exp_001.json`
- canonical D 字段：`embedding_dim/learning_rate/l2/batch_size/epochs/patience/max_batches`
- `factorization_machine` 不要求 `model.factory`
- objective 路由 pointwise BCE / same-user BPR
- run manifest 产生 `experiment_id`、`commit_sha`、`worktree_clean`、`run_id`、`commands`、`executor_role=B`、protected hashes、data/config/prediction/checkpoint hashes
- baseline 与 BPR 在同一 clean B commit、同一 data hash、同一 seed/预算下运行
- smoke 不构成指标结论
- 最多一次 allowlisted infrastructure retry
- 不得自动安装依赖
- 不得访问 test
- 只有产生 immutable valid predictions 后 `NEXT_RECEIVER=E`；否则 `NEXT_RECEIVER=A` 或对应 blocker owner

B 实现范围明确写为：

- `tools/run_experiment.py`
- `tools/validate_contract.py`
- 相关 B-owned tests

A 本轮不得替 B 修改这些文件。

## 十二、验证与提交

运行：

```bash
python -m pytest -q
python -m unittest discover -s tests -v
python scripts/check_repository_contracts.py
python scripts/check_protected_files.py
python scripts/check_prediction_contract.py
git diff --check
git status --short
```

不得运行真实 baseline、BPR、test scoring 或任何读取 test 标签的命令。

确认：

- `starter/` 无任何 diff。
- 用户未跟踪的 Word 文件未被 stage、修改或删除。
- 正式合同不再混用旧别名。
- A 修改仅限治理、模板、协调和必要的静态 CI enforcement。

使用 scoped commit，例如：

```text
chore(governance): finalize exp_001 contracts and B handoff
```

推送现有 `A-part` 并创建 PR，但不得合并。

## 最终回报格式

```text
STATUS=PASS | PARTIAL | HUMAN_DECISION_REQUIRED
BRANCH=A-part
COMMIT_SHA=<A PR head full SHA>
FILES_CHANGED=<list>
CONTRACT_DECISIONS=<SHA semantics / experiment_id source / role ownership / stage gates>
MAIN_SHA_VERIFIED=<full origin/main SHA>
BRANCH_PROTECTION=ENABLED | DISABLED | UNKNOWN
REQUIRED_CHECKS=<exact names and status>
B_HANDOFF_PATH=coordination/inbox/B/exp_001_handoff.json
B_BRANCH=B-Part
C_HANDOFF=PAIR_FEASIBILITY_CONFIRMATION_REQUESTED
D_HANDOFF=INTERFACE_CONFIRMATION_REQUESTED
E_HANDOFF=WAIT_FOR_IMMUTABLE_B_OUTPUT
PROTECTED_HASHES=UNCHANGED
TESTS=<commands and exact results>
TEST_ACCESS=false
UNTRACKED_USER_FILES_PRESERVED=true
C_PART_RISK=HUMAN_DECISION_REQUIRED
PR_URL=<url or NOT_CREATED>
MERGED=false
BLOCKERS=<exact blockers>
NEXT_RECEIVER=HUMAN_FOR_MERGE | B | HUMAN_DECISION_REQUIRED
```
