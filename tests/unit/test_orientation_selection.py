from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import kikuchi_lab.orientations.selection as selection_module
from kikuchi_lab.cli.main import main
from kikuchi_lab.model.identity import canonical_json, stable_id
import pytest

from kikuchi_lab.orientations.selection import (
    OrientationSelectionError,
    SelectionExistsError,
    create_orientation_selection,
    load_orientation_selection,
    proof_tree_digest,
    verify_orientation_selection,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(value), encoding="utf-8")


def _proof_bundle(tmp_path: Path) -> Path:
    run = tmp_path / "runs" / "proof-fixture"
    candidate = {
        "id": "fo-011-phi1-045",
        "name": "bc mixed axis phi1 045",
        "orientation": {
            "angle_units": "degree",
            "euler_bunge_deg": [45.0, 51.50414783, 0.0],
            "frame": "crystal_to_sample",
        },
        "bunge_phi1_deg": 45.0,
        "zone_axis_uvw": [0, 1, 1],
        "zone_axis_intent": "Center [011] on sample ND.",
        "composition_intent": "Diagonal crossing.",
        "zone_axis_label": "[011]",
    }
    candidate_set_identity = {
        "schema_version": 1,
        "phase": "forsterite (Mg2SiO4)",
        "space_group": "Pnma (No. 62, standard setting)",
        "point_group": "mmm",
        "orientation_convention": "active crystal-to-sample Bunge ZXZ Euler angles in degrees",
        "phi1_semantics": "explicit first Bunge Euler angle",
        "equivalence_tolerance_deg": 0.01,
        "generation_rationale": "Bounded human-review set.",
        "exhaustive": False,
        "lattice_abc_angstrom": [10.207, 5.98, 4.756],
        "candidates": [{key: value for key, value in candidate.items() if key != "zone_axis_label"}],
    }
    candidate_set_id = stable_id("candidate-set", candidate_set_identity)
    candidate_set = {
        "candidate_set_id": candidate_set_id,
        **candidate_set_identity,
        "candidates": [candidate],
    }
    evidence = {
        "schema_version": 1,
        "candidate": candidate,
        "comparison_contract": {
            "detector_recipe_id": "recipe-0123456789abcdef",
            "detector": {"shape": [180, 240], "pc": {"x": 0.5, "y": 0.72, "z": 0.6}},
        },
        "processing_evidence": {
            "geometry": {
                "source_shape": [360, 480],
                "output_shape": [180, 240],
                "supersampling": 2,
                "physical_extent_um": [9000.0, 12000.0],
            }
        },
        "metrics": {
            "schema_version": 1,
            "raw": {"gradient": {"mean": 1.0}},
            "processed": {"gradient": {"mean": 2.0}},
        },
    }
    candidate_set_path = run / "metadata" / "orientation-candidates.json"
    evidence_path = run / "candidates" / candidate["id"] / "evidence.json"
    raw_path = run / "candidates" / candidate["id"] / "raw.bin"
    _write_json(candidate_set_path, candidate_set)
    _write_json(evidence_path, evidence)
    raw_path.write_bytes(b"sealed proof pixels")
    files = {}
    for path in (candidate_set_path, evidence_path, raw_path):
        relative = path.relative_to(run).as_posix()
        files[relative] = {"bytes": path.stat().st_size, "sha256": _sha256(path)}
    identity = {
        "candidate_order": [candidate["id"]],
        "candidate_set_id": candidate_set_id,
        "comparison_contract": evidence["comparison_contract"],
    }
    manifest = {
        "schema_version": 3,
        "proof_id": stable_id("proof", identity),
        "state": "awaiting-human-selection",
        "identity": identity,
        "candidate_order": [candidate["id"]],
        "candidate_set_id": candidate_set_id,
        "files": files,
    }
    _write_json(run / "manifest.json", manifest)
    return run


def _tree_checksums(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): _sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _reseal_duplicate_candidate_proof(run: Path) -> None:
    candidate_set_path = run / "metadata/orientation-candidates.json"
    candidate_set = json.loads(candidate_set_path.read_text())
    duplicate = deepcopy(candidate_set["candidates"][0])
    duplicate["orientation"]["euler_bunge_deg"][0] = 46.0
    duplicate["bunge_phi1_deg"] = 46.0
    candidate_set["candidates"].append(duplicate)
    identity_payload = {
        key: value for key, value in candidate_set.items() if key != "candidate_set_id"
    }
    identity_payload["candidates"] = [
        {key: value for key, value in candidate.items() if key != "zone_axis_label"}
        for candidate in candidate_set["candidates"]
    ]
    candidate_set_id = stable_id("candidate-set", identity_payload)
    candidate_set["candidate_set_id"] = candidate_set_id
    _write_json(candidate_set_path, candidate_set)

    manifest_path = run / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    repeated_order = [candidate["id"] for candidate in candidate_set["candidates"]]
    manifest["candidate_order"] = repeated_order
    manifest["candidate_set_id"] = candidate_set_id
    manifest["identity"]["candidate_order"] = repeated_order
    manifest["identity"]["candidate_set_id"] = candidate_set_id
    relative = candidate_set_path.relative_to(run).as_posix()
    manifest["files"][relative] = {
        "bytes": candidate_set_path.stat().st_size,
        "sha256": _sha256(candidate_set_path),
    }
    manifest["proof_id"] = stable_id("proof", manifest["identity"])
    _write_json(manifest_path, manifest)


