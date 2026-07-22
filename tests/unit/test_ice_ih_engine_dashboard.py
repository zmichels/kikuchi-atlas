from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "scripts/build_ice_ih_engine_dashboard.py"
_SPEC = importlib.util.spec_from_file_location("ice_ih_engine_dashboard", SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(MODULE)


def test_dashboard_html_keeps_observation_boundary_and_evidence_links() -> None:
    page = MODULE._html(
        [
            {
                "title": "Example",
                "eyebrow": "Evidence",
                "summary": "A bounded test card.",
                "image": "dictionaries/example.png",
                "evidence": "dictionaries/example.json",
            }
        ],
        "observations/example.json",
    )

    assert "One pattern, named all the way down." in page
    assert "identity-preprocessing only" in page
    assert 'href="dictionaries/example.json"' in page
    assert 'src="dictionaries/example.png"' in page


def test_dashboard_links_are_relative_to_the_index_file_not_local_root(tmp_path) -> None:
    dashboard = tmp_path / "local/ice-ih-engine-dashboard-v0.1.1"
    evidence = tmp_path / "local/dictionaries/example.png"

    assert MODULE._relative_from_dashboard(dashboard, evidence) == "../dictionaries/example.png"
