from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.run_agent_cycle import (
    CommandResult,
    CycleError,
    REQUIRED_CHECKS,
    _load_or_initialize_campaign_state,
    _record_campaign_stop,
    artifact_inventory,
    assess_pr,
    build_codex_command,
    build_role_prompt,
    build_parser,
    completed_experiment_ids,
    create_handoff_manifest,
    determine_receivers,
    experiment_comparison,
    fast_forward_to_origin_main,
    generate_reports,
    is_terminal_state,
    next_experiment_id,
    normalize_receivers,
    parse_pr_number,
    select_target_experiment,
    validate_campaign_authorization,
    validate_agent_result,
    watch_pr,
)


def safe_result(**overrides):
    value = {
        "status": "COMPLETED",
        "role": "B",
        "phase": "PACKAGE_AUDIT",
        "experiment_id": "exp_003",
        "summary": "approved role step completed",
        "commit_sha": "a" * 40,
        "pr_url": "https://github.com/example/repo/pull/54",
        "small_evidence_paths": ["coordination/inbox/B/result.md"],
        "large_artifact_paths": [],
        "next_receiver": "E",
        "formal_metrics_produced": False,
        "pr_25_evidence_used": False,
        "final_approval_created": False,
        "test_access": False,
    }
    value.update(overrides)
    return value


def successful_pr(files=None):
    checks = []
    for full_name in sorted(REQUIRED_CHECKS):
        workflow, name = full_name.split(" / ", 1)
        checks.append(
            {"workflowName": workflow, "name": name, "conclusion": "SUCCESS"}
        )
    return {
        "state": "OPEN",
        "mergeable": "MERGEABLE",
        "headRefOid": "a" * 40,
        "files": [{"path": path} for path in (files or ["tools/example.py"])],
        "statusCheckRollup": checks,
    }


class ReceiverTests(unittest.TestCase):
    def test_normalizes_composite_receivers(self):
        self.assertEqual(normalize_receivers("C_AND_D"), ["C", "D"])
        self.assertEqual(normalize_receivers("B/E"), ["B", "E"])
        self.assertEqual(normalize_receivers(["C", "D", "C"]), ["C", "D"])

    def test_rejects_unknown_receiver(self):
        with self.assertRaises(CycleError):
            normalize_receivers("A_AND_F")

    def test_terminal_state_selects_next_experiment_and_A(self):
        current = {"experiment_id": "exp_002", "status": "COMPLETED_REJECTED"}
        state = {"next_receiver": "E"}
        self.assertTrue(is_terminal_state(current))
        self.assertEqual(next_experiment_id("exp_002"), "exp_003")
        target = select_target_experiment(None, current, state)
        self.assertEqual(target, "exp_003")
        self.assertEqual(determine_receivers(target, current, state), ["A"])

    def test_active_experiment_cannot_be_skipped(self):
        current = {"experiment_id": "exp_003", "status": "IMPLEMENTING"}
        with self.assertRaises(CycleError):
            select_target_experiment("exp_004", current, {})


class ResultContractTests(unittest.TestCase):
    def test_accepts_safe_result(self):
        validate_agent_result(safe_result(), role="B", experiment_id="exp_003")

    def test_rejects_test_access(self):
        with self.assertRaisesRegex(CycleError, "test_access"):
            validate_agent_result(
                safe_result(test_access=True), role="B", experiment_id="exp_003"
            )

    def test_rejects_pr25_or_final_approval(self):
        for field in ("pr_25_evidence_used", "final_approval_created"):
            with self.subTest(field=field), self.assertRaises(CycleError):
                validate_agent_result(
                    safe_result(**{field: True}), role="B", experiment_id="exp_003"
                )

    def test_rejects_short_sha(self):
        with self.assertRaisesRegex(CycleError, "full lowercase SHA"):
            validate_agent_result(
                safe_result(commit_sha="abc123"), role="B", experiment_id="exp_003"
            )


