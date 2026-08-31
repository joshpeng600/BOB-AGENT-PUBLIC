#!/usr/bin/env python3
"""Safely coordinate asynchronous A-E experiment-cycle work.

The coordinator is deliberately conservative: status/report operations are
read-only, role execution requires ``--execute``, formal validation additionally
requires an A-recorded gate, and large artifacts are never sent to Git.  The
continuous ``run`` action is bounded by an A-recorded campaign authorization;
it never creates or expands that authorization itself.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


ROLES = ("A", "B", "C", "D", "E")
REQUIRED_CHECKS = {
    "protected-files / verify-protected-files",
    "unit-tests / tests",
    "prediction-contract / prediction-contract",
    "repository-contracts / contracts",
}
PROTECTED_AUTOMERGE_PATHS = {
    ".gitattributes",
    "protected_manifest.json",
    "governance/protected_files.json",
}
RELEASE_ONLY_AUTOMERGE_PATHS = {
    "contracts/final_approval.template.json",
    "tools/final_approval.py",
    "tools/final_submission.py",
}
E_OWNED_TOOL_PATHS = {
    "tools/audit_run.py",
    "tools/final_submission.py",
    "tools/safe_evaluate.py",
}
TERMINAL_WORDS = ("COMPLETED", "REJECTED", "ACCEPTED", "CLOSED")
EXPERIMENT_RE = re.compile(r"^exp_(\d{3,})$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class CycleError(RuntimeError):
    """Fail-closed cycle validation error."""


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class CampaignAuthorization:
    """Validated, A-recorded limits for one continuous valid-only campaign."""

    experiment_ids: tuple[str, ...]
    max_completed_experiments: int
    max_role_steps: int
    automatic_public_valid: bool
    authorization_hash: str


@dataclass(frozen=True)
class PrivateRuntimeConfig:
    """Validated paths that must remain outside every Git checkout."""

    config_path: Path
    dev_data_dir: Path
    artifact_root: Path
    fingerprint: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run_command(
    argv: Sequence[str],
    *,
    cwd: Path,
    input_text: str | None = None,
    timeout_seconds: int | None = None,
    env: Mapping[str, str] | None = None,
) -> CommandResult:
    try:
        completed = subprocess.run(
            list(argv),
            cwd=str(cwd),
            input=input_text,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
            env=dict(env) if env is not None else None,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return CommandResult(124, stdout, stderr or "command timed out")
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


def require_success(result: CommandResult, label: str) -> str:
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "no output"
        raise CycleError(f"{label} failed ({result.returncode}): {detail}")
    return result.stdout.strip()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CycleError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CycleError(f"expected JSON object in {path}")
    return value


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_campaign_data_dir(supplied: Path | None) -> tuple[Path, str]:
    """Freeze one complete, test-free development dataset for the campaign."""

    if supplied is None:
        raise CycleError("--data-dir is required for a train-valid-only campaign")
    if supplied.is_symlink() or not supplied.is_dir():
        raise CycleError(f"campaign data directory is missing or unsafe: {supplied}")
    data_dir = supplied.resolve()
    manifest_path = data_dir / "dataset_manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise CycleError("campaign data directory has no regular dataset_manifest.json")
    manifest = load_json(manifest_path)
    if manifest.get("max_date") != 20220428:
        raise CycleError("campaign dataset manifest max_date must equal 20220428")
    if manifest.get("test_rows") != 0:
        raise CycleError("campaign dataset manifest must record test_rows=0")
    files = manifest.get("files")
    if not isinstance(files, Mapping) or not files:
        raise CycleError("campaign dataset manifest files must be a non-empty object")
    for relative, metadata in files.items():
        if not isinstance(relative, str) or not isinstance(metadata, Mapping):
            raise CycleError("campaign dataset manifest contains an invalid file entry")
        relative_path = Path(relative)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise CycleError(f"campaign dataset path is not relative: {relative}")
        supplied_candidate = data_dir / relative_path
        if supplied_candidate.is_symlink():
            raise CycleError(f"campaign dataset file is a symlink: {relative}")
        candidate = supplied_candidate.resolve()
        try:
            candidate.relative_to(data_dir)
        except ValueError as exc:
            raise CycleError(
                f"campaign dataset path escapes data directory: {relative}"
            ) from exc
        if not candidate.is_file():
            raise CycleError(f"campaign dataset file is missing or unsafe: {relative}")
        expected = metadata.get("sha256")
        if not isinstance(expected, str) or len(expected) != 64:
            raise CycleError(f"campaign dataset file has no valid SHA-256: {relative}")
        if sha256_file(candidate) != expected.lower():
            raise CycleError(f"campaign dataset file hash mismatch: {relative}")
    return data_dir, sha256_file(manifest_path)


def repository_root(start: Path | None = None) -> Path:
    start = (start or Path.cwd()).resolve()
    result = run_command(("git", "rev-parse", "--show-toplevel"), cwd=start)
    return Path(require_success(result, "git repository lookup")).resolve()


def require_clean_worktree(repo: Path) -> str:
    status = require_success(
        run_command(("git", "status", "--porcelain"), cwd=repo),
        "git status",
    )
    if status:
        raise CycleError("worktree is not clean; refusing role execution")
    return require_success(
        run_command(("git", "rev-parse", "HEAD"), cwd=repo), "git HEAD"
    )


def git_common_dir(worktree: Path) -> Path:
    """Return the exact writable Git metadata tree for a linked worktree."""

    value = require_success(
        run_command(
            ("git", "rev-parse", "--path-format=absolute", "--git-common-dir"),
            cwd=worktree,
        ),
        "git common-dir lookup",
    )
    common_dir = Path(value).resolve()
    if not common_dir.is_dir():
        raise CycleError(f"Git common-dir is missing: {common_dir}")
    return common_dir


def role_command_environment() -> dict[str, str]:
    """Preserve the runner's Python environment for Codex role subprocesses."""

    environment = dict(os.environ)
    python_executable = Path(sys.executable).absolute()
    python_bin = str(python_executable.parent)
    current_path = environment.get("PATH", "")
    environment["PATH"] = (
        python_bin if not current_path else python_bin + os.pathsep + current_path
    )
    environment["BOB_AGENT_PYTHON"] = str(python_executable)
    if sys.prefix != getattr(sys, "base_prefix", sys.prefix):
        environment["VIRTUAL_ENV"] = str(Path(sys.prefix).absolute())
    return environment


