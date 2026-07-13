"""Immutable, content-addressed human orientation selections."""

from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import re
import shutil
import stat
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any

from kikuchi_lab.model.identity import canonical_json, stable_id


LEGACY_PROOF_TREE_DIGEST_CONTRACT = {
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
PROOF_TREE_DIGEST_CONTRACT = {
    "schema_version": 2,
    "algorithm": "sha256",
    "file_inclusion": (
        "all regular files recursively beneath the proof root, including manifest.json; "
        "any symbolic link or non-regular entry is an error"
    ),
    "exclusions": [],
    "entry_fields": ["relative_posix_path", "sha256", "bytes"],
    "ordering": "ascending Unicode code-point order of relative_posix_path",
    "serialization": "kikuchi-lab canonical JSON encoded as UTF-8 without a newline",
    "digest_payload": "canonical JSON object with contract and ordered entries fields",
}
_SELECTION_ID = re.compile(r"^orientation-selection-[0-9a-f]{16}$")
_PROOF_ID = re.compile(r"^proof-[0-9a-f]{16}$")
_CANDIDATE_SET_ID = re.compile(r"^candidate-set-[0-9a-f]{16}$")
_CANDIDATE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)+$")
_RECIPE_ID = re.compile(r"^recipe-[0-9a-f]{16}$")


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


def _proof_root(path: str | Path) -> Path:
    root = Path(os.path.abspath(os.fspath(path)))
    try:
        mode = root.lstat().st_mode
    except OSError as error:
        raise OrientationSelectionError(f"proof run does not exist: {root}") from error
    if stat.S_ISLNK(mode):
        raise OrientationSelectionError("proof root cannot be a symbolic link")
    if not stat.S_ISDIR(mode):
        raise OrientationSelectionError(f"proof run does not exist: {root}")
    return root


def _proof_files(root: Path) -> list[Path]:
    files: list[Path] = []

    def visit(directory: Path) -> None:
        for child in sorted(directory.iterdir(), key=lambda item: item.name):
            mode = child.lstat().st_mode
            relative = child.relative_to(root).as_posix()
            if stat.S_ISLNK(mode):
                raise OrientationSelectionError(
                    f"proof tree contains a symbolic link: {relative}"
                )
            if stat.S_ISDIR(mode):
                visit(child)
            elif stat.S_ISREG(mode):
                files.append(child)
            else:
                raise OrientationSelectionError(
                    f"proof tree contains a non-regular entry: {relative}"
                )

    visit(root)
    return sorted(files, key=lambda path: path.relative_to(root).as_posix())


def _relative_locator(value: Any, label: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise OrientationSelectionError(f"{label} must be a safe relative POSIX path")
    locator = PurePosixPath(value)
    if (
        locator.is_absolute()
        or value != locator.as_posix()
        or any(part in ("", ".", "..") for part in locator.parts)
    ):
        raise OrientationSelectionError(f"{label} must be a safe relative POSIX path")
    return locator


def _proof_locator(root: Path, value: Any, label: str) -> Path:
    locator = _relative_locator(value, label)
    current = root
    for part in locator.parts:
        current = current / part
        try:
            mode = current.lstat().st_mode
        except OSError as error:
            raise OrientationSelectionError(f"{label} is unavailable: {value}") from error
        if stat.S_ISLNK(mode):
            raise OrientationSelectionError(
                f"{label} contains a symbolic link: {value}"
            )
    resolved_root = root.resolve(strict=True)
    resolved = current.resolve(strict=True)
    if not resolved.is_relative_to(resolved_root):
        raise OrientationSelectionError(f"{label} escapes the proof root: {value}")
    return current


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OrientationSelectionError(f"{field} must be nonblank text")
    return value.strip()


def _require_exact_fields(mapping: dict[str, Any], expected: set[str], label: str) -> None:
    if set(mapping) != expected:
        raise OrientationSelectionError(f"{label} fields differ from schema")


def _load_json(path: Path, label: str) -> dict[str, Any]:
    def reject_nonfinite(constant: str) -> None:
        raise ValueError(f"non-finite JSON constant: {constant}")

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"), parse_constant=reject_nonfinite
        )
    except OSError as error:
        raise OrientationSelectionError(f"{label} is unavailable: {path}") from error
    except ValueError as error:
        raise OrientationSelectionError(f"{label} is not valid JSON: {path}") from error
    if not isinstance(value, dict):
        raise OrientationSelectionError(f"{label} must contain a JSON object")
    return value