class DispatchConstructionTests(unittest.TestCase):
    def test_codex_command_uses_reviewable_sandbox(self):
        command = build_codex_command(
            executable="codex",
            worktree=Path("worktree"),
            schema=Path("schema.json"),
            last_message=Path("last.json"),
        )
        self.assertIn("workspace-write", command)
        self.assertNotIn("--approve-for-me", command)
        self.assertIn("--output-schema", command)
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", command)

    def test_resume_command_contains_session(self):
        command = build_codex_command(
            executable="codex",
            worktree=Path("worktree"),
            schema=Path("schema.json"),
            last_message=Path("last.json"),
            session_id="session-123",
        )
        self.assertEqual(command[1:4], ["exec", "resume", "session-123"])

    def test_prompt_keeps_formal_run_closed_without_both_conditions(self):
        prompt = build_role_prompt(
            role="B",
            experiment_id="exp_003",
            gate_status="ALLOWED",
            allow_real_valid=False,
        )
        self.assertIn("Do not run real data training", prompt)
        prompt = build_role_prompt(
            role="B",
            experiment_id="exp_003",
            gate_status="ALLOWED",
            allow_real_valid=True,
        )
        self.assertIn("explicitly permits B", prompt)

    def test_campaign_prompt_opens_only_b_valid_gate_and_keeps_test_closed(self):
        prompt = build_role_prompt(
            role="B",
            experiment_id="exp_003",
            gate_status="ALLOWED",
            allow_real_valid=False,
            campaign_public_valid_authorized=True,
        )
        self.assertIn("bounded train-valid-only campaign", prompt)
        self.assertIn("never access, compute, print, or report test", prompt.lower())
        evaluator = build_role_prompt(
            role="E",
            experiment_id="exp_003",
            gate_status="ALLOWED",
            allow_real_valid=False,
            campaign_public_valid_authorized=True,
        )
        self.assertIn("Independently evaluate only B's immutable", evaluator)
        closed = build_role_prompt(
            role="C",
            experiment_id="exp_003",
            gate_status="ALLOWED",
            allow_real_valid=False,
            campaign_public_valid_authorized=True,
        )
        self.assertIn("Do not run real data training", closed)


class CampaignAuthorizationTests(unittest.TestCase):
    def authorization(self, **overrides):
        value = {
            "status": "ALLOWED",
            "experiment_ids": ["exp_003", "exp_004", "exp_005"],
            "max_completed_experiments": 3,
            "max_role_steps": 24,
            "data_mode": "train_valid_only",
            "automatic_public_valid": True,
            "test_access": False,
            "final_approval_allowed": False,
        }
        value.update(overrides)
        return {"bounded_campaign_authorization": value}

    def test_accepts_explicit_bounded_valid_only_campaign(self):
        authorization = validate_campaign_authorization(
            self.authorization(),
            start_experiment_id="exp_003",
            requested_iterations=3,
            requested_role_steps=20,
        )
        self.assertEqual(
            authorization.experiment_ids, ("exp_003", "exp_004", "exp_005")
        )
        self.assertTrue(authorization.automatic_public_valid)

    def test_rejects_missing_or_widened_authorization(self):
        unsafe_states = [
            {},
            self.authorization(status="BLOCKED"),
            self.authorization(data_mode="train_test"),
            self.authorization(test_access=True),
            self.authorization(final_approval_allowed=True),
            self.authorization(automatic_public_valid=False),
            self.authorization(experiment_ids=["exp_003", "exp_005"]),
        ]
        for state in unsafe_states:
            with self.subTest(state=state), self.assertRaises(CycleError):
                validate_campaign_authorization(
                    state,
                    start_experiment_id="exp_003",
                    requested_iterations=2,
                    requested_role_steps=None,
                )

    def test_rejects_requested_iterations_or_steps_above_a_limits(self):
        with self.assertRaisesRegex(CycleError, "iterations exceed"):
            validate_campaign_authorization(
                self.authorization(max_completed_experiments=2),
                start_experiment_id="exp_003",
                requested_iterations=3,
                requested_role_steps=None,
            )
        with self.assertRaisesRegex(CycleError, "role steps exceed"):
            validate_campaign_authorization(
                self.authorization(max_role_steps=4),
                start_experiment_id="exp_003",
                requested_iterations=2,
                requested_role_steps=5,
            )

    def test_parser_exposes_continuous_run_bounds(self):
        args = build_parser().parse_args(
            [
                "--experiment",
                "exp_003",
                "--action",
                "run",
                "--max-iterations",
                "3",
                "--max-role-steps",
                "20",
            ]
        )
        self.assertEqual(args.action, "run")
        self.assertEqual(args.max_iterations, 3)
        self.assertEqual(args.max_role_steps, 20)


