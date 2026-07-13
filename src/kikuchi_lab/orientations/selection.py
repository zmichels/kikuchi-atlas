"""Immutable, content-addressed human orientation selections."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from kikuchi_lab.model.identity import canonical_json, stable_id


PROOF_TREE_DIGEST_CONTRACT = {
    "schema_version": 1,
    "algorithm": "sha256",
    "file_inclusion": (
        "all non-symlink regular files recursively beneath the proof root, "
        "including manifest.json"
    ),
    "exclusions": [],
    "entry_fields": ["relative_posix_path", "sha256", "bytes"],
    "ordering": "ascending Unicode code-point order of relative_posix_path",
    "serialization": "kikuchi-lab canonical JSON encoded as UTF-8 without a newline",
    "digest_payload": "canonical JSON object with contract and ordered entries fields",
}


class OrientationSelectionError(ValueError):
    """A proof run or requested human selection is not valid."""


class SelectionExistsError(FileExistsError):
    """The immutable selection artifact already exists."""


@dataclass(frozen=True)
class OrientationSelectionResult:
    """Location and identity of a newly published selection artifact."""

    selection_id: str
    path: Path
    selection_path: Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OrientationSelectionError(f"{field} must be nonblank text")
    return value.strip()


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise OrientationSelectionError(f"{label} is unavailable: {path}") from error
    except json.JSONDecodeError as error:
        raise OrientationSelectionError(f"{label} is not valid JSON: {path}") from error
    if not isinstance(value, dict):
        raise OrientationSelectionError(f"{label} must contain a JSON object")
    return value


def _validate_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise OrientationSelectionError(f"{label} must be a lowercase SHA-256")
    try:
        int(value, 16)
    except ValueError as error:
        raise OrientationSelectionError(f"{label} must be a lowercase SHA-256") from error
    if value != value.lower():
        raise OrientationSelectionError(f"{label} must be a lowercase SHA-256")
    return value


def _verify_inventory(run: Path, manifest: dict[str, Any]) -> None:
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise OrientationSelectionError("proof manifest requires a nonempty files inventory")
    for relative, record in files.items():
        if (
            not isinstance(relative, str)
            or Path(relative).is_absolute()
            or ".." in Path(relative).parts
        ):
            raise OrientationSelectionError("proof manifest contains an unsafe file path")
        if not isinstance(record, dict):
            raise OrientationSelectionError(f"proof inventory record is invalid: {relative}")
        path = run / relative
        if not path.is_file():
            raise OrientationSelectionError(f"proof inventory file is missing: {relative}")
        expected = _validate_sha256(record.get("sha256"), f"proof inventory {relative} sha256")
        if _sha256(path) != expected:
            raise OrientationSelectionError(f"proof inventory checksum mismatch: {relative}")
        expected_bytes = record.get("bytes")
        if type(expected_bytes) is not int or path.stat().st_size != expected_bytes:
            raise OrientationSelectionError(f"proof inventory byte count mismatch: {relative}")


def _candidate_set_identity_payload(candidate_set: dict[str, Any]) -> dict[str, Any]:
    payload = {key: value for key, value in candidate_set.items() if key != "candidate_set_id"}
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        raise OrientationSelectionError("proof candidate set requires a candidates list")
    payload["candidates"] = [
        {key: value for key, value in candidate.items() if key != "zone_axis_label"}
        if isinstance(candidate, dict)
        else candidate
        for candidate in candidates
    ]
    return payload


def _content_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def proof_tree_digest(run: str | Path) -> dict[str, Any]:
    """Return the path-stable digest contract and value for a sealed proof tree."""
    root = Path(run).resolve()
    if not root.is_dir():
        raise OrientationSelectionError(f"proof run does not exist: {root}")
    paths = sorted(
        (path for path in root.rglob("*") if path.is_file() and not path.is_symlink()),
        key=lambda path: path.relative_to(root).as_posix(),
    )
    entries = [
        {
            "relative_posix_path": path.relative_to(root).as_posix(),
            "sha256": _sha256(path),
            "bytes": path.stat().st_size,
        }
        for path in paths
    ]
    payload = {"contract": PROOF_TREE_DIGEST_CONTRACT, "entries": entries}
    return {
        "contract": PROOF_TREE_DIGEST_CONTRACT,
        "file_count": len(entries),
        "sha256": _content_sha256(payload),
    }


def _selection_records(output_root: Path) -> list[tuple[Path, dict[str, Any]]]:
    records: list[tuple[Path, dict[str, Any]]] = []
    if not output_root.is_dir():
        return records
    for path in sorted(output_root.glob("orientation-selection-*/selection.json")):
        records.append((path, _load_json(path, "existing selection")))
    return records


def load_orientation_selection(path: str | Path) -> dict[str, Any]:
    """Load and validate one content-addressed selection artifact."""
    selection_path = Path(path).resolve()
    record = _load_json(selection_path, "orientation selection")
    schema_version = record.get("schema_version")
    if schema_version not in (1, 2):
        raise OrientationSelectionError("selection schema_version must be integer 1 or 2")
    decision = record.get("decision")
    if not isinstance(decision, dict):
        raise OrientationSelectionError("selection requires decision content")
    decision_sha256 = _content_sha256(decision)
    if record.get("decision_sha256") != decision_sha256:
        raise OrientationSelectionError("selection decision checksum is invalid")
    selection_id = record.get("selection_id")
    if selection_id != stable_id("orientation-selection", decision):
        raise OrientationSelectionError("selection identity is invalid")
    if selection_path.parent.name != selection_id:
        raise OrientationSelectionError("selection directory must match selection identity")
    if decision.get("schema_version") != schema_version:
        raise OrientationSelectionError("decision schema_version must match selection schema")
    if decision.get("kind") != "human-orientation-selection":
        raise OrientationSelectionError("decision kind must be human-orientation-selection")
    for field in ("author", "rationale", "selected_on"):
        _required_text(decision.get(field), field.replace("_", "-"))
    try:
        selected_on = decision["selected_on"]
        if date.fromisoformat(selected_on).isoformat() != selected_on:
            raise ValueError
    except (TypeError, ValueError) as error:
        raise OrientationSelectionError(
            "selected-on must be an ISO calendar date (YYYY-MM-DD)"
        ) from error

    proof = decision.get("proof")
    if not isinstance(proof, dict) or not isinstance(proof.get("proof_id"), str):
        raise OrientationSelectionError("decision requires a proof identity")
    _validate_sha256(proof.get("manifest_sha256"), "proof manifest_sha256")
    if schema_version == 2:
        tree_digest = proof.get("tree_digest")
        if not isinstance(tree_digest, dict):
            raise OrientationSelectionError("schema 2 decision requires a proof tree digest")
        if tree_digest.get("contract") != PROOF_TREE_DIGEST_CONTRACT:
            raise OrientationSelectionError("proof tree digest contract is invalid")
        if type(tree_digest.get("file_count")) is not int or tree_digest["file_count"] <= 0:
            raise OrientationSelectionError("proof tree digest file_count must be positive")
        _validate_sha256(tree_digest.get("sha256"), "proof tree digest sha256")
    candidate_set = decision.get("candidate_set")
    if not isinstance(candidate_set, dict) or not isinstance(
        candidate_set.get("candidate_set_id"), str
    ):
        raise OrientationSelectionError("decision requires a candidate-set identity")
    _validate_sha256(candidate_set.get("candidate_set_sha256"), "candidate-set sha256")

    selected = decision.get("selected_candidate")
    if not isinstance(selected, dict):
        raise OrientationSelectionError("decision requires selected-candidate content")
    candidate = selected.get("candidate")
    if not isinstance(candidate, dict) or selected.get("candidate_id") != candidate.get("id"):
        raise OrientationSelectionError("selected candidate identity is invalid")
    if selected.get("candidate_sha256") != _content_sha256(candidate):
        raise OrientationSelectionError("selected candidate checksum is invalid")
    _validate_sha256(selected.get("evidence_sha256"), "candidate evidence_sha256")
    geometry = selected.get("geometry")
    if not isinstance(geometry, dict) or selected.get("geometry_sha256") != _content_sha256(
        geometry
    ):
        raise OrientationSelectionError("selected geometry checksum is invalid")
    metrics = selected.get("metrics")
    if not isinstance(metrics, dict) or selected.get("metrics_sha256") != _content_sha256(
        metrics
    ):
        raise OrientationSelectionError("selected metrics checksum is invalid")
    supersession = decision.get("supersession")
    if supersession is not None:
        if not isinstance(supersession, dict):
            raise OrientationSelectionError("decision supersession must be null or an object")
        _required_text(supersession.get("selection_id"), "superseded selection-id")
        _required_text(supersession.get("reason"), "supersede-reason")
        _validate_sha256(supersession.get("decision_sha256"), "superseded decision_sha256")
        _validate_sha256(supersession.get("selection_sha256"), "superseded selection_sha256")
    return record


def create_orientation_selection(
    *,
    run: str | Path,
    candidate_id: str,
    author: str,
    rationale: str,
    selected_on: str,
    output_root: str | Path,
    supersedes: str | None = None,
    supersede_reason: str | None = None,
) -> OrientationSelectionResult:
    """Validate a sealed proof and publish one immutable human decision."""
    run_path = Path(run).resolve()
    if not run_path.is_dir():
        raise OrientationSelectionError(f"proof run does not exist: {run_path}")
    candidate_id = _required_text(candidate_id, "candidate")
    author = _required_text(author, "author")
    rationale = _required_text(rationale, "rationale")
    selected_on = _required_text(selected_on, "selected-on")
    try:
        if date.fromisoformat(selected_on).isoformat() != selected_on:
            raise ValueError
    except ValueError as error:
        raise OrientationSelectionError(
            "selected-on must be an ISO calendar date (YYYY-MM-DD)"
        ) from error
    output = Path(output_root).resolve()
    if (supersedes is None) != (supersede_reason is None):
        raise OrientationSelectionError(
            "supersedes and supersede-reason must be provided together"
        )
    supersession: dict[str, str] | None = None
    predecessor: dict[str, Any] | None = None
    if supersedes is not None:
        supersedes = _required_text(supersedes, "supersedes")
        reason = _required_text(supersede_reason, "supersede-reason")
        predecessor_path = output / supersedes / "selection.json"
        predecessor = _load_json(predecessor_path, "superseded selection")
        predecessor_decision = predecessor.get("decision")
        if not isinstance(predecessor_decision, dict):
            raise OrientationSelectionError("superseded selection requires decision content")
        predecessor_digest = _content_sha256(predecessor_decision)
        if predecessor.get("selection_id") != supersedes:
            raise OrientationSelectionError("superseded selection identity disagrees with path")
        if predecessor.get("decision_sha256") != predecessor_digest:
            raise OrientationSelectionError("superseded decision checksum is invalid")
        if stable_id("orientation-selection", predecessor_decision) != supersedes:
            raise OrientationSelectionError("superseded selection identity is invalid")
        supersession = {
            "selection_id": supersedes,
            "decision_sha256": predecessor_digest,
            "selection_sha256": _sha256(predecessor_path),
            "reason": reason,
        }

    manifest_path = run_path / "manifest.json"
    manifest = _load_json(manifest_path, "proof manifest")
    if manifest.get("state") != "awaiting-human-selection":
        raise OrientationSelectionError("proof run is not awaiting human selection")
    identity = manifest.get("identity")
    if not isinstance(identity, dict):
        raise OrientationSelectionError("proof manifest requires identity content")
    proof_id = manifest.get("proof_id")
    if proof_id != stable_id("proof", identity):
        raise OrientationSelectionError("proof identity does not match proof content")
    if predecessor is not None:
        predecessor_decision = predecessor["decision"]
        predecessor_proof = predecessor_decision.get("proof")
        if not isinstance(predecessor_proof, dict) or predecessor_proof.get("proof_id") != proof_id:
            raise OrientationSelectionError(
                "superseded selection must reference the same proof run"
            )
    _verify_inventory(run_path, manifest)

    candidate_set_relative = "metadata/orientation-candidates.json"
    candidate_set_path = run_path / candidate_set_relative
    candidate_set = _load_json(candidate_set_path, "proof candidate set")
    candidate_set_id = candidate_set.get("candidate_set_id")
    expected_candidate_set_id = stable_id(
        "candidate-set", _candidate_set_identity_payload(candidate_set)
    )
    if candidate_set_id != expected_candidate_set_id:
        raise OrientationSelectionError("candidate-set identity does not match its content")
    if manifest.get("candidate_set_id") != candidate_set_id:
        raise OrientationSelectionError("proof and candidate-set identities disagree")
    candidates = candidate_set["candidates"]
    if any(not isinstance(item, dict) for item in candidates):
        raise OrientationSelectionError("candidate metadata entries must be objects")
    candidate_ids = [item.get("id") for item in candidates]
    if any(not isinstance(item, str) or not item for item in candidate_ids):
        raise OrientationSelectionError("candidate metadata requires nonblank IDs")
    if len(candidate_ids) != len(set(candidate_ids)):
        raise OrientationSelectionError("candidate IDs must be globally unique")
    candidate_order = manifest.get("candidate_order")
    if (
        not isinstance(candidate_order, list)
        or any(not isinstance(item, str) or not item for item in candidate_order)
        or len(candidate_order) != len(candidate_ids)
        or len(candidate_order) != len(set(candidate_order))
        or set(candidate_order) != set(candidate_ids)
    ):
        raise OrientationSelectionError(
            "candidate_order must contain every candidate ID exactly once"
        )
    if identity.get("candidate_order") != candidate_order:
        raise OrientationSelectionError("proof identity and candidate_order disagree")
    if identity.get("candidate_set_id") != candidate_set_id:
        raise OrientationSelectionError("proof identity and candidate-set identities disagree")
    if candidate_id not in candidate_order:
        raise OrientationSelectionError(f"candidate is not in proof run: {candidate_id}")
    matching_candidates = [item for item in candidates if item["id"] == candidate_id]
    if not matching_candidates:
        raise OrientationSelectionError(f"candidate is absent from candidate set: {candidate_id}")
    if len(matching_candidates) != 1:
        raise OrientationSelectionError("selected candidate ID must match exactly one candidate")
    candidate = matching_candidates[0]

    evidence_relative = f"candidates/{candidate_id}/evidence.json"
    evidence_path = run_path / evidence_relative
    evidence_matches: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted((run_path / "candidates").glob("*/evidence.json")):
        item = _load_json(path, "candidate evidence")
        item_candidate = item.get("candidate")
        if isinstance(item_candidate, dict) and item_candidate.get("id") == candidate_id:
            evidence_matches.append((path, item))
    if len(evidence_matches) != 1 or evidence_matches[0][0] != evidence_path:
        raise OrientationSelectionError(
            "selected candidate ID must match exactly one evidence directory"
        )
    evidence = evidence_matches[0][1]
    if evidence.get("candidate") != candidate:
        raise OrientationSelectionError("candidate evidence does not preserve candidate content")
    processing_evidence = evidence.get("processing_evidence")
    if not isinstance(processing_evidence, dict) or not isinstance(
        processing_evidence.get("geometry"), dict
    ):
        raise OrientationSelectionError("candidate evidence requires geometry content")
    metrics = evidence.get("metrics")
    if not isinstance(metrics, dict):
        raise OrientationSelectionError("candidate evidence requires metrics content")
    comparison_contract = evidence.get("comparison_contract")
    if not isinstance(comparison_contract, dict):
        raise OrientationSelectionError("candidate evidence requires a comparison contract")
    geometry = {
        "detector": comparison_contract.get("detector"),
        "detector_recipe_id": comparison_contract.get("detector_recipe_id"),
        "processing_geometry": processing_evidence["geometry"],
    }

    candidate_set_record = manifest["files"].get(candidate_set_relative)
    evidence_record = manifest["files"].get(evidence_relative)
    if not isinstance(candidate_set_record, dict) or not isinstance(evidence_record, dict):
        raise OrientationSelectionError("proof inventory omits selection evidence")

    decision = {
        "schema_version": 2,
        "kind": "human-orientation-selection",
        "selected_on": selected_on,
        "author": author,
        "rationale": rationale,
        "proof": {
            "proof_id": proof_id,
            "manifest_sha256": _sha256(manifest_path),
            "manifest_locator": "manifest.json",
            "tree_digest": proof_tree_digest(run_path),
        },
        "candidate_set": {
            "candidate_set_id": candidate_set_id,
            "candidate_set_sha256": candidate_set_record["sha256"],
            "candidate_set_locator": candidate_set_relative,
        },
        "selected_candidate": {
            "candidate_id": candidate_id,
            "candidate": candidate,
            "candidate_sha256": _content_sha256(candidate),
            "evidence_sha256": evidence_record["sha256"],
            "evidence_locator": evidence_relative,
            "geometry": geometry,
            "geometry_sha256": _content_sha256(geometry),
            "metrics": metrics,
            "metrics_sha256": _content_sha256(metrics),
        },
        "supersession": supersession,
    }
    decision_sha256 = _content_sha256(decision)
    selection_id = f"orientation-selection-{decision_sha256[:16]}"
    record = {
        "schema_version": 2,
        "selection_id": selection_id,
        "decision_sha256": decision_sha256,
        "decision": decision,
        "external_locators": {"proof_run": str(run_path)},
    }
    output.mkdir(parents=True, exist_ok=True)
    target = output / selection_id
    if target.exists():
        raise SelectionExistsError(f"selection artifact already exists: {selection_id}")
    for _, existing in _selection_records(output):
        existing_decision = existing.get("decision")
        if (
            supersession is None
            and isinstance(existing_decision, dict)
            and isinstance(existing_decision.get("proof"), dict)
            and existing_decision["proof"].get("proof_id") == proof_id
        ):
            raise OrientationSelectionError(
                "proof already has a selection; use --supersedes and --supersede-reason"
            )
    staging = Path(tempfile.mkdtemp(prefix=f".{selection_id}-", dir=output))
    try:
        (staging / "selection.json").write_text(canonical_json(record), encoding="utf-8")
        os.rename(staging, target)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return OrientationSelectionResult(selection_id, target, target / "selection.json")