def _write_self_consistent_selection(
    original_path: Path, record: dict[str, object]
) -> Path:
    decision = record["decision"]
    decision_sha256 = hashlib.sha256(
        canonical_json(decision).encode("utf-8")
    ).hexdigest()
    selection_id = f"orientation-selection-{decision_sha256[:16]}"
    record["decision_sha256"] = decision_sha256
    record["selection_id"] = selection_id
    rewritten = original_path.parent.parent / selection_id / "selection.json"
    _write_json(rewritten, record)
    return rewritten


def test_selection_is_content_addressed_and_references_sealed_evidence(tmp_path: Path) -> None:
    proof = _proof_bundle(tmp_path)
    before = _tree_checksums(proof)

    result = create_orientation_selection(
        run=proof,
        candidate_id="fo-011-phi1-045",
        author="Z",
        rationale="Balanced radial bands and strong clarity-forward potential.",
        selected_on="2026-07-13",
        output_root=tmp_path / "decisions",
    )

    record = json.loads(result.selection_path.read_text())
    assert result.selection_id == stable_id("orientation-selection", record["decision"])
    assert record["selection_id"] == result.selection_id
    assert record["decision_sha256"] == hashlib.sha256(
        canonical_json(record["decision"]).encode("utf-8")
    ).hexdigest()
    assert record["decision"]["proof"]["proof_id"].startswith("proof-")
    assert record["decision"]["proof"]["manifest_sha256"] == _sha256(
        proof / "manifest.json"
    )
    selected = record["decision"]["selected_candidate"]
    assert selected["candidate_id"] == "fo-011-phi1-045"
    assert selected["candidate_sha256"] == hashlib.sha256(
        canonical_json(selected["candidate"]).encode("utf-8")
    ).hexdigest()
    assert selected["evidence_sha256"] == _sha256(
        proof / "candidates/fo-011-phi1-045/evidence.json"
    )
    assert len(selected["geometry_sha256"]) == 64
    assert len(selected["metrics_sha256"]) == 64
    assert _tree_checksums(proof) == before


def test_selection_rejects_sealed_duplicate_candidate_ids_before_choice(
    tmp_path: Path,
) -> None:
    proof = _proof_bundle(tmp_path)
    _reseal_duplicate_candidate_proof(proof)

    with pytest.raises(OrientationSelectionError, match="candidate IDs must be globally unique"):
        create_orientation_selection(
            run=proof,
            candidate_id="fo-011-phi1-045",
            author="Z",
            rationale="A human rationale.",
            selected_on="2026-07-13",
            output_root=tmp_path / "decisions",
        )