class WorktreeRefreshTests(unittest.TestCase):
    def test_existing_role_branch_fast_forwards_for_second_a_step(self):
        commands = []

        def fake_run(argv, *, cwd, input_text=None, timeout_seconds=None):
            commands.append(tuple(argv))
            if tuple(argv) == ("git", "rev-parse", "HEAD"):
                return CommandResult(0, "a" * 40 + "\n", "")
            if tuple(argv) == ("git", "rev-parse", "origin/main"):
                return CommandResult(0, "b" * 40 + "\n", "")
            return CommandResult(0, "", "")

        with patch("tools.run_agent_cycle.run_command", side_effect=fake_run), patch(
            "tools.run_agent_cycle.require_clean_worktree",
            side_effect=["a" * 40, "b" * 40],
        ):
            refreshed = fast_forward_to_origin_main(
                Path("/tmp/a-exp003"), label="existing A role worktree"
            )
        self.assertEqual(refreshed, "b" * 40)
        self.assertIn(("git", "merge", "--ff-only", "origin/main"), commands)
        self.assertNotIn(("git", "rebase", "origin/main"), commands)

    def test_diverged_role_branch_stops_without_rebase_or_reset(self):
        commands = []

        def fake_run(argv, *, cwd, input_text=None, timeout_seconds=None):
            commands.append(tuple(argv))
            if tuple(argv) == ("git", "rev-parse", "HEAD"):
                return CommandResult(0, "a" * 40 + "\n", "")
            if tuple(argv) == ("git", "rev-parse", "origin/main"):
                return CommandResult(0, "b" * 40 + "\n", "")
            if tuple(argv[:3]) == ("git", "merge-base", "--is-ancestor"):
                return CommandResult(1, "", "")
            return CommandResult(0, "", "")

        with patch("tools.run_agent_cycle.run_command", side_effect=fake_run), patch(
            "tools.run_agent_cycle.require_clean_worktree", return_value="a" * 40
        ), self.assertRaisesRegex(CycleError, "refusing rebase or reset"):
            fast_forward_to_origin_main(
                Path("/tmp/a-exp003"), label="existing A role worktree"
            )
        self.assertFalse(any(command[:2] == ("git", "rebase") for command in commands))
        self.assertFalse(any(command[:2] == ("git", "reset") for command in commands))


class PullRequestGateTests(unittest.TestCase):
    def test_allows_clean_pr_with_all_checks(self):
        ready, reasons = assess_pr(successful_pr())
        self.assertTrue(ready)
        self.assertEqual(reasons, [])

    def test_rejects_protected_file_change(self):
        ready, reasons = assess_pr(successful_pr(["starter/data.py"]))
        self.assertFalse(ready)
        self.assertTrue(any("protected paths" in reason for reason in reasons))

    def test_rejects_release_only_change_and_unexpected_head(self):
        ready, reasons = assess_pr(
            successful_pr(["tools/final_approval.py"]), expected_head_sha="b" * 40
        )
        self.assertFalse(ready)
        self.assertTrue(any("protected paths" in reason for reason in reasons))
        self.assertTrue(any("PR head" in reason for reason in reasons))

    def test_continuous_gate_enforces_role_write_authority(self):
        ready, reasons = assess_pr(
            successful_pr(["governance/policy.json"]), expected_role="D"
        )
        self.assertFalse(ready)
        self.assertTrue(any("does not own" in reason for reason in reasons))
        ready, reasons = assess_pr(
            successful_pr(["src/models/fm.py"]), expected_role="D"
        )
        self.assertTrue(ready)
        self.assertEqual(reasons, [])

    def test_rejects_missing_check(self):
        pr = successful_pr()
        pr["statusCheckRollup"].pop()
        ready, reasons = assess_pr(pr)
        self.assertFalse(ready)
        self.assertTrue(any("MISSING" in reason for reason in reasons))

    def test_parses_pr_number(self):
        self.assertEqual(
            parse_pr_number("https://github.com/example/repo/pull/123"), 123
        )
        self.assertIsNone(parse_pr_number(None))

    def test_auto_merge_waits_for_checks_and_preserves_reusable_role_branch(self):
        opened = successful_pr()
        merged = dict(opened, state="MERGED")
        with patch(
            "tools.run_agent_cycle.load_pr", side_effect=[opened, merged]
        ), patch(
            "tools.run_agent_cycle.run_command",
            return_value=CommandResult(0, "", ""),
        ) as command:
            result = watch_pr(
                Path("/tmp/repo"),
                pr_number=54,
                timeout_seconds=0,
                poll_seconds=5,
                auto_merge=True,
                expected_head_sha="a" * 40,
                expected_role="B",
            )
        self.assertTrue(result["ready"])
        merge_command = command.call_args.args[0]
        self.assertEqual(merge_command, ("gh", "pr", "merge", "54", "--merge"))
        self.assertNotIn("--delete-branch", merge_command)