def _validate_sha256(value: Any, label: str) -> str:
    message = f"{label} must be a nonzero lowercase SHA-256"
    if not isinstance(value, str) or len(value) != 64 or value == "0" * 64:
        raise OrientationSelectionError(message)
    try:
        int(value, 16)
    except ValueError as error:
        raise OrientationSelectionError(message) from error
    if value != value.lower():
        raise OrientationSelectionError(message)
    return value


def _verify_inventory(run: Path, manifest: dict[str, Any]) -> None:
    _proof_files(run)
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise OrientationSelectionError("proof manifest requires a nonempty files inventory")
    for relative, record in files.items():
        if not isinstance(record, dict):
            raise OrientationSelectionError(f"proof inventory record is invalid: {relative}")
        path = _proof_locator(run, relative, "proof inventory path")
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


def _proof_tree_digest_with_contract(
    run: str | Path, contract: dict[str, Any]
) -> dict[str, Any]:
    root = _proof_root(run)
    paths = _proof_files(root)
    entries = [
        {
            "relative_posix_path": path.relative_to(root).as_posix(),
            "sha256": _sha256(path),
            "bytes": path.stat().st_size,
        }
        for path in paths
    ]
    payload = {"contract": contract, "entries": entries}
    return {
        "contract": contract,
        "file_count": len(entries),
        "sha256": _content_sha256(payload),
    }


def proof_tree_digest(run: str | Path) -> dict[str, Any]:
    """Return the path-stable digest contract and value for a sealed proof tree."""
    return _proof_tree_digest_with_contract(run, PROOF_TREE_DIGEST_CONTRACT)


def _selection_records(output_root: Path) -> list[tuple[Path, dict[str, Any]]]:
    records: list[tuple[Path, dict[str, Any]]] = []
    if not output_root.is_dir():
        return records
    for path in sorted(output_root.glob("orientation-selection-*/selection.json")):
        records.append((path, load_orientation_selection(path)))
    return records


def _validate_linear_predecessor(
    records: list[tuple[Path, dict[str, Any]]],
    *,
    proof_id: str,
    supersedes: str | None,
) -> None:
    same_proof = {
        record["selection_id"]: (path, record)
        for path, record in records
        if record["decision"]["proof"]["proof_id"] == proof_id
    }
    if not same_proof:
        if supersedes is not None:
            raise OrientationSelectionError(
                "superseded selection must be the current unique leaf"
            )
        return
    successors: dict[str, list[str]] = {selection_id: [] for selection_id in same_proof}
    for selection_id, (_path, record) in same_proof.items():
        supersession = record["decision"]["supersession"]
        if supersession is None:
            continue
        predecessor_id = supersession["selection_id"]
        if predecessor_id not in same_proof:
            raise OrientationSelectionError(
                "selection lineage predecessor is absent from the proof lineage"
            )
        predecessor_path, predecessor = same_proof[predecessor_id]
        if supersession["decision_sha256"] != predecessor["decision_sha256"]:
            raise OrientationSelectionError(
                "selection lineage predecessor decision checksum disagrees"
            )
        if supersession["selection_sha256"] != _sha256(predecessor_path):
            raise OrientationSelectionError(
                "selection lineage predecessor artifact checksum disagrees"
            )
        successors[predecessor_id].append(selection_id)
    if any(len(items) > 1 for items in successors.values()):
        raise OrientationSelectionError("selection lineage contains a supersession fork")
    leaves = [selection_id for selection_id, items in successors.items() if not items]
    if len(leaves) != 1:
        raise OrientationSelectionError("selection lineage must have one current unique leaf")
    if supersedes != leaves[0]:
        raise OrientationSelectionError(
            "superseded selection must be the current unique leaf"
        )