def verify_protected(repo: Path) -> None:
    result = run_command(
        (sys.executable, "scripts/check_protected_files.py"), cwd=repo
    )
    require_success(result, "protected-file verification")


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def load_private_runtime_config(
    repo: Path, supplied_path: Path | None
) -> PrivateRuntimeConfig:
    """Load a local-only JSON config and fail if any private path enters Git."""

    selected = supplied_path
    if selected is None:
        from_environment = os.environ.get("BOB_AGENT_LOCAL_CONFIG")
        selected = Path(from_environment) if from_environment else None
    if selected is None:
        raise CycleError(
            "continuous run requires --local-config or BOB_AGENT_LOCAL_CONFIG"
        )
    if not selected.is_absolute():
        raise CycleError("private runtime config path must be absolute")
    config_path = selected.resolve()
    repo = repo.resolve()
    if _is_within(config_path, repo):
        raise CycleError("private runtime config must remain outside the Git checkout")
    payload = load_json(config_path)
    allowed = {"dev_data_dir", "artifact_root"}
    unexpected = sorted(set(payload) - allowed)
    missing = sorted(allowed - set(payload))
    if unexpected or missing:
        detail = []
        if missing:
            detail.append("missing " + ", ".join(missing))
        if unexpected:
            detail.append("unexpected " + ", ".join(unexpected))
        raise CycleError("invalid private runtime config: " + "; ".join(detail))

    resolved: dict[str, Path] = {}
    for field in sorted(allowed):
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            raise CycleError(f"private runtime config {field} must be a path string")
        raw_path = Path(value)
        if not raw_path.is_absolute():
            raise CycleError(f"private runtime config {field} must be absolute")
        resolved[field] = raw_path.resolve()
        if _is_within(resolved[field], repo):
            raise CycleError(
                f"private runtime config {field} must remain outside the Git checkout"
            )

    dev_data_dir = resolved["dev_data_dir"]
    artifact_root = resolved["artifact_root"]
    if not dev_data_dir.is_dir():
        raise CycleError(f"private dev data directory does not exist: {dev_data_dir}")
    artifact_root.mkdir(parents=True, exist_ok=True)
    if not artifact_root.is_dir():
        raise CycleError(f"private artifact root is not a directory: {artifact_root}")
    if _is_within(artifact_root, dev_data_dir) or _is_within(
        dev_data_dir, artifact_root
    ):
        raise CycleError("dev_data_dir and artifact_root must be separate private trees")
    canonical = json.dumps(
        {
            "dev_data_dir": str(dev_data_dir),
            "artifact_root": str(artifact_root),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return PrivateRuntimeConfig(
        config_path=config_path,
        dev_data_dir=dev_data_dir,
        artifact_root=artifact_root,
        fingerprint=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    )


def validate_runtime_environment(repo: Path, config: PrivateRuntimeConfig) -> None:
    """Fail before dispatch if the local data, GitHub, or Codex setup is unusable."""

    require_clean_worktree(repo)
    origin = require_success(
        run_command(("git", "remote", "get-url", "origin"), cwd=repo),
        "origin remote lookup",
    )
    if not re.search(
        r"(?:github\.com[:/])joshpeng600/BOB-AGENT-PUBLIC(?:\.git)?$", origin
    ):
        raise CycleError(
            "continuous run must use joshpeng600/BOB-AGENT-PUBLIC as origin"
        )
    find_codex_executable()
    require_success(
        run_command((sys.executable, "-c", "import numpy"), cwd=repo),
        "NumPy runtime verification",
    )
    gh = find_gh_executable()
    require_success(run_command((gh, "auth", "status"), cwd=repo), "GitHub CLI auth")
    if not os.access(config.dev_data_dir, os.R_OK | os.X_OK):
        raise CycleError(f"private dev data is not readable: {config.dev_data_dir}")
    if not os.access(config.artifact_root, os.R_OK | os.W_OK | os.X_OK):
        raise CycleError(f"private artifact root is not writable: {config.artifact_root}")
    require_success(
        run_command(
            (
                sys.executable,
                "tools/preflight.py",
                "--data-dir",
                str(config.dev_data_dir),
                "--mode",
                "experiment",
            ),
            cwd=repo,
        ),
        "private train-valid data preflight",
    )


def normalize_receivers(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        tokens = [str(item) for item in value]
    else:
        tokens = re.split(r"(?:_AND_|\s*(?:/|,|\+|&)\s*)", str(value).upper())
    receivers: list[str] = []
    for token in tokens:
        token = token.strip().upper()
        if not token:
            continue
        if token not in ROLES:
            raise CycleError(f"unsupported next_receiver value: {token}")
        if token not in receivers:
            receivers.append(token)
    return receivers


def is_terminal_state(state: Mapping[str, Any]) -> bool:
    status = " ".join(
        str(state.get(key, "")).upper()
        for key in ("state", "status", "decision")
    )
    return any(word in status for word in TERMINAL_WORDS)


def next_experiment_id(experiment_id: str) -> str:
    match = EXPERIMENT_RE.fullmatch(experiment_id)
    if not match:
        raise CycleError(f"invalid experiment identifier: {experiment_id}")
    return f"exp_{int(match.group(1)) + 1:03d}"


def select_target_experiment(
    requested: str | None,
    current_experiment: Mapping[str, Any],
    current_state: Mapping[str, Any],
) -> str:
    active = str(
        current_experiment.get("experiment_id")
        or current_state.get("active_experiment_id")
        or ""
    )
    if not active:
        if not requested:
            raise CycleError("no active experiment and no --experiment supplied")
        return requested
    if not requested:
        return next_experiment_id(active) if is_terminal_state(current_experiment) else active
    if requested == active:
        return requested
    if is_terminal_state(current_experiment) and requested == next_experiment_id(active):
        return requested
    raise CycleError(
        f"requested {requested} is inconsistent with active {active} and its state"
    )


def determine_receivers(
    target: str,
    current_experiment: Mapping[str, Any],
    current_state: Mapping[str, Any],
) -> list[str]:
    active = str(current_experiment.get("experiment_id", ""))
    if target != active and is_terminal_state(current_experiment):
        return ["A"]
    return normalize_receivers(
        current_state.get("next_receiver") or current_experiment.get("next_receiver")
    )


def real_valid_gate_status(current_state: Mapping[str, Any]) -> str:
    stage_gates = current_state.get("stage_gates", {})
    if not isinstance(stage_gates, Mapping):
        return "MISSING"
    gate = stage_gates.get("REAL_VALID_RUN_ALLOWED", {})
    if not isinstance(gate, Mapping):
        return "MISSING"
    return str(gate.get("status", "MISSING")).upper()


def real_valid_gate_is_allowed(status: str) -> bool:
    """Recognize only the exact A-owned public-validation gate statuses."""

    return status.upper() in {
        "ALLOWED",
        "ALLOWED_EXACTLY_ONE_VALID_ONLY_PAIR",
        "ALLOWED_EXACTLY_ONE_FULL_BUDGET_VALID_ONLY_PAIR",
    }


def _positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise CycleError(f"campaign authorization {field} must be a positive integer")
    return value


def validate_campaign_authorization(
    current_state: Mapping[str, Any],
    *,
    start_experiment_id: str,
    requested_iterations: int,
    requested_role_steps: int | None,
) -> CampaignAuthorization:
    """Validate an A-owned authorization without creating or widening it."""

    raw = current_state.get("bounded_campaign_authorization")
    if not isinstance(raw, Mapping):
        raise CycleError("missing A-recorded bounded_campaign_authorization")
    if str(raw.get("status", "")).upper() != "ALLOWED":
        raise CycleError("bounded campaign authorization is not ALLOWED")
    if raw.get("data_mode") != "train_valid_only":
        raise CycleError("bounded campaign must be train_valid_only")
    if raw.get("automatic_public_valid") is not True:
        raise CycleError("bounded campaign does not authorize automatic public validation")
    if raw.get("test_access") is not False:
        raise CycleError("bounded campaign must explicitly forbid test access")
    if raw.get("final_approval_allowed") is not False:
        raise CycleError("bounded campaign must explicitly forbid final approval")

    supplied_ids = raw.get("experiment_ids")
    if not isinstance(supplied_ids, list) or not supplied_ids:
        raise CycleError("campaign authorization experiment_ids must be a non-empty list")
    experiment_ids = tuple(str(item) for item in supplied_ids)
    if len(set(experiment_ids)) != len(experiment_ids):
        raise CycleError("campaign authorization experiment_ids contains duplicates")
    for index, experiment_id in enumerate(experiment_ids):
        if not EXPERIMENT_RE.fullmatch(experiment_id):
            raise CycleError(f"invalid campaign experiment identifier: {experiment_id}")
        if index and experiment_id != next_experiment_id(experiment_ids[index - 1]):
            raise CycleError("campaign authorization experiment_ids must be consecutive")

    maximum = _positive_int(
        raw.get("max_completed_experiments"), "max_completed_experiments"
    )
    max_role_steps = _positive_int(raw.get("max_role_steps"), "max_role_steps")
    if maximum > len(experiment_ids):
        raise CycleError("campaign maximum exceeds its explicit experiment_ids")
    if requested_iterations <= 0:
        raise CycleError("--max-iterations must be a positive integer")
    if requested_iterations > maximum:
        raise CycleError("requested iterations exceed A-recorded campaign maximum")
    if start_experiment_id not in experiment_ids:
        raise CycleError("requested start experiment is outside the A-recorded campaign")
    start_index = experiment_ids.index(start_experiment_id)
    if start_index + requested_iterations > len(experiment_ids):
        raise CycleError("requested iterations exceed the authorized experiment range")
    if requested_role_steps is not None:
        if requested_role_steps <= 0:
            raise CycleError("--max-role-steps must be a positive integer")
        if requested_role_steps > max_role_steps:
            raise CycleError("requested role steps exceed A-recorded campaign maximum")

    canonical = json.dumps(raw, sort_keys=True, separators=(",", ":"))
    return CampaignAuthorization(
        experiment_ids=experiment_ids,
        max_completed_experiments=maximum,
        max_role_steps=max_role_steps,
        automatic_public_valid=True,
        authorization_hash=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    )


def completed_experiment_ids(records: Sequence[Mapping[str, Any]]) -> set[str]:
    return {
        str(record["experiment_id"])
        for record in records
        if record.get("record_type") == "experiment_decision"
        and isinstance(record.get("experiment_id"), str)
        and EXPERIMENT_RE.fullmatch(str(record["experiment_id"]))
    }


def repository_progress_fingerprint(repo: Path) -> str:
    """Hash only A-owned routing/decision state used to authorize the next step."""

    digest = hashlib.sha256()
    for relative in (
        "coordination/current_experiment.json",
        "coordination/current_state.json",
        "coordination/experiment_history.jsonl",
    ):
        path = repo / relative
        if not path.is_file():
            raise CycleError(f"missing campaign progress file: {relative}")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def consecutive_no_improve_limit(repo: Path) -> int:
    policy = load_json(repo / "governance" / "policy.json")
    return _positive_int(
        policy.get("consecutive_no_improve"), "policy consecutive_no_improve"
    )


def current_no_improve_count(current_state: Mapping[str, Any]) -> int:
    value = current_state.get("consecutive_no_improve", 0)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CycleError("current consecutive_no_improve must be a non-negative integer")
    return value


def build_role_prompt(
    *,
    role: str,
    experiment_id: str,
    gate_status: str,
    allow_real_valid: bool,
    bounded_campaign_authorized: bool = False,
    campaign_public_valid_authorized: bool = False,
    data_context: str | None = None,
    handoff_context: str | None = None,
    integration_context: str | None = None,
    private_runtime_context: str | None = None,
    python_executable: str | None = None,
) -> str:
    formal_run_allowed = (
        role == "B"
        and real_valid_gate_is_allowed(gate_status)
        and (allow_real_valid or campaign_public_valid_authorized)
    )
    formal_evaluation_allowed = (
        role == "E"
        and real_valid_gate_is_allowed(gate_status)
        and campaign_public_valid_authorized
    )
    if formal_run_allowed and campaign_public_valid_authorized:
        formal_instruction = (
            "A's recorded REAL_VALID gate is ALLOWED and the invocation is inside "
            "A's bounded train-valid-only campaign. Execute only the approved "
            "valid-only run; this does not authorize hidden-test or final-release work."
        )
    elif formal_run_allowed:
        formal_instruction = (
            "A's recorded REAL_VALID gate is ALLOWED and this invocation explicitly "
            "permits B to execute only the approved valid-only run."
        )
    elif formal_evaluation_allowed:
        formal_instruction = (
            "A's bounded train-valid-only campaign and REAL_VALID gate are ALLOWED. "
            "Do not train. Independently evaluate only B's immutable approved validation "
            "artifacts; hidden-test and final-release work remain forbidden."
        )
    else:
        formal_instruction = (
            "Do not run real data training or produce formal validation metrics."
        )
    local_context = ""
    if bounded_campaign_authorized and role == "A":
        local_context += (
            "\nBounded campaign authority:\n"
            "The repository owner already authorized this exact bounded campaign. "
            "Do not request repeated per-experiment operator approval. A must still "
            "verify every recorded C/D/B/E prerequisite before opening or consuming "
            "REAL_VALID_RUN_ALLOWED, and must stop on any governance stop condition.\n"
        )
    if data_context:
        local_context += (
            "\nPrivate read-only development dataset (never copy into Git):\n"
            f"{data_context}\nUse only this exact path and verify the frozen manifest "
            "hash before data-dependent work.\n"
        )
    if handoff_context:
        local_context += (
            "\nPrivate read-only artifact handoff (never commit these files):\n"
            f"{handoff_context}\nVerify the manifest hashes before use.\n"
        )
    if integration_context:
        local_context += (
            "\nAutomatic A-integration context:\n"
            f"{integration_context}\nReview the merged role evidence and advance only "
            "the canonical routing state justified by it.\n"
        )
    if private_runtime_context:
        local_context += (
            "\nPrivate runtime paths (read locally; never copy into Git):\n"
            f"{private_runtime_context}\n"
        )
    if python_executable:
        local_context += (
            "\nRepository Python runtime:\n"
            f"Use {python_executable} for every Python command; do not replace it "
            "with a bare python or another interpreter. NumPy was preflighted in "
            "this exact runtime.\n"
        )
    return f"""You are Track 2 role {role} continuing {experiment_id} asynchronously.

Read AGENTS.md, .codex/agents/{role}.toml, coordination/current_state.json,
coordination/current_experiment.json, and the applicable experiment evidence.
Stay within role {role}'s write authority. Work on the already prepared role
branch, preserve user files, use a pull request, and never commit generated
data, predictions, checkpoints, credentials, or artifacts.

Safety constraints:
- Never access, compute, print, or report test labels or test metrics.
- Never use quarantined PR #25 evidence.
- Never create final approval.
- {formal_instruction}
- Small evidence may be committed through the PR. Large artifacts must remain
  local and be listed in large_artifact_paths for a private hashed handoff.
- If a prerequisite is absent, return BLOCKED instead of inventing evidence.
{local_context}

Complete only role {role}'s currently legal next step for {experiment_id}, run
the repository checks required by AGENTS.md, push the role branch, and create a
PR without merging it. Your final response must satisfy the supplied JSON
schema. Set test_access, pr_25_evidence_used, and final_approval_created false.
"""


def find_codex_executable() -> str:
    candidates = ["codex.cmd", "codex"] if os.name == "nt" else ["codex"]
    for candidate in candidates:
        found = shutil.which(candidate)
        if found:
            return found
    raise CycleError("Codex CLI was not found on PATH")


def find_gh_executable() -> str:
    found = shutil.which("gh")
    if found:
        return found
    user_local = Path.home() / ".local" / "bin" / "gh"
    if user_local.is_file() and os.access(user_local, os.X_OK):
        return str(user_local)
    raise CycleError("GitHub CLI is missing; install gh and run gh auth login")


def build_codex_command(
    *,
    executable: str,
    worktree: Path,
    schema: Path,
    last_message: Path,
    session_id: str | None = None,
    git_metadata_dir: Path | None = None,
) -> list[str]:
    if session_id:
        return [
            executable,
            "exec",
            "resume",
            session_id,
            "--output-schema",
            str(schema),
            "--json",
            "-o",
            str(last_message),
            "-",
        ]
    command = [
        executable,
        "exec",
        "-c",
        "shell_environment_policy.inherit=all",
        "-c",
        "sandbox_workspace_write.network_access=true",
        "-C",
        str(worktree),
        "-s",
        "workspace-write",
    ]
    if git_metadata_dir is not None:
        command.extend(("--add-dir", str(git_metadata_dir)))
    command.extend([
        "--output-schema",
        str(schema),
        "--json",
        "-o",
        str(last_message),
        "-",
    ])
    return command


def validate_agent_result(
    value: Mapping[str, Any], *, role: str, experiment_id: str
) -> None:
    required = {
        "status",
        "role",
        "phase",
        "experiment_id",
        "summary",
        "commit_sha",
        "pr_url",
        "small_evidence_paths",
        "large_artifact_paths",
        "next_receiver",
        "formal_metrics_produced",
        "pr_25_evidence_used",
        "final_approval_created",
        "test_access",
    }
    missing = sorted(required - set(value))
    if missing:
        raise CycleError(f"agent result is missing fields: {', '.join(missing)}")
    if value["role"] != role or value["experiment_id"] != experiment_id:
        raise CycleError("agent result role or experiment_id does not match dispatch")
    if value["status"] not in {"COMPLETED", "WAITING", "BLOCKED", "FAILED"}:
        raise CycleError(f"invalid agent status: {value['status']}")
    for field in ("test_access", "pr_25_evidence_used", "final_approval_created"):
        if value[field] is not False:
            raise CycleError(f"unsafe agent result: {field} must be false")
    if not isinstance(value["formal_metrics_produced"], bool):
        raise CycleError("agent result formal_metrics_produced must be boolean")
    if value["formal_metrics_produced"] and role != "E":
        raise CycleError("only independent evaluator E may report formal metrics")
    sha = value.get("commit_sha")
    if sha is not None and not SHA_RE.fullmatch(str(sha)):
        raise CycleError("agent result commit_sha must be a full lowercase SHA")
    for field in ("small_evidence_paths", "large_artifact_paths"):
        if not isinstance(value[field], list) or not all(
            isinstance(item, str) for item in value[field]
        ):
            raise CycleError(f"agent result {field} must be an array of paths")
        if len(value[field]) != len(set(value[field])):
            raise CycleError(f"agent result {field} must not contain duplicate paths")
    normalize_receivers(value.get("next_receiver"))


def safe_branch_name(role: str, experiment_id: str) -> str:
    return f"{role}/{experiment_id}-auto"


def fast_forward_to_origin_main(worktree: Path, *, label: str) -> str:
    """Refresh a clean checkout without rebasing, resetting, or rewriting history."""

    require_clean_worktree(worktree)
    head = require_success(
        run_command(("git", "rev-parse", "HEAD"), cwd=worktree), f"{label} HEAD"
    )
    origin_main = require_success(
        run_command(("git", "rev-parse", "origin/main"), cwd=worktree),
        f"{label} origin/main",
    )
    if head == origin_main:
        return head
    ancestor = run_command(
        ("git", "merge-base", "--is-ancestor", head, origin_main), cwd=worktree
    )
    if ancestor.returncode != 0:
        raise CycleError(
            f"{label} cannot fast-forward to origin/main; refusing rebase or reset"
        )
    require_success(
        run_command(("git", "merge", "--ff-only", "origin/main"), cwd=worktree),
        f"{label} fast-forward",
    )
    return require_clean_worktree(worktree)


def sync_main_checkout(repo: Path) -> str:
    branch = require_success(
        run_command(("git", "branch", "--show-current"), cwd=repo),
        "current branch lookup",
    )
    if branch != "main":
        raise CycleError("continuous run must be launched from the clean main checkout")
    require_success(run_command(("git", "fetch", "origin", "main"), cwd=repo), "git fetch")
    return fast_forward_to_origin_main(repo, label="main checkout")


def prepare_role_worktree(
    repo: Path, *, role: str, experiment_id: str, worktree_root: Path | None
) -> Path:
    require_success(run_command(("git", "fetch", "origin", "main"), cwd=repo), "git fetch")
    root = worktree_root or (
        Path(tempfile.gettempdir())
        / "bob-agent-cycle"
        / hashlib.sha256(str(repo).encode("utf-8")).hexdigest()[:12]
    )
    path = (root / experiment_id / role.lower()).resolve()
    branch = safe_branch_name(role, experiment_id)
    if path.exists():
        try:
            actual = repository_root(path)
        except CycleError as exc:
            raise CycleError(f"existing role worktree is invalid: {path}") from exc
        if actual != path:
            raise CycleError(f"existing role worktree resolves unexpectedly: {actual}")
        fast_forward_to_origin_main(path, label=f"existing {role} role worktree")
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    branch_exists = run_command(
        ("git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"), cwd=repo
    ).returncode == 0
    if branch_exists:
        raise CycleError(
            f"local branch {branch} exists without its recorded worktree; inspect manually"
        )
    require_success(
        run_command(
            ("git", "worktree", "add", "-b", branch, str(path), "origin/main"),
            cwd=repo,
        ),
        "role worktree creation",
    )
    return path


def extract_session_id(events_text: str) -> str | None:
    for line in events_text.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "thread.started":
            value = event.get("thread_id") or event.get("session_id")
            if isinstance(value, str) and value:
                return value
    return None


def dispatch_role(
    repo: Path,
    runtime: Path,
    *,
    role: str,
    experiment_id: str,
    gate_status: str,
    allow_real_valid: bool,
    worktree_root: Path | None,
    resume_session: str | None,
    bounded_campaign_authorized: bool = False,
    campaign_public_valid_authorized: bool = False,
    execution_timeout_seconds: int | None = None,
    data_context: str | None = None,
    handoff_context: str | None = None,
    integration_context: str | None = None,
    private_runtime_context: str | None = None,
) -> dict[str, Any]:
    worktree = prepare_role_worktree(
        repo, role=role, experiment_id=experiment_id, worktree_root=worktree_root
    )
    repository_git_dir = git_common_dir(repo)
    role_git_dir = git_common_dir(worktree)
    if role_git_dir != repository_git_dir:
        raise CycleError("role worktree does not share the coordinator Git metadata")
    role_runtime = runtime / role.lower()
    role_runtime.mkdir(parents=True, exist_ok=True)
    schema = repo / "contracts" / "agent_cycle_result.schema.json"
    last_message = role_runtime / "last_message.json"
    events = role_runtime / "events.jsonl"
    command = build_codex_command(
        executable=find_codex_executable(),
        worktree=worktree,
        schema=schema,
        last_message=last_message,
        session_id=resume_session,
        git_metadata_dir=role_git_dir,
    )
    prompt = build_role_prompt(
        role=role,
        experiment_id=experiment_id,
        gate_status=gate_status,
        allow_real_valid=allow_real_valid,
        bounded_campaign_authorized=bounded_campaign_authorized,
        campaign_public_valid_authorized=campaign_public_valid_authorized,
        data_context=data_context,
        handoff_context=handoff_context,
        integration_context=integration_context,
        private_runtime_context=private_runtime_context,
        python_executable=str(Path(sys.executable).absolute()),
    )
    result = run_command(
        command,
        cwd=worktree,
        input_text=prompt,
        timeout_seconds=execution_timeout_seconds,
        env=role_command_environment(),
    )
    events.write_text(result.stdout, encoding="utf-8")
    session_id = extract_session_id(result.stdout)
    if result.returncode != 0:
        write_json(
            role_runtime / "stopped_manifest.json",
            {
                "status": "STOPPED",
                "role": role,
                "experiment_id": experiment_id,
                "exit_code": result.returncode,
                "session_id": session_id,
                "recorded_at_utc": utc_now(),
                "test_access": False,
            },
        )
        detail = result.stderr.strip() or "see events.jsonl"
        raise CycleError(f"Codex role execution stopped: {detail}")
    value = load_json(last_message)
    validate_agent_result(value, role=role, experiment_id=experiment_id)
    value = dict(value)
    value["session_id"] = session_id
    value["role_worktree"] = str(worktree)
    write_json(role_runtime / "result.json", value)
    return value


def artifact_inventory(paths: Iterable[Path]) -> list[dict[str, Any]]:
    inventory: list[dict[str, Any]] = []
    for supplied in paths:
        path = supplied.resolve()
        if not path.exists():
            raise CycleError(f"artifact path does not exist: {path}")
        files = [path] if path.is_file() else sorted(item for item in path.rglob("*") if item.is_file())
        base = path.parent if path.is_file() else path
        for file_path in files:
            if file_path.is_symlink():
                raise CycleError(f"symlink artifacts are not accepted: {file_path}")
            inventory.append(
                {
                    "source_root": str(path),
                    "relative_path": file_path.relative_to(base).as_posix(),
                    "size_bytes": file_path.stat().st_size,
                    "sha256": sha256_file(file_path),
                }
            )
    return inventory


def _verify_private_store_package(package: Path, package_id: str) -> Path:
    metadata = load_json(package / "package_manifest.json")
    if metadata.get("package_id") != package_id:
        raise CycleError("private artifact package identity does not match its path")
    if metadata.get("git_upload_allowed") is not False:
        raise CycleError("private artifact package must forbid Git upload")
    if metadata.get("test_access") is not False:
        raise CycleError("private artifact package must preserve test isolation")
    records = metadata.get("files")
    if not isinstance(records, list) or not records:
        raise CycleError("private artifact package contains no file records")
    canonical = json.dumps(records, sort_keys=True, separators=(",", ":"))
    if hashlib.sha256(canonical.encode("utf-8")).hexdigest() != package_id:
        raise CycleError("private artifact package manifest does not match package ID")
    data_root = (package / "data").resolve()
    expected_paths: set[str] = set()
    for record in records:
        if not isinstance(record, Mapping):
            raise CycleError("private artifact package contains an invalid record")
        relative = Path(str(record.get("stored_relative_path", "")))
        if relative.is_absolute() or ".." in relative.parts:
            raise CycleError("private artifact package contains an unsafe path")
        expected_paths.add(relative.as_posix())
        candidate = (data_root / relative).resolve()
        try:
            candidate.relative_to(data_root)
        except ValueError as exc:
            raise CycleError("private artifact package path escapes its root") from exc
        if candidate.is_symlink() or not candidate.is_file():
            raise CycleError(f"private artifact package file is unavailable: {candidate}")
        if candidate.stat().st_size != record.get("size_bytes"):
            raise CycleError(f"private artifact package size changed: {candidate}")
        if sha256_file(candidate) != record.get("sha256"):
            raise CycleError(f"private artifact package hash changed: {candidate}")
    actual_paths = {
        item.relative_to(data_root).as_posix()
        for item in data_root.rglob("*")
        if item.is_file()
    }
    if actual_paths != expected_paths:
        raise CycleError("private artifact package file inventory changed")
    return data_root


def snapshot_artifacts_to_store(
    artifact_root: Path,
    *,
    experiment_id: str,
    artifact_paths: Sequence[Path],
) -> list[Path]:
    """Copy role outputs into a content-addressed local package outside Git."""

    if not EXPERIMENT_RE.fullmatch(experiment_id):
        raise CycleError(f"invalid artifact experiment identifier: {experiment_id}")
    if not artifact_paths:
        raise CycleError("private artifact snapshot requires at least one path")
    store = artifact_root.resolve()
    store.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    sources: list[tuple[Path, Path]] = []
    for root_index, supplied in enumerate(artifact_paths):
        source_root = supplied.resolve()
        if not source_root.exists() or source_root.is_symlink():
            raise CycleError(f"artifact source is unavailable or a symlink: {source_root}")
        files = (
            [source_root]
            if source_root.is_file()
            else sorted(item for item in source_root.rglob("*") if item.is_file())
        )
        if not files:
            raise CycleError(f"artifact source contains no files: {source_root}")
        base = source_root.parent if source_root.is_file() else source_root
        for file_path in files:
            if file_path.is_symlink():
                raise CycleError(f"symlink artifacts are not accepted: {file_path}")
            source_relative = file_path.relative_to(base)
            stored_relative = Path(f"root_{root_index:03d}") / source_relative
            record = {
                "source_label": source_root.name,
                "source_relative_path": source_relative.as_posix(),
                "stored_relative_path": stored_relative.as_posix(),
                "size_bytes": file_path.stat().st_size,
                "sha256": sha256_file(file_path),
            }
            records.append(record)
            sources.append((file_path, stored_relative))
    canonical = json.dumps(records, sort_keys=True, separators=(",", ":"))
    package_id = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    experiment_root = store / experiment_id
    experiment_root.mkdir(parents=True, exist_ok=True)
    package = experiment_root / package_id
    if package.exists():
        return [_verify_private_store_package(package, package_id)]

    stage = Path(tempfile.mkdtemp(prefix=".staging-", dir=experiment_root))
    try:
        data_root = stage / "data"
        for (source, relative), record in zip(sources, records):
            destination = data_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            if destination.stat().st_size != record["size_bytes"]:
                raise CycleError(f"artifact changed while copying: {source}")
            if sha256_file(destination) != record["sha256"]:
                raise CycleError(f"artifact hash changed while copying: {source}")
        write_json(
            stage / "package_manifest.json",
            {
                "schema_version": 1,
                "package_id": package_id,
                "experiment_id": experiment_id,
                "git_upload_allowed": False,
                "test_access": False,
                "files": records,
            },
        )
        try:
            stage.replace(package)
        except FileExistsError:
            shutil.rmtree(stage)
        data_root = _verify_private_store_package(package, package_id)
        for file_path in data_root.rglob("*"):
            if file_path.is_file():
                file_path.chmod(0o444)
        (package / "package_manifest.json").chmod(0o444)
        for directory in sorted(
            (item for item in data_root.rglob("*") if item.is_dir()),
            key=lambda item: len(item.parts),
            reverse=True,
        ):
            directory.chmod(0o555)
        data_root.chmod(0o555)
        package.chmod(0o555)
        return [data_root]
    except BaseException:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)
        raise


def create_handoff_manifest(
    runtime: Path,
    *,
    experiment_id: str,
    recipient: str,
    artifact_paths: Sequence[Path],
    local_read_only_access: bool = False,
    artifact_store_root: Path | None = None,
) -> Path:
    if recipient not in ROLES:
        raise CycleError(f"invalid recipient role: {recipient}")
    manifest_path = runtime / "handoff" / f"to_{recipient.lower()}.json"
    write_json(
        manifest_path,
        {
            "schema_version": 1,
            "experiment_id": experiment_id,
            "recipient": recipient,
            "manual_private_transfer_required": not local_read_only_access,
            "local_read_only_access": local_read_only_access,
            "artifact_store_root": (
                str(artifact_store_root.resolve()) if artifact_store_root else None
            ),
            "git_upload_allowed": False,
            "created_at_utc": utc_now(),
            "files": artifact_inventory(artifact_paths),
            "test_access": False,
        },
    )
    return manifest_path


def verify_handoff_manifest(
    path: Path,
    *,
    expected_recipient: str,
    expected_artifact_root: Path | None = None,
) -> dict[str, Any]:
    """Re-hash every private artifact immediately before the receiver reads it."""

    payload = load_json(path)
    if payload.get("recipient") != expected_recipient:
        raise CycleError("artifact handoff recipient does not match dispatched role")
    if payload.get("git_upload_allowed") is not False:
        raise CycleError("artifact handoff must explicitly forbid Git upload")
    if payload.get("test_access") is not False:
        raise CycleError("artifact handoff must preserve test isolation")
    verified_store: Path | None = None
    if expected_artifact_root is not None:
        verified_store = expected_artifact_root.resolve()
        if payload.get("artifact_store_root") != str(verified_store):
            raise CycleError("artifact handoff store root does not match runtime config")
        if payload.get("local_read_only_access") is not True:
            raise CycleError("artifact handoff does not permit same-host read-only access")
    files = payload.get("files")
    if not isinstance(files, list) or not files:
        raise CycleError("artifact handoff manifest contains no files")
    for item in files:
        if not isinstance(item, Mapping):
            raise CycleError("artifact handoff contains an invalid file record")
        raw_source_root = Path(str(item.get("source_root", "")))
        if raw_source_root.is_symlink():
            raise CycleError("artifact handoff source root must not be a symlink")
        source_root = raw_source_root.resolve()
        if verified_store is not None and not _is_within(source_root, verified_store):
            raise CycleError("artifact handoff source is outside the private store")
        relative = Path(str(item.get("relative_path", "")))
        if relative.is_absolute() or ".." in relative.parts:
            raise CycleError("artifact handoff contains an unsafe relative path")
        if source_root.is_file():
            if relative.as_posix() != source_root.name:
                raise CycleError("artifact handoff file record does not match source root")
            raw_candidate = raw_source_root
        else:
            raw_candidate = raw_source_root / relative
        if raw_candidate.is_symlink() or not raw_candidate.is_file():
            raise CycleError(f"artifact handoff file is unavailable: {raw_candidate}")
        candidate = raw_candidate.resolve()
        if not source_root.is_file():
            try:
                candidate.relative_to(source_root)
            except ValueError as exc:
                raise CycleError("artifact handoff file escapes its source root") from exc
        if not candidate.is_file():
            raise CycleError(f"artifact handoff file is unavailable: {candidate}")
        expected_size = item.get("size_bytes")
        if candidate.stat().st_size != expected_size:
            raise CycleError(f"artifact handoff size changed: {candidate}")
        if sha256_file(candidate) != item.get("sha256"):
            raise CycleError(f"artifact handoff hash changed: {candidate}")
    return payload


def parse_history(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CycleError(f"invalid history JSONL line {number}: {exc}") from exc
        if isinstance(value, dict):
            records.append(value)
    return records


def experiment_comparison(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    comparison: list[dict[str, Any]] = []
    for record in records:
        if record.get("record_type") != "experiment_decision":
            continue
        comparison.append(
            {
                "experiment_id": record.get("experiment_id"),
                "decision": record.get("decision"),
                "baseline_primary": record.get("baseline_primary"),
                "candidate_primary": record.get("candidate_primary"),
                "primary_delta": record.get("primary_delta"),
                "test_access": record.get("test_access"),
            }
        )
    return comparison


def render_status_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        f"# Agent cycle status: {report['target_experiment_id']}",
        "",
        f"- Generated: `{report['generated_at_utc']}`",
        f"- Current repository experiment: `{report['repository_experiment_id']}`",
        f"- Current champion: `{report['champion_experiment_id']}`",
        f"- Next receiver(s): `{', '.join(report['next_receivers']) or 'none'}`",
        f"- REAL_VALID gate: `{report['real_valid_gate_status']}`",
        f"- Test access: `{str(report['test_access']).lower()}`",
        "",
        "## Experiment comparison",
        "",
        "| Experiment | Decision | Baseline primary | Candidate primary | Delta |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in report["experiment_comparison"]:
        lines.append(
            "| {experiment_id} | {decision} | {baseline_primary} | "
            "{candidate_primary} | {primary_delta} |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Demo summary",
            "",
            "The coordinator reads governance state, dispatches only the legal next role, "
            "waits for reviewable PR evidence, and keeps large artifacts outside Git.",
            f"The verified champion is {report['champion_experiment_id']}; "
            "the next experiment remains uncreated until A proposes it.",
            "Hidden test was never accessed by this report or the recorded ordinary cycle.",
            "",
        ]
    )
    return "\n".join(lines)


def generate_reports(
    repo: Path,
    runtime: Path,
    *,
    target: str,
    current_experiment: Mapping[str, Any],
    current_state: Mapping[str, Any],
) -> dict[str, Any]:
    receivers = determine_receivers(target, current_experiment, current_state)
    comparison = experiment_comparison(
        parse_history(repo / "coordination" / "experiment_history.jsonl")
    )
    report = {
        "schema_version": 1,
        "generated_at_utc": utc_now(),
        "target_experiment_id": target,
        "repository_experiment_id": current_experiment.get("experiment_id"),
        "repository_status": current_experiment.get("status"),
        "champion_experiment_id": current_experiment.get(
            "retained_champion_experiment_id",
            current_experiment.get("experiment_id"),
        ),
        "next_receivers": receivers,
        "real_valid_gate_status": real_valid_gate_status(current_state),
        "experiment_comparison": comparison,
        "manual_large_artifact_transfer": True,
        "test_access": False,
    }
    write_json(runtime / "cycle_state.json", report)
    (runtime / "status.md").write_text(
        render_status_markdown(report), encoding="utf-8"
    )
    write_json(
        runtime / "demo_summary.json",
        {
            "experiment_id": target,
            "current_status": current_experiment.get("status"),
            "champion_experiment_id": report["champion_experiment_id"],
            "next_receivers": receivers,
            "completed_experiments": len(comparison),
            "capabilities": [
                "state_driven_role_dispatch",
                "Codex_session_resume",
                "PR_and_CI_gate_monitoring",
                "hashed_manual_artifact_handoff",
                "cycle_status_and_experiment_comparison",
            ],
            "test_access": False,
        },
    )
    return report


def role_owns_path(role: str, path: str) -> bool:
    """Conservative auto-merge allowlist derived from AGENTS.md ownership."""

    if path.startswith(f"coordination/inbox/{role}/"):
        return True
    if role == "A":
        return (
            path == "AGENTS.md"
            or path == "README.md"
            or path.startswith("governance/")
            or path.startswith(".github/")
            or path.startswith(".codex/")
            or path.startswith("experiments/")
            or path.startswith("configs/approved/")
            or path.startswith("coordination/iterations/")
            or path.startswith("reports/decisions/")
            or path.startswith("docs/")
            or path
            in {
                "coordination/current_state.json",
                "coordination/current_experiment.json",
                "coordination/experiment_history.jsonl",
            }
        )
    if role == "B":
        return (
            path.startswith("tests/")
            or path.startswith("contracts/")
            or path.startswith("scripts/")
            or (path.startswith("tools/") and path not in E_OWNED_TOOL_PATHS)
            or path.startswith("reports/bootstrap/")
        )
    if role == "C":
        return path.startswith("src/data/")
    if role == "D":
        return (
            path.startswith("src/models/")
            or path.startswith("src/training/")
            or path.startswith("configs/candidates/")
        )
    if role == "E":
        return (
            path.startswith("evaluation/")
            or path in E_OWNED_TOOL_PATHS
            or path.startswith("reports/evaluation/")
            or path.startswith("coordination/results/")
        )
    return False


def assess_pr(
    pr: Mapping[str, Any],
    *,
    expected_head_sha: str | None = None,
    expected_role: str | None = None,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if pr.get("state") != "OPEN":
        reasons.append(f"PR state is {pr.get('state')}, not OPEN")
    if pr.get("mergeable") != "MERGEABLE":
        reasons.append(f"PR mergeable is {pr.get('mergeable')}")
    files = {
        str(item.get("path", ""))
        for item in pr.get("files", [])
        if isinstance(item, Mapping)
    }
    unsafe = sorted(
        path
        for path in files
        if path.startswith("starter/")
        or path in PROTECTED_AUTOMERGE_PATHS
        or path in RELEASE_ONLY_AUTOMERGE_PATHS
        or "/final_approval" in path
    )
    if unsafe:
        reasons.append("protected paths require human review: " + ", ".join(unsafe))
    if expected_role is not None:
        ownership_conflicts = sorted(
            path for path in files if not role_owns_path(expected_role, path)
        )
        if ownership_conflicts:
            reasons.append(
                f"role {expected_role} does not own changed paths: "
                + ", ".join(ownership_conflicts)
            )
    if expected_head_sha is not None and pr.get("headRefOid") != expected_head_sha:
        reasons.append(
            "PR head does not match dispatched role commit: "
            f"expected {expected_head_sha}, observed {pr.get('headRefOid', 'MISSING')}"
        )
    checks = pr.get("statusCheckRollup", [])
    observed: dict[str, str] = {}
    for check in checks if isinstance(checks, list) else []:
        if not isinstance(check, Mapping):
            continue
        workflow = check.get("workflowName")
        name = check.get("name") or check.get("context")
        full = f"{workflow} / {name}" if workflow and name else str(name or workflow or "")
        observed[full] = str(check.get("conclusion") or check.get("state") or "")
    for required in sorted(REQUIRED_CHECKS):
        if observed.get(required) != "SUCCESS":
            reasons.append(
                f"required check not successful: {required}={observed.get(required, 'MISSING')}"
            )
    return not reasons, reasons


def load_pr(repo: Path, pr_number: int) -> dict[str, Any]:
    fields = "number,url,state,mergeable,mergeStateStatus,headRefOid,files,statusCheckRollup"
    stdout = require_success(
        run_command(
            (
                find_gh_executable(),
                "pr",
                "view",
                str(pr_number),
                "--json",
                fields,
            ),
            cwd=repo,
        ),
        "GitHub PR lookup",
    )
    value = json.loads(stdout)
    if not isinstance(value, dict):
        raise CycleError("GitHub PR response was not an object")
    return value


def watch_pr(
    repo: Path,
    *,
    pr_number: int,
    timeout_seconds: int,
    poll_seconds: int,
    auto_merge: bool,
    expected_head_sha: str | None = None,
    expected_role: str | None = None,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    while True:
        pr = load_pr(repo, pr_number)
        ready, reasons = assess_pr(
            pr,
            expected_head_sha=expected_head_sha,
            expected_role=expected_role,
        )
        if ready:
            if auto_merge:
                require_success(
                    run_command(
                        (
                            find_gh_executable(),
                            "pr",
                            "merge",
                            str(pr_number),
                            "--merge",
                        ),
                        cwd=repo,
                    ),
                    "GitHub PR merge",
                )
                pr = load_pr(repo, pr_number)
                if pr.get("state") != "MERGED":
                    return {
                        "ready": False,
                        "reasons": ["PR merge command completed but state is not MERGED"],
                        "pr": pr,
                    }
            return {"ready": True, "reasons": [], "pr": pr}
        terminal_block = any(
            reason.startswith("protected paths require human review")
            or reason.startswith("role ")
            or reason.startswith("PR state is")
            or reason == "PR mergeable is CONFLICTING"
            or reason.startswith("PR head does not match")
            for reason in reasons
        )
        if terminal_block or time.monotonic() >= deadline:
            return {"ready": False, "reasons": reasons, "pr": pr}
        time.sleep(poll_seconds)


def parse_pr_number(pr_url: Any) -> int | None:
    if not isinstance(pr_url, str):
        return None
    match = re.search(r"/pull/(\d+)(?:$|[/?#])", pr_url)
    return int(match.group(1)) if match else None


def _campaign_state_path(runtime: Path) -> Path:
    return runtime / "campaign_state.json"


def _record_campaign_stop(
    runtime: Path,
    campaign_state: dict[str, Any],
    *,
    reason: str,
    detail: str,
) -> None:
    campaign_state.update(
        {
            "status": "STOPPED",
            "stop_reason": reason,
            "stop_detail": detail,
            "updated_at_utc": utc_now(),
            "test_access": False,
            "final_approval_created": False,
        }
    )
    write_json(_campaign_state_path(runtime), campaign_state)


def _load_or_initialize_campaign_state(
    runtime: Path,
    *,
    start_experiment_id: str,
    authorized_experiment_ids: Sequence[str],
    max_iterations: int,
    max_role_steps: int,
    authorization_hash: str,
    existing_decisions: set[str],
    runtime_config_hash: str | None = None,
    campaign_data_dir: str | None = None,
    campaign_data_manifest_sha256: str | None = None,
) -> dict[str, Any]:
    path = _campaign_state_path(runtime)
    expected_ids = list(authorized_experiment_ids)
    if path.exists():
        value = load_json(path)
        expected = {
            "start_experiment_id": start_experiment_id,
            "authorized_experiment_ids": expected_ids,
            "max_iterations": max_iterations,
            "max_role_steps": max_role_steps,
            "authorization_hash": authorization_hash,
            "runtime_config_hash": runtime_config_hash,
            "campaign_data_dir": campaign_data_dir,
            "campaign_data_manifest_sha256": campaign_data_manifest_sha256,
        }
        mismatched = [key for key, item in expected.items() if value.get(key) != item]
        if mismatched:
            raise CycleError(
                "existing campaign state does not match this invocation: "
                + ", ".join(mismatched)
            )
        if value.get("test_access") is not False:
            raise CycleError("existing campaign state does not preserve test isolation")
        return value

    if start_experiment_id in existing_decisions:
        raise CycleError(
            "start experiment was already completed; choose the next experiment or resume its existing campaign state"
        )
    value = {
        "schema_version": 1,
        "status": "RUNNING",
        "start_experiment_id": start_experiment_id,
        "authorized_experiment_ids": expected_ids,
        "max_iterations": max_iterations,
        "max_role_steps": max_role_steps,
        "role_steps_completed": 0,
        "completed_experiment_ids": [],
        "pending_receivers": [],
        "handoff_manifest": None,
        "handoff_recipient": None,
        "decisions_present_at_start": sorted(existing_decisions),
        "authorization_hash": authorization_hash,
        "runtime_config_hash": runtime_config_hash,
        "campaign_data_dir": campaign_data_dir,
        "campaign_data_manifest_sha256": campaign_data_manifest_sha256,
        "created_at_utc": utc_now(),
        "updated_at_utc": utc_now(),
        "test_access": False,
        "final_approval_created": False,
    }
    write_json(path, value)
    return value


def _refresh_campaign_completion(
    campaign_state: dict[str, Any], records: Sequence[Mapping[str, Any]]
) -> list[str]:
    decided = completed_experiment_ids(records)
    initial = set(campaign_state["decisions_present_at_start"])
    completed = [
        experiment_id
        for experiment_id in campaign_state["authorized_experiment_ids"]
        if experiment_id in decided and experiment_id not in initial
    ]
    campaign_state["completed_experiment_ids"] = completed
    campaign_state["updated_at_utc"] = utc_now()
    return completed


def next_campaign_receivers(
    *,
    role: str,
    queued_after_role: Sequence[str],
    reported_receivers: Sequence[str],
    progress_changed: bool,
) -> list[str]:
    """Route role evidence through A without trusting non-A roles to edit A state."""

    if role == "A" and not progress_changed:
        raise CycleError("A integration did not advance canonical campaign state")
    if queued_after_role:
        return list(queued_after_role)
    if not progress_changed and role == "B" and reported_receivers:
        return list(reported_receivers)
    if not progress_changed and role != "A":
        return ["A"]
    return []


def run_campaign(repo: Path, args: argparse.Namespace) -> int:
    """Run reviewed role PRs until the bounded goal or a truthful stop point."""

    sync_main_checkout(repo)
    verify_protected(repo)
    runtime_config = load_private_runtime_config(
        repo, getattr(args, "local_config", None)
    )
    validate_runtime_environment(repo, runtime_config)
    current_experiment = load_json(repo / "coordination" / "current_experiment.json")
    current_state = load_json(repo / "coordination" / "current_state.json")
    start_target = select_target_experiment(
        args.experiment, current_experiment, current_state
    )
    authorization = validate_campaign_authorization(
        current_state,
        start_experiment_id=start_target,
        requested_iterations=args.max_iterations,
        requested_role_steps=args.max_role_steps,
    )
    campaign_data_dir, campaign_data_manifest_sha256 = validate_campaign_data_dir(
        runtime_config.dev_data_dir
    )
    start_index = authorization.experiment_ids.index(start_target)
    authorized_ids = authorization.experiment_ids[
        start_index : start_index + args.max_iterations
    ]
    effective_role_steps = args.max_role_steps or authorization.max_role_steps
    runtime = (
        args.runtime_root.resolve()
        if args.runtime_root
        else repo / "artifacts" / "agent_cycle" / f"campaign_{start_target}"
    )
    history_path = repo / "coordination" / "experiment_history.jsonl"
    initial_records = parse_history(history_path)
    campaign_state = _load_or_initialize_campaign_state(
        runtime,
        start_experiment_id=start_target,
        authorized_experiment_ids=authorized_ids,
        max_iterations=args.max_iterations,
        max_role_steps=effective_role_steps,
        authorization_hash=authorization.authorization_hash,
        existing_decisions=completed_experiment_ids(initial_records),
        runtime_config_hash=runtime_config.fingerprint,
        campaign_data_dir=str(campaign_data_dir),
        campaign_data_manifest_sha256=campaign_data_manifest_sha256,
    )
    policy = load_json(repo / "governance" / "policy.json")
    execution_timeout = _positive_int(
        policy.get("max_single_round_seconds"), "policy max_single_round_seconds"
    )
    no_improve_limit = consecutive_no_improve_limit(repo)

    while True:
        current_experiment = load_json(
            repo / "coordination" / "current_experiment.json"
        )
        current_state = load_json(repo / "coordination" / "current_state.json")
        refreshed_authorization = validate_campaign_authorization(
            current_state,
            start_experiment_id=start_target,
            requested_iterations=args.max_iterations,
            requested_role_steps=effective_role_steps,
        )
        if refreshed_authorization.authorization_hash != authorization.authorization_hash:
            _record_campaign_stop(
                runtime,
                campaign_state,
                reason="AUTHORIZATION_CHANGED",
                detail="A-recorded campaign authorization changed during execution",
            )
            raise CycleError("campaign authorization changed during execution")

        history_records = parse_history(history_path)
        all_decisions = completed_experiment_ids(history_records)
        active_id = str(current_experiment.get("experiment_id", ""))
        if (
            active_id in authorized_ids
            and is_terminal_state(current_experiment)
            and active_id not in all_decisions
        ):
            _record_campaign_stop(
                runtime,
                campaign_state,
                reason="TERMINAL_DECISION_MISSING_FROM_HISTORY",
                detail=f"terminal {active_id} has no experiment_decision history record",
            )
            raise CycleError("terminal experiment is missing canonical decision history")
        completed = _refresh_campaign_completion(campaign_state, history_records)
        if len(completed) >= args.max_iterations:
            campaign_state.update(
                {
                    "status": "COMPLETED",
                    "stop_reason": "MAX_ITERATIONS_COMPLETED",
                    "updated_at_utc": utc_now(),
                    "test_access": False,
                    "final_approval_created": False,
                }
            )
            write_json(_campaign_state_path(runtime), campaign_state)
            print(json.dumps(campaign_state, indent=2, ensure_ascii=False))
            return 0
        if current_no_improve_count(current_state) >= no_improve_limit:
            _record_campaign_stop(
                runtime,
                campaign_state,
                reason="NO_IMPROVEMENT_STOP_RULE",
                detail="policy consecutive-no-improvement limit reached",
            )
            raise CycleError("campaign reached the consecutive no-improvement stop rule")
        if campaign_state["role_steps_completed"] >= effective_role_steps:
            _record_campaign_stop(
                runtime,
                campaign_state,
                reason="MAX_ROLE_STEPS",
                detail="A-recorded role-step bound reached",
            )
            raise CycleError("campaign reached its maximum role-step bound")

        remaining = [item for item in authorized_ids if item not in completed]
        target = remaining[0]
        select_target_experiment(target, current_experiment, current_state)
        target_runtime = runtime / "experiments" / target
        report = generate_reports(
            repo,
            target_runtime,
            target=target,
            current_experiment=current_experiment,
            current_state=current_state,
        )
        pending_receivers = normalize_receivers(
            campaign_state.get("pending_receivers")
        )
        receivers = pending_receivers or report["next_receivers"]
        if not receivers:
            _record_campaign_stop(
                runtime,
                campaign_state,
                reason="NO_LEGAL_RECEIVER",
                detail=f"repository has no legal receiver for {target}",
            )
            raise CycleError("repository state has no legal next receiver")
        role = receivers[0]
        queued_after_role = receivers[1:]
        gate_status = report["real_valid_gate_status"]
        campaign_public_valid = real_valid_gate_is_allowed(gate_status)
        data_context = (
            f"development_data_dir={campaign_data_dir}\n"
            f"dataset_manifest={campaign_data_dir / 'dataset_manifest.json'}\n"
            f"dataset_manifest_sha256={campaign_data_manifest_sha256}"
        )
        handoff_context: str | None = None
        handoff_manifest_value = campaign_state.get("handoff_manifest")
        if handoff_manifest_value and campaign_state.get("handoff_recipient") == role:
            handoff_path = Path(str(handoff_manifest_value))
            verify_handoff_manifest(
                handoff_path,
                expected_recipient=role,
                expected_artifact_root=runtime_config.artifact_root,
            )
            handoff_context = f"manifest={handoff_path.resolve()}"
        integration_context = None
        if role == "A" and campaign_state.get("integration_required_after_role"):
            integration_context = (
                f"previous_role={campaign_state['integration_required_after_role']}; "
                f"previous_commit={campaign_state.get('last_role_commit')}; "
                f"previous_pr={campaign_state.get('last_pr_number')}"
            )
        private_runtime_context = None
        if role in {"B", "C", "E"}:
            private_runtime_context = (
                f"dev_data_dir={runtime_config.dev_data_dir}; "
                f"artifact_root={runtime_config.artifact_root}; "
                "the data path is train/public-valid only and hidden test is forbidden"
            )
        progress_before = repository_progress_fingerprint(repo)
        result = dispatch_role(
            repo,
            target_runtime,
            role=role,
            experiment_id=target,
            gate_status=gate_status,
            allow_real_valid=False,
            worktree_root=args.worktree_root,
            resume_session=None,
            bounded_campaign_authorized=True,
            campaign_public_valid_authorized=campaign_public_valid,
            execution_timeout_seconds=execution_timeout,
            data_context=data_context,
            handoff_context=handoff_context,
            integration_context=integration_context,
            private_runtime_context=private_runtime_context,
        )
        role_worktree = Path(result["role_worktree"])
        produced_head = require_clean_worktree(role_worktree)
        if produced_head != result.get("commit_sha"):
            _record_campaign_stop(
                runtime,
                campaign_state,
                reason="ROLE_COMMIT_MISMATCH",
                detail=(
                    f"role result declared {result.get('commit_sha')} but clean worktree "
                    f"HEAD is {produced_head}"
                ),
            )
            raise CycleError("role result commit does not match its clean worktree HEAD")
        campaign_state["role_steps_completed"] += 1
        campaign_state["last_role"] = role
        campaign_state["last_role_commit"] = result.get("commit_sha")
        campaign_state["last_experiment_id"] = target
        campaign_state["updated_at_utc"] = utc_now()
        write_json(_campaign_state_path(runtime), campaign_state)

        if result["status"] != "COMPLETED":
            _record_campaign_stop(
                runtime,
                campaign_state,
                reason=f"ROLE_{result['status']}",
                detail=str(result.get("summary", "role did not complete")),
            )
            raise CycleError(f"role {role} returned {result['status']}")
        pr_number = parse_pr_number(result.get("pr_url"))
        if pr_number is None:
            _record_campaign_stop(
                runtime,
                campaign_state,
                reason="MISSING_PR",
                detail=f"completed role {role} did not return a reviewable PR",
            )
            raise CycleError("completed campaign role did not return a PR URL")
        pr_result = watch_pr(
            repo,
            pr_number=pr_number,
            timeout_seconds=max(0, args.timeout_seconds),
            poll_seconds=max(5, min(60, args.poll_seconds)),
            auto_merge=True,
            expected_head_sha=str(result["commit_sha"]),
            expected_role=role,
        )
        if not pr_result["ready"]:
            detail = "; ".join(pr_result["reasons"])
            _record_campaign_stop(
                runtime,
                campaign_state,
                reason="PR_GATE_BLOCKED",
                detail=detail,
            )
            raise CycleError(f"PR gate blocked continuous campaign: {detail}")
        campaign_state["last_pr_number"] = pr_number

        sync_main_checkout(repo)
        verify_protected(repo)
        progress_after = repository_progress_fingerprint(repo)
        large_paths = [
            supplied if supplied.is_absolute() else role_worktree / supplied
            for supplied in (
                Path(path) for path in result.get("large_artifact_paths", [])
            )
        ]
        reported_receivers = normalize_receivers(result.get("next_receiver"))
        if large_paths:
            if not reported_receivers:
                _record_campaign_stop(
                    runtime,
                    campaign_state,
                    reason="ARTIFACT_RECIPIENT_MISSING",
                    detail="large artifacts have no declared recipient",
                )
                raise CycleError("large artifacts have no declared recipient")
            stored_paths = snapshot_artifacts_to_store(
                runtime_config.artifact_root,
                experiment_id=target,
                artifact_paths=large_paths,
            )
            manifest = create_handoff_manifest(
                target_runtime,
                experiment_id=target,
                recipient=reported_receivers[0],
                artifact_paths=stored_paths,
                local_read_only_access=True,
                artifact_store_root=runtime_config.artifact_root,
            )
            campaign_state["handoff_manifest"] = str(manifest.resolve())
            campaign_state["handoff_recipient"] = reported_receivers[0]

        progress_changed = progress_after != progress_before
        if role == "A" and not progress_changed:
            _record_campaign_stop(
                runtime,
                campaign_state,
                reason="NO_STATE_PROGRESS",
                detail=(
                    "A role PR merged, but canonical routing/decision state did not change"
                ),
            )
            raise CycleError("A integration did not advance canonical campaign state")

        next_pending = next_campaign_receivers(
            role=role,
            queued_after_role=queued_after_role,
            reported_receivers=reported_receivers,
            progress_changed=progress_changed,
        )

        if role == campaign_state.get("handoff_recipient"):
            campaign_state["handoff_manifest"] = None
            campaign_state["handoff_recipient"] = None
        campaign_state["pending_receivers"] = next_pending
        campaign_state["integration_required_after_role"] = (
            role if next_pending == ["A"] else None
        )
        campaign_state["updated_at_utc"] = utc_now()
        write_json(_campaign_state_path(runtime), campaign_state)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Safely coordinate asynchronous Track 2 A-E experiment cycles."
    )
    parser.add_argument("--experiment", help="target experiment, for example exp_003")
    parser.add_argument(
        "--action",
        choices=("status", "step", "run", "watch-pr", "handoff", "report"),
        default="status",
    )
    parser.add_argument("--execute", action="store_true", help="actually invoke Codex")
    parser.add_argument("--worker-role", choices=ROLES)
    parser.add_argument("--allow-real-valid", action="store_true")
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=1,
        help="maximum newly completed experiments for --action run",
    )
    parser.add_argument(
        "--max-role-steps",
        type=int,
        help="optional tighter role-dispatch bound for --action run",
    )
    parser.add_argument("--auto-merge", action="store_true")
    parser.add_argument("--wait-pr", action="store_true")
    parser.add_argument("--pr", type=int, help="PR number for watch-pr")
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--poll-seconds", type=int, default=20)
    parser.add_argument("--recipient", choices=ROLES)
    parser.add_argument("--artifact-path", action="append", default=[])
    parser.add_argument("--resume-session")
    parser.add_argument("--worktree-root", type=Path)
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument(
        "--local-config",
        type=Path,
        help=(
            "absolute path to private JSON with dev_data_dir and artifact_root; "
            "required for --action run unless BOB_AGENT_LOCAL_CONFIG is set"
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.action != "run" and args.local_config is not None:
            raise CycleError("--local-config is valid only with --action run")
        repo = repository_root()
        if args.action == "run":
            incompatible = []
            for active, flag in (
                (args.execute, "--execute"),
                (args.worker_role is not None, "--worker-role"),
                (args.allow_real_valid, "--allow-real-valid"),
                (args.auto_merge, "--auto-merge"),
                (args.wait_pr, "--wait-pr"),
                (args.pr is not None, "--pr"),
                (args.recipient is not None, "--recipient"),
                (bool(args.artifact_path), "--artifact-path"),
                (args.resume_session is not None, "--resume-session"),
            ):
                if active:
                    incompatible.append(flag)
            if incompatible:
                raise CycleError(
                    "--action run manages execution, PR merge, and resume state itself; "
                    "remove " + ", ".join(incompatible)
                )
            return run_campaign(repo, args)

        current_experiment = load_json(repo / "coordination" / "current_experiment.json")
        current_state = load_json(repo / "coordination" / "current_state.json")
        target = select_target_experiment(args.experiment, current_experiment, current_state)
        runtime = (
            args.runtime_root.resolve()
            if args.runtime_root
            else repo / "artifacts" / "agent_cycle" / target
        )
        report = generate_reports(
            repo,
            runtime,
            target=target,
            current_experiment=current_experiment,
            current_state=current_state,
        )

        if args.action in {"status", "report"}:
            print(render_status_markdown(report))
            print(f"STATUS_PATH={runtime / 'status.md'}")
            return 0

        if args.action == "handoff":
            if not args.recipient or not args.artifact_path:
                raise CycleError("handoff requires --recipient and --artifact-path")
            manifest = create_handoff_manifest(
                runtime,
                experiment_id=target,
                recipient=args.recipient,
                artifact_paths=[Path(path) for path in args.artifact_path],
            )
            print(f"STATUS=MANUAL_TRANSFER_REQUIRED\nHANDOFF_MANIFEST={manifest}")
            return 0

        if args.action == "watch-pr":
            if not args.pr:
                raise CycleError("watch-pr requires --pr")
            result = watch_pr(
                repo,
                pr_number=args.pr,
                timeout_seconds=max(0, args.timeout_seconds),
                poll_seconds=max(5, min(60, args.poll_seconds)),
                auto_merge=args.auto_merge,
            )
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0 if result["ready"] else 2

        if not args.execute:
            raise CycleError("step is dry-run by default; add --execute to invoke Codex")
        require_clean_worktree(repo)
        verify_protected(repo)
        receivers = report["next_receivers"]
        if not receivers:
            raise CycleError("repository state has no legal next receiver")
        if args.worker_role:
            if args.worker_role not in receivers:
                print(
                    f"STATUS=WAITING_FOR_ROLE\nWORKER_ROLE={args.worker_role}\n"
                    f"NEXT_RECEIVERS={','.join(receivers)}"
                )
                return 0
            role = args.worker_role
        else:
            role = receivers[0]
        gate_status = report["real_valid_gate_status"]
        if args.allow_real_valid and not (
            role == "B" and real_valid_gate_is_allowed(gate_status)
        ):
            raise CycleError(
                "--allow-real-valid is valid only for B with recorded gate status ALLOWED"
            )
        result = dispatch_role(
            repo,
            runtime,
            role=role,
            experiment_id=target,
            gate_status=gate_status,
            allow_real_valid=args.allow_real_valid,
            worktree_root=args.worktree_root,
            resume_session=args.resume_session,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        role_worktree = Path(result["role_worktree"])
        large_paths = [
            supplied if supplied.is_absolute() else role_worktree / supplied
            for supplied in (Path(path) for path in result["large_artifact_paths"])
        ]
        if large_paths and result.get("next_receiver"):
            manifest = create_handoff_manifest(
                runtime,
                experiment_id=target,
                recipient=normalize_receivers(result["next_receiver"])[0],
                artifact_paths=large_paths,
            )
            print(f"MANUAL_TRANSFER_MANIFEST={manifest}")
        pr_number = parse_pr_number(result.get("pr_url"))
        if args.wait_pr and pr_number:
            pr_result = watch_pr(
                repo,
                pr_number=pr_number,
                timeout_seconds=max(0, args.timeout_seconds),
                poll_seconds=max(5, min(60, args.poll_seconds)),
                auto_merge=args.auto_merge,
                expected_head_sha=str(result["commit_sha"]),
                expected_role=role,
            )
            print(json.dumps(pr_result, indent=2, ensure_ascii=False))
            return 0 if pr_result["ready"] else 2
        return 0
    except (CycleError, OSError, json.JSONDecodeError) as exc:
        print(f"STATUS=BLOCKED\nERROR={exc}\ntest_access=false", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