class ArtifactAndReportTests(unittest.TestCase):
    def test_artifact_manifest_hashes_bytes_without_modifying_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = root / "package"
            package.mkdir()
            artifact = package / "valid_predictions.csv"
            artifact.write_bytes(b"row_id,score\n0,0.5\n")
            before = artifact.read_bytes()
            inventory = artifact_inventory([package])
            self.assertEqual(len(inventory), 1)
            self.assertEqual(inventory[0]["relative_path"], "valid_predictions.csv")
            self.assertEqual(artifact.read_bytes(), before)

            manifest = create_handoff_manifest(
                root / "runtime",
                experiment_id="exp_003",
                recipient="E",
                artifact_paths=[package],
            )
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertTrue(payload["manual_private_transfer_required"])
            self.assertFalse(payload["git_upload_allowed"])
            self.assertFalse(payload["test_access"])

    def test_comparison_uses_decisions_only(self):
        rows = experiment_comparison(
            [
                {"record_type": "experiment_plan", "experiment_id": "exp_001"},
                {
                    "record_type": "experiment_decision",
                    "experiment_id": "exp_001",
                    "decision": "KEEP",
                    "baseline_primary": 0.60,
                    "candidate_primary": 0.61,
                    "primary_delta": 0.01,
                    "test_access": False,
                },
            ]
        )
        self.assertEqual([row["experiment_id"] for row in rows], ["exp_001"])

    def test_generates_status_comparison_and_demo_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            history = root / "coordination" / "experiment_history.jsonl"
            history.parent.mkdir(parents=True)
            history.write_text(
                json.dumps(
                    {
                        "record_type": "experiment_decision",
                        "experiment_id": "exp_002",
                        "decision": "REJECT",
                        "baseline_primary": 0.60,
                        "candidate_primary": 0.59,
                        "primary_delta": -0.01,
                        "test_access": False,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            runtime = root / "artifacts" / "agent_cycle" / "exp_003"
            report = generate_reports(
                root,
                runtime,
                target="exp_003",
                current_experiment={
                    "experiment_id": "exp_002",
                    "status": "COMPLETED_REJECTED",
                    "retained_champion_experiment_id": "exp_001",
                },
                current_state={
                    "next_receiver": "A",
                    "stage_gates": {
                        "REAL_VALID_RUN_ALLOWED": {"status": "CONSUMED_BLOCKED"}
                    },
                },
            )
            self.assertEqual(report["next_receivers"], ["A"])
            self.assertEqual(report["champion_experiment_id"], "exp_001")
            self.assertTrue((runtime / "cycle_state.json").exists())
            self.assertTrue((runtime / "status.md").exists())
            self.assertTrue((runtime / "demo_summary.json").exists())
            status = (runtime / "status.md").read_text(encoding="utf-8")
            self.assertIn("Current champion: `exp_001`", status)
            self.assertIn("Hidden test was never accessed", status)


class CampaignStateTests(unittest.TestCase):
    def test_counts_only_completed_decision_records(self):
        self.assertEqual(
            completed_experiment_ids(
                [
                    {"record_type": "experiment_plan", "experiment_id": "exp_003"},
                    {
                        "record_type": "experiment_decision",
                        "experiment_id": "exp_003",
                    },
                ]
            ),
            {"exp_003"},
        )

    def test_stop_state_is_resumable_but_never_authorizes_test(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            state = _load_or_initialize_campaign_state(
                runtime,
                start_experiment_id="exp_003",
                authorized_experiment_ids=["exp_003", "exp_004"],
                max_iterations=2,
                max_role_steps=12,
                authorization_hash="a" * 64,
                existing_decisions={"exp_001", "exp_002"},
            )
            _record_campaign_stop(
                runtime,
                state,
                reason="NO_STATE_PROGRESS",
                detail="A must advance routing state",
            )
            saved = json.loads(
                (runtime / "campaign_state.json").read_text(encoding="utf-8")
            )
            self.assertEqual(saved["status"], "STOPPED")
            self.assertFalse(saved["test_access"])
            self.assertFalse(saved["final_approval_created"])
            resumed = _load_or_initialize_campaign_state(
                runtime,
                start_experiment_id="exp_003",
                authorized_experiment_ids=["exp_003", "exp_004"],
                max_iterations=2,
                max_role_steps=12,
                authorization_hash="a" * 64,
                existing_decisions={"exp_001", "exp_002"},
            )
            self.assertEqual(resumed["stop_reason"], "NO_STATE_PROGRESS")


if __name__ == "__main__":
    unittest.main()