@contextmanager
def _proof_selection_lock(output_root: Path, proof_id: str):
    """Serialize lineage validation and publication for one proof across processes."""
    lock_root = output_root / ".locks"
    lock_root.mkdir(parents=True, exist_ok=True)
    lock_path = lock_root / f"{proof_id}.lock"
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _validate_external_selection_evidence(
    record: dict[str, Any], *, schema_version: int
) -> None:
    decision = record["decision"]
    proof = decision["proof"]
    candidate_set_record = decision["candidate_set"]
    selected = decision["selected_candidate"]
    proof_root = _proof_root(record["external_locators"]["proof_run"])
    _proof_files(proof_root)

    manifest_path = _proof_locator(
        proof_root, proof["manifest_locator"], "proof manifest locator"
    )
    if _sha256(manifest_path) != proof["manifest_sha256"]:
        raise OrientationSelectionError("external proof manifest checksum disagrees")
    manifest = _load_json(manifest_path, "external proof manifest")
    if manifest.get("proof_id") != proof["proof_id"]:
        raise OrientationSelectionError("external proof identity disagrees")

    candidate_set_path = _proof_locator(
        proof_root,
        candidate_set_record["candidate_set_locator"],
        "candidate-set locator",
    )
    if _sha256(candidate_set_path) != candidate_set_record["candidate_set_sha256"]:
        raise OrientationSelectionError("external candidate-set checksum disagrees")
    candidate_set = _load_json(candidate_set_path, "external candidate set")
    if candidate_set.get("candidate_set_id") != candidate_set_record["candidate_set_id"]:
        raise OrientationSelectionError("external candidate-set identity disagrees")
    candidates = candidate_set.get("candidates")
    if not isinstance(candidates, list):
        raise OrientationSelectionError("external candidate set requires candidates")
    candidate_matches = [
        candidate
        for candidate in candidates
        if isinstance(candidate, dict) and candidate.get("id") == selected["candidate_id"]
    ]
    if len(candidate_matches) != 1 or candidate_matches[0] != selected["candidate"]:
        raise OrientationSelectionError("proof candidate evidence disagrees with selection")

    evidence_path = _proof_locator(
        proof_root, selected["evidence_locator"], "candidate evidence locator"
    )
    if _sha256(evidence_path) != selected["evidence_sha256"]:
        raise OrientationSelectionError("external candidate evidence checksum disagrees")
    evidence = _load_json(evidence_path, "external candidate evidence")
    if evidence.get("candidate") != selected["candidate"]:
        raise OrientationSelectionError("proof candidate evidence disagrees with selection")
    comparison = evidence.get("comparison_contract")
    processing = evidence.get("processing_evidence")
    if not isinstance(comparison, dict) or not isinstance(processing, dict):
        raise OrientationSelectionError("external candidate evidence is incomplete")
    external_geometry = {
        "detector": comparison.get("detector"),
        "detector_recipe_id": comparison.get("detector_recipe_id"),
        "processing_geometry": processing.get("geometry"),
    }
    if external_geometry != selected["geometry"]:
        raise OrientationSelectionError("proof geometry evidence disagrees with selection")
    if evidence.get("metrics") != selected["metrics"]:
        raise OrientationSelectionError("proof metrics evidence disagrees with selection")

    if schema_version >= 2:
        contract = (
            LEGACY_PROOF_TREE_DIGEST_CONTRACT
            if schema_version == 2
            else PROOF_TREE_DIGEST_CONTRACT
        )
        if _proof_tree_digest_with_contract(proof_root, contract) != proof["tree_digest"]:
            raise OrientationSelectionError("external proof tree digest disagrees")