def test_proof_tree_digest_contract_is_exact_and_recomputable(tmp_path: Path) -> None:
    proof = _proof_bundle(tmp_path)
    expected_contract = {
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
    entries = [
        {
            "relative_posix_path": path.relative_to(proof).as_posix(),
            "sha256": _sha256(path),
            "bytes": path.stat().st_size,
        }
        for path in sorted(
            (path for path in proof.rglob("*") if path.is_file() and not path.is_symlink()),
            key=lambda path: path.relative_to(proof).as_posix(),
        )
    ]
    expected_sha256 = hashlib.sha256(
        canonical_json({"contract": expected_contract, "entries": entries}).encode("utf-8")
    ).hexdigest()

    observed = proof_tree_digest(proof)

    assert observed == {
        "contract": expected_contract,
        "file_count": len(entries),
        "sha256": expected_sha256,
    }


def test_selection_schema_records_the_recomputable_proof_tree_digest(tmp_path: Path) -> None:
    proof = _proof_bundle(tmp_path)

    result = create_orientation_selection(
        run=proof,
        candidate_id="fo-011-phi1-045",
        author="Z",
        rationale="A human rationale.",
        selected_on="2026-07-13",
        output_root=tmp_path / "decisions",
    )

    record = load_orientation_selection(result.selection_path)
    assert record["schema_version"] == 3
    assert record["decision"]["schema_version"] == 3
    assert record["decision"]["proof"]["tree_digest"] == proof_tree_digest(proof)


def test_selection_requires_exactly_one_evidence_directory_for_selected_id(
    tmp_path: Path,
) -> None:
    proof = _proof_bundle(tmp_path)
    source = proof / "candidates/fo-011-phi1-045/evidence.json"
    duplicate = proof / "candidates/duplicate-folder/evidence.json"
    duplicate.parent.mkdir(parents=True)
    shutil.copyfile(source, duplicate)
    manifest_path = proof / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    relative = duplicate.relative_to(proof).as_posix()
    manifest["files"][relative] = {
        "bytes": duplicate.stat().st_size,
        "sha256": _sha256(duplicate),
    }
    _write_json(manifest_path, manifest)

    with pytest.raises(
        OrientationSelectionError,
        match="selected candidate ID must match exactly one evidence directory",
    ):
        create_orientation_selection(
            run=proof,
            candidate_id="fo-011-phi1-045",
            author="Z",
            rationale="A human rationale.",
            selected_on="2026-07-13",
            output_root=tmp_path / "decisions",
        )


def test_selection_rejects_external_candidate_file_symlink(tmp_path: Path) -> None:
    proof = _proof_bundle(tmp_path)
    evidence = proof / "candidates/fo-011-phi1-045/evidence.json"
    external = tmp_path / "external-evidence.json"
    shutil.copyfile(evidence, external)
    evidence.unlink()
    evidence.symlink_to(external)

    with pytest.raises(OrientationSelectionError, match="symbolic link"):
        create_orientation_selection(
            run=proof,
            candidate_id="fo-011-phi1-045",
            author="Z",
            rationale="A human rationale.",
            selected_on="2026-07-13",
            output_root=tmp_path / "decisions",
        )


def test_selection_rejects_external_candidate_directory_symlink(tmp_path: Path) -> None:
    proof = _proof_bundle(tmp_path)
    candidate_dir = proof / "candidates/fo-011-phi1-045"
    external = tmp_path / "external-candidate"
    shutil.move(candidate_dir, external)
    candidate_dir.symlink_to(external, target_is_directory=True)

    with pytest.raises(OrientationSelectionError, match="symbolic link"):
        create_orientation_selection(
            run=proof,
            candidate_id="fo-011-phi1-045",
            author="Z",
            rationale="A human rationale.",
            selected_on="2026-07-13",
            output_root=tmp_path / "decisions",
        )


@pytest.mark.parametrize("declared_order", [[], ["fo-011-phi1-045", "fo-011-phi1-045"]])
def test_selection_requires_candidate_order_to_cover_each_candidate_once(
    tmp_path: Path, declared_order: list[str]
) -> None:
    proof = _proof_bundle(tmp_path)
    manifest_path = proof / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["candidate_order"] = declared_order
    manifest["identity"]["candidate_order"] = declared_order
    manifest["proof_id"] = stable_id("proof", manifest["identity"])
    _write_json(manifest_path, manifest)

    with pytest.raises(
        OrientationSelectionError,
        match="candidate_order must contain every candidate ID exactly once",
    ):
        create_orientation_selection(
            run=proof,
            candidate_id="fo-011-phi1-045",
            author="Z",
            rationale="A human rationale.",
            selected_on="2026-07-13",
            output_root=tmp_path / "decisions",
        )


def test_selection_normalizes_non_text_candidate_order_entries(tmp_path: Path) -> None:
    proof = _proof_bundle(tmp_path)
    manifest_path = proof / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["candidate_order"] = [{"not": "an ID"}]
    manifest["identity"]["candidate_order"] = [{"not": "an ID"}]
    manifest["proof_id"] = stable_id("proof", manifest["identity"])
    _write_json(manifest_path, manifest)

    with pytest.raises(
        OrientationSelectionError,
        match="candidate_order must contain every candidate ID exactly once",
    ):
        create_orientation_selection(
            run=proof,
            candidate_id="fo-011-phi1-045",
            author="Z",
            rationale="A human rationale.",
            selected_on="2026-07-13",
            output_root=tmp_path / "decisions",
        )


def test_second_decision_for_proof_requires_explicit_supersession(tmp_path: Path) -> None:
    proof = _proof_bundle(tmp_path)
    output = tmp_path / "decisions"
    create_orientation_selection(
        run=proof,
        candidate_id="fo-011-phi1-045",
        author="Z",
        rationale="First human decision.",
        selected_on="2026-07-13",
        output_root=output,
    )

    with pytest.raises(OrientationSelectionError, match="supersede"):
        create_orientation_selection(
            run=proof,
            candidate_id="fo-011-phi1-045",
            author="Z",
            rationale="A revised human decision.",
            selected_on="2026-07-13",
            output_root=output,
        )


def test_supersession_creates_a_linked_new_immutable_artifact(tmp_path: Path) -> None:
    proof = _proof_bundle(tmp_path)
    output = tmp_path / "decisions"
    first = create_orientation_selection(
        run=proof,
        candidate_id="fo-011-phi1-045",
        author="Z",
        rationale="First human decision.",
        selected_on="2026-07-13",
        output_root=output,
    )
    predecessor_bytes = first.selection_path.read_bytes()

    second = create_orientation_selection(
        run=proof,
        candidate_id="fo-011-phi1-045",
        author="Z",
        rationale="Revised rationale after another review.",
        selected_on="2026-07-14",
        output_root=output,
        supersedes=first.selection_id,
        supersede_reason="The recorded rationale needed a material clarification.",
    )

    assert second.selection_id != first.selection_id
    assert first.selection_path.read_bytes() == predecessor_bytes
    record = json.loads(second.selection_path.read_text())
    assert record["decision"]["supersession"] == {
        "reason": "The recorded rationale needed a material clarification.",
        "selection_id": first.selection_id,
        "decision_sha256": json.loads(predecessor_bytes)["decision_sha256"],
        "selection_sha256": hashlib.sha256(predecessor_bytes).hexdigest(),
    }


def test_supersession_rejects_fork_from_non_leaf_predecessor(tmp_path: Path) -> None:
    proof = _proof_bundle(tmp_path)
    output = tmp_path / "decisions"
    first = create_orientation_selection(
        run=proof,
        candidate_id="fo-011-phi1-045",
        author="Z",
        rationale="First decision.",
        selected_on="2026-07-13",
        output_root=output,
    )
    create_orientation_selection(
        run=proof,
        candidate_id="fo-011-phi1-045",
        author="Z",
        rationale="Current leaf.",
        selected_on="2026-07-14",
        output_root=output,
        supersedes=first.selection_id,
        supersede_reason="First linear correction.",
    )

    with pytest.raises(OrientationSelectionError, match="current unique leaf"):
        create_orientation_selection(
            run=proof,
            candidate_id="fo-011-phi1-045",
            author="Z",
            rationale="Forked successor.",
            selected_on="2026-07-15",
            output_root=output,
            supersedes=first.selection_id,
            supersede_reason="This fork must be rejected.",
        )


def test_concurrent_subprocesses_cannot_fork_one_predecessor(tmp_path: Path) -> None:
    proof = _proof_bundle(tmp_path)
    output = tmp_path / "decisions"
    first = create_orientation_selection(
        run=proof,
        candidate_id="fo-011-phi1-045",
        author="Z",
        rationale="Initial decision.",
        selected_on="2026-07-13",
        output_root=output,
    )
    start = tmp_path / "start"
    ready = tmp_path / "ready"
    ready.mkdir()
    processes = []
    for index in range(6):
        script = f"""
import sys
import time
from pathlib import Path
import kikuchi_lab.orientations.selection as selection_module
from kikuchi_lab.orientations.selection import create_orientation_selection

original_selection_records = selection_module._selection_records
def synchronized_selection_records(root, **kwargs):
    records = original_selection_records(root, **kwargs)
    Path({str(ready / str(index))!r}).write_text("ready", encoding="utf-8")
    deadline = time.monotonic() + 0.35
    while len(list(Path({str(ready)!r}).iterdir())) < 6 and time.monotonic() < deadline:
        time.sleep(0.001)
    return records
selection_module._selection_records = synchronized_selection_records

while not Path({str(start)!r}).exists():
    time.sleep(0.001)
try:
    create_orientation_selection(
        run={str(proof)!r},
        candidate_id="fo-011-phi1-045",
        author="Z",
        rationale={f"Concurrent successor {index}."!r},
        selected_on="2026-07-14",
        output_root={str(output)!r},
        supersedes={first.selection_id!r},
        supersede_reason="Concurrent linearity test.",
    )
except Exception as error:
    print(type(error).__name__ + ": " + str(error), file=sys.stderr)
    raise SystemExit(1)
"""
        processes.append(
            subprocess.Popen(
                [sys.executable, "-c", script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        )
    start.write_text("go", encoding="utf-8")
    results = [process.communicate(timeout=30) for process in processes]

    assert sum(process.returncode == 0 for process in processes) == 1, results
    assert len(list(output.glob("orientation-selection-*/selection.json"))) == 2


def test_concurrent_initial_subprocess_selections_have_one_winner(tmp_path: Path) -> None:
    proof = _proof_bundle(tmp_path)
    output = tmp_path / "decisions"
    start = tmp_path / "start"
    processes = []
    script = f"""
import sys
import time
from pathlib import Path
from kikuchi_lab.orientations.selection import create_orientation_selection

while not Path({str(start)!r}).exists():
    time.sleep(0.001)
try:
    create_orientation_selection(
        run={str(proof)!r},
        candidate_id="fo-011-phi1-045",
        author="Z",
        rationale="One shared initial decision.",
        selected_on="2026-07-13",
        output_root={str(output)!r},
    )
except Exception as error:
    print(type(error).__name__ + ": " + str(error), file=sys.stderr)
    raise SystemExit(1)
"""
    for _ in range(4):
        processes.append(
            subprocess.Popen(
                [sys.executable, "-c", script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        )
    start.write_text("go", encoding="utf-8")
    results = [process.communicate(timeout=30) for process in processes]

    assert sum(process.returncode == 0 for process in processes) == 1, results
    assert len(list(output.glob("orientation-selection-*/selection.json"))) == 1


def test_selection_identity_excludes_local_proof_and_output_paths(tmp_path: Path) -> None:
    first_proof = _proof_bundle(tmp_path / "first")
    second_proof = tmp_path / "second" / "runs" / first_proof.name
    shutil.copytree(first_proof, second_proof)
    arguments = {
        "candidate_id": "fo-011-phi1-045",
        "author": "Z",
        "rationale": "Same human decision over identical sealed evidence.",
        "selected_on": "2026-07-13",
    }

    first = create_orientation_selection(
        run=first_proof,
        output_root=tmp_path / "first-decisions",
        **arguments,
    )
    second = create_orientation_selection(
        run=second_proof,
        output_root=tmp_path / "second-decisions",
        **arguments,
    )

    assert first.selection_id == second.selection_id


def test_selection_requires_an_iso_calendar_date(tmp_path: Path) -> None:
    with pytest.raises(OrientationSelectionError, match="selected-on"):
        create_orientation_selection(
            run=_proof_bundle(tmp_path),
            candidate_id="fo-011-phi1-045",
            author="Z",
            rationale="A human rationale.",
            selected_on="July 13",
            output_root=tmp_path / "decisions",
        )


@pytest.mark.parametrize(("field", "value"), [("author", "  "), ("rationale", "\n")])
def test_selection_requires_nonblank_human_fields(
    tmp_path: Path, field: str, value: str
) -> None:
    arguments = {
        "run": _proof_bundle(tmp_path),
        "candidate_id": "fo-011-phi1-045",
        "author": "Z",
        "rationale": "Human visual judgment.",
        "selected_on": "2026-07-13",
        "output_root": tmp_path / "decisions",
    }
    arguments[field] = value

    with pytest.raises(OrientationSelectionError, match=field):
        create_orientation_selection(**arguments)


def test_selection_rejects_missing_candidate(tmp_path: Path) -> None:
    with pytest.raises(OrientationSelectionError, match="candidate is not in proof"):
        create_orientation_selection(
            run=_proof_bundle(tmp_path),
            candidate_id="fo-does-not-exist",
            author="Z",
            rationale="Human visual judgment.",
            selected_on="2026-07-13",
            output_root=tmp_path / "decisions",
        )


def test_selection_rejects_proof_inventory_drift(tmp_path: Path) -> None:
    proof = _proof_bundle(tmp_path)
    evidence = proof / "candidates/fo-011-phi1-045/evidence.json"
    evidence.write_text(evidence.read_text() + "\n", encoding="utf-8")

    with pytest.raises(OrientationSelectionError, match="checksum mismatch"):
        create_orientation_selection(
            run=proof,
            candidate_id="fo-011-phi1-045",
            author="Z",
            rationale="Human visual judgment.",
            selected_on="2026-07-13",
            output_root=tmp_path / "decisions",
        )


def test_selection_never_overwrites_an_existing_artifact(tmp_path: Path) -> None:
    proof = _proof_bundle(tmp_path)
    arguments = {
        "run": proof,
        "candidate_id": "fo-011-phi1-045",
        "author": "Z",
        "rationale": "Human visual judgment.",
        "selected_on": "2026-07-13",
        "output_root": tmp_path / "decisions",
    }
    first = create_orientation_selection(**arguments)
    before = first.selection_path.read_bytes()

    with pytest.raises(SelectionExistsError, match="already exists"):
        create_orientation_selection(**arguments)

    assert first.selection_path.read_bytes() == before


def test_selection_publication_fsyncs_before_and_after_atomic_rename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[str] = []

    def write_file(path: Path, payload: bytes) -> None:
        events.append("write-and-fsync-file")
        path.write_bytes(payload)

    def fsync_directory(path: Path) -> None:
        events.append("fsync-output" if path.name == "decisions" else "fsync-staging")

    def rename(source: Path, target: Path) -> None:
        events.append("atomic-rename")
        source.rename(target)

    monkeypatch.setattr(selection_module, "_write_selection_file", write_file)
    monkeypatch.setattr(selection_module, "_fsync_directory", fsync_directory)
    monkeypatch.setattr(selection_module, "_rename_selection", rename)

    create_orientation_selection(
        run=_proof_bundle(tmp_path),
        candidate_id="fo-011-phi1-045",
        author="Z",
        rationale="Human visual judgment.",
        selected_on="2026-07-13",
        output_root=tmp_path / "decisions",
    )

    assert events == [
        "write-and-fsync-file",
        "fsync-staging",
        "atomic-rename",
        "fsync-output",
    ]


def test_selection_publication_cleans_staging_after_rename_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "decisions"

    def fail_rename(_source: Path, _target: Path) -> None:
        raise OSError("injected rename failure")

    monkeypatch.setattr(selection_module, "_rename_selection", fail_rename)

    with pytest.raises(OSError, match="injected rename failure"):
        create_orientation_selection(
            run=_proof_bundle(tmp_path),
            candidate_id="fo-011-phi1-045",
            author="Z",
            rationale="Human visual judgment.",
            selected_on="2026-07-13",
            output_root=output,
        )

    assert not list(output.glob(".orientation-selection-*"))
    assert not list(output.glob("orientation-selection-*"))


def test_superseding_requires_a_nonblank_reason(tmp_path: Path) -> None:
    proof = _proof_bundle(tmp_path)
    first = create_orientation_selection(
        run=proof,
        candidate_id="fo-011-phi1-045",
        author="Z",
        rationale="First human decision.",
        selected_on="2026-07-13",
        output_root=tmp_path / "decisions",
    )

    with pytest.raises(OrientationSelectionError, match="supersede-reason"):
        create_orientation_selection(
            run=proof,
            candidate_id="fo-011-phi1-045",
            author="Z",
            rationale="Revised human decision.",
            selected_on="2026-07-14",
            output_root=tmp_path / "decisions",
            supersedes=first.selection_id,
            supersede_reason=" ",
        )


def test_select_orientation_cli_reports_concise_validation_errors(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    status = main(
        [
            "select-orientation",
            "--run",
            str(tmp_path / "missing-proof"),
            "--candidate",
            "fo-011-phi1-045",
            "--author",
            "Z",
            "--rationale",
            "Human visual judgment.",
            "--selected-on",
            "2026-07-13",
            "--output",
            str(tmp_path / "decisions"),
        ]
    )

    captured = capsys.readouterr()
    assert status == 1
    assert "selection failed: proof run does not exist" in captured.err
    assert "Traceback" not in captured.err


def test_select_orientation_cli_rejects_nonfinite_json_without_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    proof = _proof_bundle(tmp_path)
    manifest_path = proof / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["identity"]["nonfinite"] = float("nan")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    status = main(
        [
            "select-orientation",
            "--run",
            str(proof),
            "--candidate",
            "fo-011-phi1-045",
            "--author",
            "Z",
            "--rationale",
            "Human visual judgment.",
            "--selected-on",
            "2026-07-13",
            "--output",
            str(tmp_path / "decisions"),
        ]
    )

    captured = capsys.readouterr()
    assert status == 1
    assert "selection failed: proof manifest is not valid JSON" in captured.err
    assert "Traceback" not in captured.err


def test_select_orientation_cli_writes_the_requested_decision(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "decisions"

    status = main(
        [
            "select-orientation",
            "--run",
            str(_proof_bundle(tmp_path)),
            "--candidate",
            "fo-011-phi1-045",
            "--author",
            "Z",
            "--rationale",
            "Human visual judgment.",
            "--selected-on",
            "2026-07-13",
            "--output",
            str(output),
        ]
    )

    assert status == 0
    reported = json.loads(capsys.readouterr().out)
    assert reported["selection_id"].startswith("orientation-selection-")
    assert Path(reported["selection"]).is_file()


def test_selection_loader_rejects_decision_content_drift(tmp_path: Path) -> None:
    result = create_orientation_selection(
        run=_proof_bundle(tmp_path),
        candidate_id="fo-011-phi1-045",
        author="Z",
        rationale="Human visual judgment.",
        selected_on="2026-07-13",
        output_root=tmp_path / "decisions",
    )
    record = json.loads(result.selection_path.read_text())
    record["decision"]["rationale"] = "Unsealed mutation"
    _write_json(result.selection_path, record)

    with pytest.raises(OrientationSelectionError, match="decision checksum"):
        load_orientation_selection(result.selection_path)


def test_selection_loader_rejects_self_consistent_unsafe_locator(tmp_path: Path) -> None:
    result = create_orientation_selection(
        run=_proof_bundle(tmp_path),
        candidate_id="fo-011-phi1-045",
        author="Z",
        rationale="Human visual judgment.",
        selected_on="2026-07-13",
        output_root=tmp_path / "decisions",
    )
    record = json.loads(result.selection_path.read_text())
    record["decision"]["selected_candidate"]["evidence_locator"] = "../outside.json"
    rewritten = _write_self_consistent_selection(result.selection_path, record)

    with pytest.raises(OrientationSelectionError, match="safe relative POSIX path"):
        load_orientation_selection(rewritten)


def test_selection_loader_rejects_self_consistent_empty_orientation(tmp_path: Path) -> None:
    result = create_orientation_selection(
        run=_proof_bundle(tmp_path),
        candidate_id="fo-011-phi1-045",
        author="Z",
        rationale="Human visual judgment.",
        selected_on="2026-07-13",
        output_root=tmp_path / "decisions",
    )
    record = json.loads(result.selection_path.read_text())
    selected = record["decision"]["selected_candidate"]
    selected["candidate"]["orientation"]["euler_bunge_deg"] = []
    selected["candidate_sha256"] = hashlib.sha256(
        canonical_json(selected["candidate"]).encode("utf-8")
    ).hexdigest()
    rewritten = _write_self_consistent_selection(result.selection_path, record)

    with pytest.raises(OrientationSelectionError, match="three finite Bunge angles"):
        load_orientation_selection(rewritten)


def test_selection_loader_rejects_self_consistent_zero_hash(tmp_path: Path) -> None:
    result = create_orientation_selection(
        run=_proof_bundle(tmp_path),
        candidate_id="fo-011-phi1-045",
        author="Z",
        rationale="Human visual judgment.",
        selected_on="2026-07-13",
        output_root=tmp_path / "decisions",
    )
    record = json.loads(result.selection_path.read_text())
    record["decision"]["selected_candidate"]["evidence_sha256"] = "0" * 64
    rewritten = _write_self_consistent_selection(result.selection_path, record)

    with pytest.raises(OrientationSelectionError, match="nonzero lowercase SHA-256"):
        load_orientation_selection(rewritten)


def test_selection_loader_rejects_boolean_schema_version(tmp_path: Path) -> None:
    result = create_orientation_selection(
        run=_proof_bundle(tmp_path),
        candidate_id="fo-011-phi1-045",
        author="Z",
        rationale="Human visual judgment.",
        selected_on="2026-07-13",
        output_root=tmp_path / "decisions",
    )
    record = json.loads(result.selection_path.read_text())
    record["schema_version"] = True
    record["decision"]["schema_version"] = True
    rewritten = _write_self_consistent_selection(result.selection_path, record)

    with pytest.raises(OrientationSelectionError, match="schema_version must be integer"):
        load_orientation_selection(rewritten)


@pytest.mark.parametrize("schema_version", [1, 3])
def test_selection_loader_rejects_boolean_decision_schema_version(
    tmp_path: Path, schema_version: int
) -> None:
    result = create_orientation_selection(
        run=_proof_bundle(tmp_path),
        candidate_id="fo-011-phi1-045",
        author="Z",
        rationale="Human visual judgment.",
        selected_on="2026-07-13",
        output_root=tmp_path / "decisions",
    )
    record = json.loads(result.selection_path.read_text())
    record["schema_version"] = schema_version
    record["decision"]["schema_version"] = True
    if schema_version == 1:
        record["decision"]["proof"].pop("tree_digest")
    rewritten = _write_self_consistent_selection(result.selection_path, record)

    with pytest.raises(
        OrientationSelectionError,
        match="decision schema_version must be integer and match selection schema",
    ):
        load_orientation_selection(rewritten)


def test_selection_loader_rejects_self_consistent_malformed_ids(tmp_path: Path) -> None:
    result = create_orientation_selection(
        run=_proof_bundle(tmp_path),
        candidate_id="fo-011-phi1-045",
        author="Z",
        rationale="Human visual judgment.",
        selected_on="2026-07-13",
        output_root=tmp_path / "decisions",
    )
    record = json.loads(result.selection_path.read_text())
    record["decision"]["proof"]["proof_id"] = "proof-not-a-content-id"
    rewritten = _write_self_consistent_selection(result.selection_path, record)

    with pytest.raises(OrientationSelectionError, match="proof identity is invalid"):
        load_orientation_selection(rewritten)


def test_selection_loader_rejects_invalid_superseded_identity_relation(
    tmp_path: Path,
) -> None:
    proof = _proof_bundle(tmp_path)
    output = tmp_path / "decisions"
    first = create_orientation_selection(
        run=proof,
        candidate_id="fo-011-phi1-045",
        author="Z",
        rationale="First decision.",
        selected_on="2026-07-13",
        output_root=output,
    )
    second = create_orientation_selection(
        run=proof,
        candidate_id="fo-011-phi1-045",
        author="Z",
        rationale="Second decision.",
        selected_on="2026-07-14",
        output_root=output,
        supersedes=first.selection_id,
        supersede_reason="Material correction.",
    )
    record = json.loads(second.selection_path.read_text())
    record["decision"]["supersession"]["selection_id"] = (
        "orientation-selection-0123456789abcdef"
    )
    rewritten = _write_self_consistent_selection(second.selection_path, record)

    with pytest.raises(
        OrientationSelectionError,
        match="superseded selection identity does not match decision checksum",
    ):
        load_orientation_selection(rewritten)


def test_selection_loader_rejects_self_consistent_empty_geometry_and_metrics(
    tmp_path: Path,
) -> None:
    result = create_orientation_selection(
        run=_proof_bundle(tmp_path),
        candidate_id="fo-011-phi1-045",
        author="Z",
        rationale="Human visual judgment.",
        selected_on="2026-07-13",
        output_root=tmp_path / "decisions",
    )
    record = json.loads(result.selection_path.read_text())
    selected = record["decision"]["selected_candidate"]
    selected["geometry"] = {}
    selected["geometry_sha256"] = hashlib.sha256(b"{}").hexdigest()
    selected["metrics"] = {}
    selected["metrics_sha256"] = hashlib.sha256(b"{}").hexdigest()
    rewritten = _write_self_consistent_selection(result.selection_path, record)

    with pytest.raises(OrientationSelectionError, match="substantive geometry"):
        load_orientation_selection(rewritten)


def test_selection_loader_rejects_unknown_schema_fields(tmp_path: Path) -> None:
    result = create_orientation_selection(
        run=_proof_bundle(tmp_path),
        candidate_id="fo-011-phi1-045",
        author="Z",
        rationale="Human visual judgment.",
        selected_on="2026-07-13",
        output_root=tmp_path / "decisions",
    )
    record = json.loads(result.selection_path.read_text())
    record["unknown_field"] = "not schema declared"
    rewritten = _write_self_consistent_selection(result.selection_path, record)

    with pytest.raises(OrientationSelectionError, match="selection fields differ"):
        load_orientation_selection(rewritten)


def test_selection_verifier_rejects_candidate_that_disagrees_with_proof_evidence(
    tmp_path: Path,
) -> None:
    result = create_orientation_selection(
        run=_proof_bundle(tmp_path),
        candidate_id="fo-011-phi1-045",
        author="Z",
        rationale="Human visual judgment.",
        selected_on="2026-07-13",
        output_root=tmp_path / "decisions",
    )
    record = json.loads(result.selection_path.read_text())
    selected = record["decision"]["selected_candidate"]
    selected["candidate"]["name"] = "self-consistent but not proof-consistent"
    selected["candidate_sha256"] = hashlib.sha256(
        canonical_json(selected["candidate"]).encode("utf-8")
    ).hexdigest()
    rewritten = _write_self_consistent_selection(result.selection_path, record)

    with pytest.raises(OrientationSelectionError, match="proof candidate evidence disagrees"):
        verify_orientation_selection(rewritten)


def test_selection_verifier_recomputes_canonical_proof_identity(tmp_path: Path) -> None:
    proof = _proof_bundle(tmp_path)
    result = create_orientation_selection(
        run=proof,
        candidate_id="fo-011-phi1-045",
        author="Z",
        rationale="Human visual judgment.",
        selected_on="2026-07-13",
        output_root=tmp_path / "decisions",
    )
    manifest_path = proof / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    forged_proof_id = "proof-0123456789abcdef"
    assert forged_proof_id != stable_id("proof", manifest["identity"])
    manifest["proof_id"] = forged_proof_id
    _write_json(manifest_path, manifest)
    record = json.loads(result.selection_path.read_text())
    record["decision"]["proof"].update(
        {
            "proof_id": forged_proof_id,
            "manifest_sha256": _sha256(manifest_path),
            "tree_digest": proof_tree_digest(proof),
        }
    )
    rewritten = _write_self_consistent_selection(result.selection_path, record)

    with pytest.raises(
        OrientationSelectionError,
        match="external proof identity does not match canonical manifest identity",
    ):
        verify_orientation_selection(rewritten)


def test_selection_verifier_recomputes_canonical_candidate_set_identity(
    tmp_path: Path,
) -> None:
    proof = _proof_bundle(tmp_path)
    result = create_orientation_selection(
        run=proof,
        candidate_id="fo-011-phi1-045",
        author="Z",
        rationale="Human visual judgment.",
        selected_on="2026-07-13",
        output_root=tmp_path / "decisions",
    )
    candidate_set_path = proof / "metadata/orientation-candidates.json"
    candidate_set = json.loads(candidate_set_path.read_text())
    forged_candidate_set_id = "candidate-set-0123456789abcdef"
    assert forged_candidate_set_id != stable_id(
        "candidate-set", selection_module._candidate_set_identity_payload(candidate_set)
    )
    candidate_set["candidate_set_id"] = forged_candidate_set_id
    _write_json(candidate_set_path, candidate_set)
    record = json.loads(result.selection_path.read_text())
    record["decision"]["candidate_set"].update(
        {
            "candidate_set_id": forged_candidate_set_id,
            "candidate_set_sha256": _sha256(candidate_set_path),
        }
    )
    record["decision"]["proof"]["tree_digest"] = proof_tree_digest(proof)
    rewritten = _write_self_consistent_selection(result.selection_path, record)

    with pytest.raises(
        OrientationSelectionError,
        match="external candidate-set identity does not match canonical content",
    ):
        verify_orientation_selection(rewritten)


def test_selection_verifier_requires_exact_manifest_candidate_order(
    tmp_path: Path,
) -> None:
    proof = _proof_bundle(tmp_path)
    result = create_orientation_selection(
        run=proof,
        candidate_id="fo-011-phi1-045",
        author="Z",
        rationale="Human visual judgment.",
        selected_on="2026-07-13",
        output_root=tmp_path / "decisions",
    )
    manifest_path = proof / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["candidate_order"] = []
    _write_json(manifest_path, manifest)
    record = json.loads(result.selection_path.read_text())
    record["decision"]["proof"].update(
        {
            "manifest_sha256": _sha256(manifest_path),
            "tree_digest": proof_tree_digest(proof),
        }
    )
    rewritten = _write_self_consistent_selection(result.selection_path, record)

    with pytest.raises(
        OrientationSelectionError,
        match="external manifest candidate_order must contain every candidate ID exactly once",
    ):
        verify_orientation_selection(rewritten)


def test_selection_verifier_preserves_canonical_candidate_set_order(
    tmp_path: Path,
) -> None:
    proof = _proof_bundle(tmp_path)
    result = create_orientation_selection(
        run=proof,
        candidate_id="fo-011-phi1-045",
        author="Z",
        rationale="Human visual judgment.",
        selected_on="2026-07-13",
        output_root=tmp_path / "decisions",
    )
    candidate_set_path = proof / "metadata/orientation-candidates.json"
    candidate_set = json.loads(candidate_set_path.read_text())
    second_candidate = deepcopy(candidate_set["candidates"][0])
    second_candidate["id"] = "fo-001-phi1-000"
    candidate_set["candidates"].append(second_candidate)
    candidate_set_id = stable_id(
        "candidate-set", selection_module._candidate_set_identity_payload(candidate_set)
    )
    candidate_set["candidate_set_id"] = candidate_set_id
    _write_json(candidate_set_path, candidate_set)

    manifest_path = proof / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    reversed_order = [second_candidate["id"], "fo-011-phi1-045"]
    manifest["candidate_order"] = reversed_order
    manifest["candidate_set_id"] = candidate_set_id
    manifest["identity"]["candidate_order"] = reversed_order
    manifest["identity"]["candidate_set_id"] = candidate_set_id
    manifest["proof_id"] = stable_id("proof", manifest["identity"])
    candidate_set_relative = candidate_set_path.relative_to(proof).as_posix()
    manifest["files"][candidate_set_relative] = {
        "bytes": candidate_set_path.stat().st_size,
        "sha256": _sha256(candidate_set_path),
    }
    _write_json(manifest_path, manifest)

    record = json.loads(result.selection_path.read_text())
    record["decision"]["proof"].update(
        {
            "proof_id": manifest["proof_id"],
            "manifest_sha256": _sha256(manifest_path),
            "tree_digest": proof_tree_digest(proof),
        }
    )
    record["decision"]["candidate_set"].update(
        {
            "candidate_set_id": candidate_set_id,
            "candidate_set_sha256": _sha256(candidate_set_path),
        }
    )
    rewritten = _write_self_consistent_selection(result.selection_path, record)

    with pytest.raises(
        OrientationSelectionError,
        match="external manifest candidate_order must preserve candidate-set order",
    ):
        verify_orientation_selection(rewritten)


def test_supersession_rejects_symbolic_link_predecessor_directory(
    tmp_path: Path,
) -> None:
    proof = _proof_bundle(tmp_path)
    output = tmp_path / "decisions"
    first = create_orientation_selection(
        run=proof,
        candidate_id="fo-011-phi1-045",
        author="Z",
        rationale="Initial decision.",
        selected_on="2026-07-13",
        output_root=output,
    )
    external = tmp_path / "external" / first.selection_id
    external.parent.mkdir()
    shutil.move(first.path, external)
    first.path.symlink_to(external, target_is_directory=True)

    with pytest.raises(OrientationSelectionError, match="symbolic link"):
        create_orientation_selection(
            run=proof,
            candidate_id="fo-011-phi1-045",
            author="Z",
            rationale="Revised decision.",
            selected_on="2026-07-14",
            output_root=output,
            supersedes=first.selection_id,
            supersede_reason="Material correction.",
        )


def test_supersession_rejects_symbolic_link_predecessor_file(tmp_path: Path) -> None:
    proof = _proof_bundle(tmp_path)
    output = tmp_path / "decisions"
    first = create_orientation_selection(
        run=proof,
        candidate_id="fo-011-phi1-045",
        author="Z",
        rationale="Initial decision.",
        selected_on="2026-07-13",
        output_root=output,
    )
    external = tmp_path / "external" / first.selection_id / "selection.json"
    external.parent.mkdir(parents=True)
    shutil.move(first.selection_path, external)
    first.selection_path.symlink_to(external)

    with pytest.raises(OrientationSelectionError, match="symbolic link"):
        create_orientation_selection(
            run=proof,
            candidate_id="fo-011-phi1-045",
            author="Z",
            rationale="Revised decision.",
            selected_on="2026-07-14",
            output_root=output,
            supersedes=first.selection_id,
            supersede_reason="Material correction.",
        )


def test_supersession_validates_identity_before_filesystem_access(tmp_path: Path) -> None:
    with pytest.raises(OrientationSelectionError, match="superseded selection identity"):
        create_orientation_selection(
            run=_proof_bundle(tmp_path),
            candidate_id="fo-011-phi1-045",
            author="Z",
            rationale="Revised decision.",
            selected_on="2026-07-14",
            output_root=tmp_path / "decisions",
            supersedes="../outside",
            supersede_reason="Material correction.",
        )


def test_intrinsic_selection_load_survives_proof_relocation_with_explicit_override(
    tmp_path: Path,
) -> None:
    proof = _proof_bundle(tmp_path / "original")
    result = create_orientation_selection(
        run=proof,
        candidate_id="fo-011-phi1-045",
        author="Z",
        rationale="Human visual judgment.",
        selected_on="2026-07-13",
        output_root=tmp_path / "decisions",
    )
    relocated = tmp_path / "relocated" / proof.name
    shutil.copytree(proof, relocated)
    shutil.rmtree(proof)

    record = load_orientation_selection(result.selection_path)
    verification = verify_orientation_selection(
        result.selection_path, proof_root=relocated
    )

    assert record["selection_id"] == result.selection_id
    assert verification.verified is True
    assert verification.selection_id == result.selection_id
    assert verification.proof_root == relocated.resolve()
