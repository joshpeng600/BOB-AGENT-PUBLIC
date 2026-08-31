from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tools.run_agent_cycle import (
    CommandResult,
    CycleError,
    PrivateRuntimeConfig,
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
    git_common_dir,
    is_terminal_state,
    load_private_runtime_config,
    next_campaign_receivers,
    next_experiment_id,
    normalize_receivers,
    parse_pr_number,
    role_command_environment,
    run_campaign,
    select_target_experiment,
    snapshot_artifacts_to_store,
    validate_campaign_authorization,
    validate_campaign_data_dir,
    validate_agent_result,
    validate_runtime_environment,
    verify_handoff_manifest,
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


class PrivateRuntimeConfigTests(unittest.TestCase):
    def write_config(self, root: Path, repo: Path, **overrides) -> Path:
        private = root / "private"
        data = private / "data" / "dev"
        artifacts = private / "artifacts"
        data.mkdir(parents=True)
        value = {
            "dev_data_dir": str(data),
            "artifact_root": str(artifacts),
        }
        value.update(overrides)
        path = private / "bob-agent.local.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_loads_absolute_private_paths_and_creates_artifact_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            path = self.write_config(root, repo)
            config = load_private_runtime_config(repo, path)
            self.assertTrue(config.dev_data_dir.is_dir())
            self.assertTrue(config.artifact_root.is_dir())
            self.assertEqual(len(config.fingerprint), 64)
            self.assertFalse(str(config.config_path).startswith(str(repo)))

    def test_rejects_config_or_private_paths_inside_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            data = repo / "data" / "dev"
            data.mkdir(parents=True)
            outside_artifacts = root / "artifacts"
            config_inside = repo / "local.json"
            config_inside.write_text(
                json.dumps(
                    {
                        "dev_data_dir": str(data),
                        "artifact_root": str(outside_artifacts),
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(CycleError, "outside the Git checkout"):
                load_private_runtime_config(repo, config_inside)

            private = root / "private"
            private.mkdir()
            outside_config = private / "local.json"
            outside_config.write_text(
                json.dumps(
                    {
                        "dev_data_dir": str(data),
                        "artifact_root": str(outside_artifacts),
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(CycleError, "dev_data_dir"):
                load_private_runtime_config(repo, outside_config)

    def test_rejects_unknown_fields_and_overlapping_private_trees(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            private = root / "private"
            data = private / "data"
            data.mkdir(parents=True)
            path = private / "local.json"
            path.write_text(
                json.dumps(
                    {
                        "dev_data_dir": str(data),
                        "artifact_root": str(data / "artifacts"),
                        "token": "must-not-be-accepted",
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(CycleError, "unexpected token"):
                load_private_runtime_config(repo, path)
            path.write_text(
                json.dumps(
                    {
                        "dev_data_dir": str(data),
                        "artifact_root": str(data / "artifacts"),
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(CycleError, "separate private trees"):
                load_private_runtime_config(repo, path)

    def test_snapshots_artifacts_into_content_addressed_private_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "role-output"
            source.mkdir()
            prediction = source / "valid_predictions.csv"
            prediction.write_bytes(b"row_id,score\n0,0.5\n")
            store = root / "private-store"
            stored = snapshot_artifacts_to_store(
                store,
                experiment_id="exp_003",
                artifact_paths=[source],
            )
            self.assertEqual(len(stored), 1)
            stored_prediction = stored[0] / "root_000" / prediction.name
            self.assertEqual(stored_prediction.read_bytes(), prediction.read_bytes())
            prediction.write_bytes(b"source changed after snapshot\n")
            manifest = create_handoff_manifest(
                root / "runtime",
                experiment_id="exp_003",
                recipient="E",
                artifact_paths=stored,
                local_read_only_access=True,
                artifact_store_root=store,
            )
            verify_handoff_manifest(
                manifest,
                expected_recipient="E",
                expected_artifact_root=store,
            )
            stored_prediction.chmod(0o644)
            stored_prediction.write_bytes(b"tampered store\n")
            with self.assertRaisesRegex(CycleError, "changed"):
                verify_handoff_manifest(
                    manifest,
                    expected_recipient="E",
                    expected_artifact_root=store,
                )

    def test_environment_preflight_requires_gh_auth_and_train_valid_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            data = root / "data"
            store = root / "store"
            repo.mkdir()
            data.mkdir()
            store.mkdir()
            config = PrivateRuntimeConfig(
                config_path=root / "local.json",
                dev_data_dir=data,
                artifact_root=store,
                fingerprint="f" * 64,
            )
            with (
                patch("tools.run_agent_cycle.require_clean_worktree"),
                patch("tools.run_agent_cycle.find_codex_executable"),
                patch("tools.run_agent_cycle.shutil.which", return_value=None),
                patch(
                    "tools.run_agent_cycle.Path.home", return_value=root / "no-home"
                ),
                patch(
                    "tools.run_agent_cycle.run_command",
                    return_value=CommandResult(
                        0,
                        "https://github.com/joshpeng600/BOB-AGENT-PUBLIC.git\n",
                        "",
                    ),
                ),
            ):
                with self.assertRaisesRegex(CycleError, "GitHub CLI is missing"):
                    validate_runtime_environment(repo, config)

            commands = []

            def fake_run(argv, *, cwd, input_text=None, timeout_seconds=None):
                commands.append(tuple(argv))
                if tuple(argv) == ("git", "remote", "get-url", "origin"):
                    return CommandResult(
                        0,
                        "git@github.com:joshpeng600/BOB-AGENT-PUBLIC.git\n",
                        "",
                    )
                return CommandResult(0, "PREFLIGHT=PASS\n", "")

            with (
                patch("tools.run_agent_cycle.require_clean_worktree"),
                patch("tools.run_agent_cycle.find_codex_executable"),
                patch("tools.run_agent_cycle.shutil.which", return_value="/usr/bin/gh"),
                patch("tools.run_agent_cycle.run_command", side_effect=fake_run),
            ):
                validate_runtime_environment(repo, config)
            self.assertIn(("/usr/bin/gh", "auth", "status"), commands)
            self.assertTrue(
                any(command[:2] == (sys.executable, "tools/preflight.py") for command in commands)
            )

    def test_campaign_resume_rejects_changed_private_runtime_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            common = {
                "start_experiment_id": "exp_003",
                "authorized_experiment_ids": ["exp_003"],
                "max_iterations": 1,
                "max_role_steps": 10,
                "authorization_hash": "a" * 64,
                "existing_decisions": {"exp_001", "exp_002"},
            }
            _load_or_initialize_campaign_state(
                runtime,
                runtime_config_hash="f" * 64,
                **common,
            )
            with self.assertRaisesRegex(CycleError, "runtime_config_hash"):
                _load_or_initialize_campaign_state(
                    runtime,
                    runtime_config_hash="e" * 64,
                    **common,
                )


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

    def test_rejects_duplicate_evidence_paths(self):
        duplicate = ["coordination/inbox/B/result.md"] * 2
        with self.assertRaisesRegex(CycleError, "duplicate paths"):
            validate_agent_result(
                safe_result(small_evidence_paths=duplicate),
                role="B",
                experiment_id="exp_003",
            )


class DispatchConstructionTests(unittest.TestCase):
    def test_output_schema_declares_every_property_type(self):
        schema_path = (
            Path(__file__).resolve().parents[1]
            / "contracts"
            / "agent_cycle_result.schema.json"
        )
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        for name, definition in schema["properties"].items():
            with self.subTest(property=name):
                self.assertIn("type", definition)

    def test_codex_command_uses_reviewable_sandbox(self):
        command = build_codex_command(
            executable="codex",
            worktree=Path("worktree"),
            schema=Path("schema.json"),
            last_message=Path("last.json"),
            git_metadata_dir=Path("/repo/.git"),
        )
        self.assertIn("workspace-write", command)
        self.assertNotIn("--approve-for-me", command)
        self.assertIn("--output-schema", command)
        self.assertIn("shell_environment_policy.inherit=all", command)
        self.assertIn("sandbox_workspace_write.network_access=true", command)
        self.assertEqual(
            command[command.index("--add-dir") + 1], str(Path("/repo/.git"))
        )
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", command)

    def test_role_environment_preserves_exact_python_runtime(self):
        environment = role_command_environment()
        expected = str(Path(sys.executable).absolute())
        self.assertEqual(environment["BOB_AGENT_PYTHON"], expected)
        self.assertEqual(environment["PATH"].split(os.pathsep)[0], str(Path(expected).parent))

    def test_prompt_requires_preflighted_python_runtime(self):
        prompt = build_role_prompt(
            role="C",
            experiment_id="exp_003",
            gate_status="BLOCKED",
            allow_real_valid=False,
            python_executable="/private/runtime/bin/python",
        )
        self.assertIn("Use /private/runtime/bin/python for every Python command", prompt)

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

    def test_campaign_prompt_accepts_exact_one_pair_gate_status(self):
        for gate_status in (
            "ALLOWED_EXACTLY_ONE_VALID_ONLY_PAIR",
            "ALLOWED_EXACTLY_ONE_FULL_BUDGET_VALID_ONLY_PAIR",
        ):
            with self.subTest(gate_status=gate_status):
                prompt = build_role_prompt(
                    role="B",
                    experiment_id="exp_003",
                    gate_status=gate_status,
                    allow_real_valid=False,
                    campaign_public_valid_authorized=True,
                )
                self.assertIn("bounded train-valid-only campaign", prompt)

    def test_campaign_prompt_rejects_unrecognized_allowed_prefix(self):
        prompt = build_role_prompt(
            role="B",
            experiment_id="exp_003",
            gate_status="ALLOWED_UNBOUNDED",
            allow_real_valid=False,
            campaign_public_valid_authorized=True,
        )
        self.assertIn("Do not run real data training", prompt)

    def test_campaign_prompt_gives_a_bounded_authority_and_frozen_data(self):
        prompt = build_role_prompt(
            role="A",
            experiment_id="exp_003",
            gate_status="BLOCKED",
            allow_real_valid=False,
            bounded_campaign_authorized=True,
            data_context=(
                "development_data_dir=C:/private/data/dev\n"
                "dataset_manifest_sha256=" + "d" * 64
            ),
        )
        self.assertIn("Do not request repeated per-experiment operator approval", prompt)
        self.assertIn("development_data_dir=C:/private/data/dev", prompt)
        self.assertIn("never copy into Git", prompt)


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

    def test_campaign_data_is_hash_bound_and_test_free(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            source = data_dir / "train.csv"
            source.write_bytes(b"date,user_id,video_id,long_view\n")
            source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
            manifest = {
                "max_date": 20220428,
                "test_rows": 0,
                "files": {"train.csv": {"sha256": source_hash}},
            }
            manifest_path = data_dir / "dataset_manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            resolved, digest = validate_campaign_data_dir(data_dir)
            self.assertEqual(resolved, data_dir.resolve())
            self.assertEqual(digest, hashlib.sha256(manifest_path.read_bytes()).hexdigest())

            source.write_bytes(b"tampered")
            with self.assertRaisesRegex(CycleError, "hash mismatch"):
                validate_campaign_data_dir(data_dir)


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

    def test_rejects_skipped_required_check(self):
        pr = successful_pr()
        pr["statusCheckRollup"][0]["conclusion"] = "SKIPPED"
        ready, reasons = assess_pr(pr)
        self.assertFalse(ready)
        self.assertTrue(any("SKIPPED" in reason for reason in reasons))

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
            "tools.run_agent_cycle.find_gh_executable", return_value="gh"
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

    def test_non_a_roles_route_through_integrator_without_stopping(self):
        self.assertEqual(
            next_campaign_receivers(
                role="C",
                queued_after_role=["D"],
                reported_receivers=["A"],
                progress_changed=False,
            ),
            ["D"],
        )
        self.assertEqual(
            next_campaign_receivers(
                role="D",
                queued_after_role=[],
                reported_receivers=["A"],
                progress_changed=False,
            ),
            ["A"],
        )
        self.assertEqual(
            next_campaign_receivers(
                role="E",
                queued_after_role=[],
                reported_receivers=["A"],
                progress_changed=False,
            ),
            ["A"],
        )
        with self.assertRaisesRegex(CycleError, "A integration"):
            next_campaign_receivers(
                role="A",
                queued_after_role=[],
                reported_receivers=[],
                progress_changed=False,
            )

    def test_b_artifacts_route_to_e_and_are_rehashed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = root / "package"
            package.mkdir()
            prediction = package / "valid_predictions.csv"
            prediction.write_bytes(b"row_id,score\n0,0.5\n")
            manifest = create_handoff_manifest(
                root / "runtime",
                experiment_id="exp_003",
                recipient="E",
                artifact_paths=[package],
                local_read_only_access=True,
            )
            payload = verify_handoff_manifest(manifest, expected_recipient="E")
            self.assertTrue(payload["local_read_only_access"])
            self.assertFalse(payload["manual_private_transfer_required"])
            self.assertEqual(
                next_campaign_receivers(
                    role="B",
                    queued_after_role=[],
                    reported_receivers=["E"],
                    progress_changed=False,
                ),
                ["E"],
            )
            prediction.write_bytes(b"tampered\n")
            with self.assertRaisesRegex(CycleError, "changed"):
                verify_handoff_manifest(manifest, expected_recipient="E")

    def test_full_same_host_cycle_routes_a_c_d_a_b_e_a_without_manual_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            coordination = root / "coordination"
            governance = root / "governance"
            coordination.mkdir()
            governance.mkdir()
            runtime = root / "artifacts" / "campaign"
            package = root / "private-package"
            package.mkdir()
            (package / "valid_predictions.csv").write_bytes(
                b"row_id,user_id,video_id,score\n0,u,v,0.5\n"
            )
            runtime_config = PrivateRuntimeConfig(
                config_path=root / "private-config.json",
                dev_data_dir=root / "private-dev-data",
                artifact_root=root / "private-artifact-store",
                fingerprint="f" * 64,
            )
            authorization = {
                "status": "ALLOWED",
                "experiment_ids": ["exp_003"],
                "max_completed_experiments": 1,
                "max_role_steps": 10,
                "data_mode": "train_valid_only",
                "automatic_public_valid": True,
                "test_access": False,
                "final_approval_allowed": False,
            }

            def write_state(*, active, receiver, gate="BLOCKED", terminal=False):
                current = {
                    "experiment_id": active,
                    "status": "COMPLETED_REJECTED" if terminal else "IMPLEMENTING",
                }
                state = {
                    "active_experiment_id": active,
                    "next_receiver": receiver,
                    "bounded_campaign_authorization": authorization,
                    "consecutive_no_improve": 1,
                    "stage_gates": {
                        "REAL_VALID_RUN_ALLOWED": {"status": gate}
                    },
                }
                (coordination / "current_experiment.json").write_text(
                    json.dumps(current), encoding="utf-8"
                )
                (coordination / "current_state.json").write_text(
                    json.dumps(state), encoding="utf-8"
                )

            write_state(active="exp_002", receiver="A", terminal=True)
            history = coordination / "experiment_history.jsonl"
            history.write_text("", encoding="utf-8")
            (governance / "policy.json").write_text(
                json.dumps(
                    {"max_single_round_seconds": 3600, "consecutive_no_improve": 3}
                ),
                encoding="utf-8",
            )
            sync_count = 0

            def sync_state(_repo):
                nonlocal sync_count
                sync_count += 1
                if sync_count == 2:
                    write_state(active="exp_003", receiver="C_AND_D")
                elif sync_count == 5:
                    write_state(active="exp_003", receiver="B", gate="ALLOWED")
                elif sync_count == 8:
                    write_state(active="exp_003", receiver="A", terminal=True)
                    history.write_text(
                        json.dumps(
                            {
                                "record_type": "experiment_decision",
                                "experiment_id": "exp_003",
                            }
                        )
                        + "\n",
                        encoding="utf-8",
                    )
                return "a" * 40

            roles = ["A", "C", "D", "A", "B", "E", "A"]
            next_roles = ["C_AND_D", "A", "A", "B", "E", "A", "A"]
            results = []
            for index, (role, next_role) in enumerate(zip(roles, next_roles), 1):
                results.append(
                    safe_result(
                        role=role,
                        experiment_id="exp_003",
                        commit_sha="a" * 40,
                        pr_url=f"https://github.com/example/repo/pull/{index}",
                        role_worktree=str(root),
                        next_receiver=next_role,
                        large_artifact_paths=[str(package)] if role == "B" else [],
                        formal_metrics_produced=role == "E",
                    )
                )
            args = SimpleNamespace(
                experiment="exp_003",
                max_iterations=1,
                max_role_steps=10,
                runtime_root=runtime,
                worktree_root=root / "worktrees",
                timeout_seconds=1,
                poll_seconds=5,
            )
            with (
                patch("tools.run_agent_cycle.sync_main_checkout", side_effect=sync_state),
                patch("tools.run_agent_cycle.verify_protected"),
                patch(
                    "tools.run_agent_cycle.load_private_runtime_config",
                    return_value=runtime_config,
                ),
                patch("tools.run_agent_cycle.validate_runtime_environment"),
                patch(
                    "tools.run_agent_cycle.validate_campaign_data_dir",
                    return_value=(root / "data", "d" * 64),
                ),
                patch(
                    "tools.run_agent_cycle.dispatch_role", side_effect=results
                ) as dispatch,
                patch(
                    "tools.run_agent_cycle.require_clean_worktree",
                    return_value="a" * 40,
                ),
                patch(
                    "tools.run_agent_cycle.watch_pr",
                    return_value={"ready": True, "reasons": [], "pr": {}},
                ),
            ):
                self.assertEqual(run_campaign(root, args), 0)
            self.assertEqual(
                [call.kwargs["role"] for call in dispatch.call_args_list], roles
            )
            evaluator_call = dispatch.call_args_list[5]
            self.assertIn("manifest=", evaluator_call.kwargs["handoff_context"])
            self.assertIn(
                "dev_data_dir=", evaluator_call.kwargs["private_runtime_context"]
            )
            self.assertTrue(evaluator_call.kwargs["bounded_campaign_authorized"])
            self.assertIn(
                "dataset_manifest_sha256=" + "d" * 64,
                evaluator_call.kwargs["data_context"],
            )
            saved = json.loads(
                (runtime / "campaign_state.json").read_text(encoding="utf-8")
            )
            self.assertEqual(saved["status"], "COMPLETED")
            self.assertEqual(saved["completed_experiment_ids"], ["exp_003"])
            self.assertFalse(saved["test_access"])


if __name__ == "__main__":
    unittest.main()