def _write_selection_file(path: Path, payload: bytes) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
        0o600,
    )
    try:
        remaining = memoryview(payload)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise OSError("selection publication made no write progress")
            remaining = remaining[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _rename_selection(source: Path, target: Path) -> None:
    os.rename(source, target)


def _publish_selection_record(
    *, output: Path, target: Path, selection_id: str, record: dict[str, Any]
) -> None:
    staging = Path(tempfile.mkdtemp(prefix=f".{selection_id}-", dir=output))
    published = False
    try:
        payload = canonical_json(record).encode("utf-8")
        _write_selection_file(staging / "selection.json", payload)
        _fsync_directory(staging)
        _rename_selection(staging, target)
        published = True
        _fsync_directory(output)
    except BaseException:
        if not published:
            shutil.rmtree(staging, ignore_errors=True)
        raise


def load_orientation_selection(path: str | Path) -> dict[str, Any]:
    """Load and validate one content-addressed selection artifact."""
    selection_path = Path(path).resolve()
    record = _load_json(selection_path, "orientation selection")
    schema_version = record.get("schema_version")
    if type(schema_version) is not int or schema_version not in (1, 2, 3):
        raise OrientationSelectionError("selection schema_version must be integer 1, 2, or 3")
    _require_exact_fields(
        record,
        {
            "schema_version",
            "selection_id",
            "decision_sha256",
            "decision",
            "external_locators",
        },
        "selection",
    )
    decision = record.get("decision")
    if not isinstance(decision, dict):
        raise OrientationSelectionError("selection requires decision content")
    _require_exact_fields(
        decision,
        {
            "schema_version",
            "kind",
            "selected_on",
            "author",
            "rationale",
            "proof",
            "candidate_set",
            "selected_candidate",
            "supersession",
        },
        "decision",
    )
    decision_sha256 = _content_sha256(decision)
    if record.get("decision_sha256") != decision_sha256:
        raise OrientationSelectionError("selection decision checksum is invalid")
    selection_id = record.get("selection_id")
    if not isinstance(selection_id, str) or not _SELECTION_ID.fullmatch(selection_id):
        raise OrientationSelectionError("selection identity is invalid")
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
    proof_fields = {"proof_id", "manifest_sha256", "manifest_locator"}
    if schema_version >= 2:
        proof_fields.add("tree_digest")
    _require_exact_fields(proof, proof_fields, "proof")
    if not _PROOF_ID.fullmatch(proof["proof_id"]):
        raise OrientationSelectionError("proof identity is invalid")
    _validate_sha256(proof.get("manifest_sha256"), "proof manifest_sha256")
    if _relative_locator(proof.get("manifest_locator"), "proof manifest locator").as_posix() != (
        "manifest.json"
    ):
        raise OrientationSelectionError("proof manifest locator must be manifest.json")
    if schema_version >= 2:
        tree_digest = proof.get("tree_digest")
        if not isinstance(tree_digest, dict):
            raise OrientationSelectionError("schema 2 decision requires a proof tree digest")
        _require_exact_fields(
            tree_digest, {"contract", "file_count", "sha256"}, "proof tree digest"
        )
        expected_contract = (
            LEGACY_PROOF_TREE_DIGEST_CONTRACT
            if schema_version == 2
            else PROOF_TREE_DIGEST_CONTRACT
        )
        if tree_digest.get("contract") != expected_contract:
            raise OrientationSelectionError("proof tree digest contract is invalid")
        if type(tree_digest.get("file_count")) is not int or tree_digest["file_count"] <= 0:
            raise OrientationSelectionError("proof tree digest file_count must be positive")
        _validate_sha256(tree_digest.get("sha256"), "proof tree digest sha256")
    candidate_set = decision.get("candidate_set")
    if not isinstance(candidate_set, dict) or not isinstance(
        candidate_set.get("candidate_set_id"), str
    ):
        raise OrientationSelectionError("decision requires a candidate-set identity")
    _require_exact_fields(
        candidate_set,
        {"candidate_set_id", "candidate_set_sha256", "candidate_set_locator"},
        "candidate-set",
    )
    if not _CANDIDATE_SET_ID.fullmatch(candidate_set["candidate_set_id"]):
        raise OrientationSelectionError("candidate-set identity is invalid")
    _validate_sha256(candidate_set.get("candidate_set_sha256"), "candidate-set sha256")
    if (
        _relative_locator(
            candidate_set.get("candidate_set_locator"), "candidate-set locator"
        ).as_posix()
        != "metadata/orientation-candidates.json"
    ):
        raise OrientationSelectionError(
            "candidate-set locator must be metadata/orientation-candidates.json"
        )

    selected = decision.get("selected_candidate")
    if not isinstance(selected, dict):
        raise OrientationSelectionError("decision requires selected-candidate content")
    _require_exact_fields(
        selected,
        {
            "candidate_id",
            "candidate",
            "candidate_sha256",
            "evidence_sha256",
            "evidence_locator",
            "geometry",
            "geometry_sha256",
            "metrics",
            "metrics_sha256",
        },
        "selected candidate",
    )
    candidate = selected.get("candidate")
    if not isinstance(candidate, dict) or selected.get("candidate_id") != candidate.get("id"):
        raise OrientationSelectionError("selected candidate identity is invalid")
    _require_exact_fields(
        candidate,
        {
            "id",
            "name",
            "orientation",
            "bunge_phi1_deg",
            "zone_axis_uvw",
            "zone_axis_intent",
            "composition_intent",
            "zone_axis_label",
        },
        "candidate",
    )
    if not isinstance(selected["candidate_id"], str) or not _CANDIDATE_ID.fullmatch(
        selected["candidate_id"]
    ):
        raise OrientationSelectionError("selected candidate identity is invalid")
    orientation = candidate.get("orientation")
    if not isinstance(orientation, dict):
        raise OrientationSelectionError("selected candidate requires orientation content")
    _require_exact_fields(
        orientation, {"angle_units", "euler_bunge_deg", "frame"}, "orientation"
    )
    eulers = orientation.get("euler_bunge_deg")
    if (
        not isinstance(eulers, list)
        or len(eulers) != 3
        or any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            for value in eulers
        )
    ):
        raise OrientationSelectionError(
            "selected candidate orientation requires three finite Bunge angles"
        )
    if orientation.get("angle_units") != "degree" or orientation.get("frame") != (
        "crystal_to_sample"
    ):
        raise OrientationSelectionError(
            "selected candidate orientation requires degree crystal_to_sample semantics"
        )
    phi1, phi, phi2 = (float(value) for value in eulers)
    if not (0 <= phi1 < 360 and 0 <= phi <= 180 and 0 <= phi2 < 360):
        raise OrientationSelectionError(
            "selected candidate orientation is outside canonical Bunge ranges"
        )
    declared_phi1 = candidate.get("bunge_phi1_deg")
    if (
        isinstance(declared_phi1, bool)
        or not isinstance(declared_phi1, (int, float))
        or not math.isfinite(float(declared_phi1))
        or float(declared_phi1) != phi1
    ):
        raise OrientationSelectionError(
            "selected candidate bunge_phi1_deg must match its orientation"
        )
    zone_axis = candidate.get("zone_axis_uvw")
    if (
        not isinstance(zone_axis, list)
        or len(zone_axis) != 3
        or any(type(value) is not int for value in zone_axis)
        or not any(zone_axis)
    ):
        raise OrientationSelectionError("selected candidate requires a nonzero zone axis")
    for field in ("name", "zone_axis_intent", "composition_intent", "zone_axis_label"):
        _required_text(candidate.get(field), f"candidate {field}")
    evidence_locator = _relative_locator(
        selected.get("evidence_locator"), "candidate evidence locator"
    ).as_posix()
    if evidence_locator != f"candidates/{selected['candidate_id']}/evidence.json":
        raise OrientationSelectionError(
            "candidate evidence locator must agree with the selected candidate ID"
        )
    if selected.get("candidate_sha256") != _content_sha256(candidate):
        raise OrientationSelectionError("selected candidate checksum is invalid")
    _validate_sha256(selected.get("evidence_sha256"), "candidate evidence_sha256")
    geometry = selected.get("geometry")
    if not isinstance(geometry, dict) or set(geometry) != {
        "detector",
        "detector_recipe_id",
        "processing_geometry",
    }:
        raise OrientationSelectionError("selected candidate requires substantive geometry")
    detector = geometry["detector"]
    detector_recipe_id = geometry["detector_recipe_id"]
    processing_geometry = geometry["processing_geometry"]
    if (
        not isinstance(detector, dict)
        or not detector
        or not isinstance(detector_recipe_id, str)
        or not _RECIPE_ID.fullmatch(detector_recipe_id)
        or not isinstance(processing_geometry, dict)
        or set(processing_geometry)
        != {"source_shape", "output_shape", "supersampling", "physical_extent_um"}
    ):
        raise OrientationSelectionError("selected candidate requires substantive geometry")
    for shape_field in ("source_shape", "output_shape"):
        shape = processing_geometry[shape_field]
        if (
            not isinstance(shape, list)
            or len(shape) != 2
            or any(type(value) is not int or value <= 0 for value in shape)
        ):
            raise OrientationSelectionError("selected candidate requires substantive geometry")
    supersampling = processing_geometry["supersampling"]
    extent = processing_geometry["physical_extent_um"]
    if (
        type(supersampling) is not int
        or supersampling <= 0
        or not isinstance(extent, list)
        or len(extent) != 2
        or any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or float(value) <= 0
            for value in extent
        )
    ):
        raise OrientationSelectionError("selected candidate requires substantive geometry")
    if selected.get("geometry_sha256") != _content_sha256(geometry):
        raise OrientationSelectionError("selected geometry checksum is invalid")
    metrics = selected.get("metrics")
    if (
        not isinstance(metrics, dict)
        or set(metrics) != {"schema_version", "raw", "processed"}
        or type(metrics["schema_version"]) is not int
        or metrics["schema_version"] != 1
        or not isinstance(metrics["raw"], dict)
        or not metrics["raw"]
        or not isinstance(metrics["processed"], dict)
        or not metrics["processed"]
    ):
        raise OrientationSelectionError("selected candidate requires substantive metrics")
    if selected.get("metrics_sha256") != _content_sha256(metrics):
        raise OrientationSelectionError("selected metrics checksum is invalid")
    supersession = decision.get("supersession")
    if supersession is not None:
        if not isinstance(supersession, dict):
            raise OrientationSelectionError("decision supersession must be null or an object")
        _require_exact_fields(
            supersession,
            {"selection_id", "decision_sha256", "selection_sha256", "reason"},
            "supersession",
        )
        superseded_id = _required_text(
            supersession.get("selection_id"), "superseded selection-id"
        )
        if not _SELECTION_ID.fullmatch(superseded_id):
            raise OrientationSelectionError("superseded selection identity is invalid")
        _required_text(supersession.get("reason"), "supersede-reason")
        superseded_decision_sha256 = _validate_sha256(
            supersession.get("decision_sha256"), "superseded decision_sha256"
        )
        if superseded_id != f"orientation-selection-{superseded_decision_sha256[:16]}":
            raise OrientationSelectionError(
                "superseded selection identity does not match decision checksum"
            )
        _validate_sha256(supersession.get("selection_sha256"), "superseded selection_sha256")
    external_locators = record.get("external_locators")
    if not isinstance(external_locators, dict):
        raise OrientationSelectionError("selection requires external locators")
    _require_exact_fields(external_locators, {"proof_run"}, "external locators")
    external_proof_run = _required_text(
        external_locators.get("proof_run"), "external proof-run locator"
    )
    if not Path(external_proof_run).is_absolute():
        raise OrientationSelectionError("external proof-run locator must be absolute")
    _validate_external_selection_evidence(record, schema_version=schema_version)
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
    run_path = _proof_root(run)
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

    manifest_path = _proof_locator(run_path, "manifest.json", "proof manifest")
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
    candidate_set_path = _proof_locator(
        run_path, candidate_set_relative, "proof candidate set"
    )
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
    evidence_path = _proof_locator(run_path, evidence_relative, "candidate evidence")
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
        "schema_version": 3,
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
        "schema_version": 3,
        "selection_id": selection_id,
        "decision_sha256": decision_sha256,
        "decision": decision,
        "external_locators": {"proof_run": str(run_path)},
    }
    output.mkdir(parents=True, exist_ok=True)
    target = output / selection_id
    with _proof_selection_lock(output, proof_id):
        if target.exists():
            raise SelectionExistsError(f"selection artifact already exists: {selection_id}")
        _validate_linear_predecessor(
            _selection_records(output), proof_id=proof_id, supersedes=supersedes
        )
        _publish_selection_record(
            output=output,
            target=target,
            selection_id=selection_id,
            record=record,
        )
    return OrientationSelectionResult(selection_id, target, target / "selection.json")
