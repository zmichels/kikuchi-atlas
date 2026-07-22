#!/usr/bin/env python3
"""Build a local browsable dashboard for the Ice Ih dictionary-engine evidence."""

from __future__ import annotations

import argparse
import html
import os
from pathlib import Path
import shutil
import sys
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "local/ice-ih-engine-dashboard-v0.1.1"


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _relative_from_dashboard(dashboard_root: Path, path: Path) -> str:
    return Path(os.path.relpath(path.resolve(), start=dashboard_root.resolve())).as_posix()


def _required_file(path: Path) -> Path:
    if not path.is_file():
        raise FileNotFoundError(f"required Ice Ih evidence file is missing: {path}")
    return path


def _card(
    *,
    title: str,
    eyebrow: str,
    summary: str,
    image: Path,
    evidence: Path,
    dashboard_root: Path,
) -> dict[str, str]:
    return {
        "title": title,
        "eyebrow": eyebrow,
        "summary": summary,
        "image": _relative_from_dashboard(dashboard_root, _required_file(image)),
        "evidence": _relative_from_dashboard(dashboard_root, _required_file(evidence)),
    }


def _html(cards: list[dict[str, str]], observation_manifest: str) -> str:
    card_html = "\n".join(
        (
            '<article class="card">'
            f'<a class="image-link" href="{html.escape(card["image"])}">'
            f'<img src="{html.escape(card["image"])}" alt="{html.escape(card["title"])}">'
            "</a>"
            '<div class="card-body">'
            f'<p class="eyebrow">{html.escape(card["eyebrow"])}</p>'
            f'<h2>{html.escape(card["title"])}</h2>'
            f'<p>{html.escape(card["summary"])}</p>'
            f'<a class="button" href="{html.escape(card["evidence"])}">open evidence</a>'
            "</div></article>"
        )
        for card in cards
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Ice Ih Engine Evidence</title>
  <style>
    :root {{ color-scheme: dark; --ink: #eaf2f6; --soft: #a8bbc8; --line: #304453; --panel: #111b22; --accent: #67d7c6; --blue: #9bc8ff; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: radial-gradient(circle at 24% -6%, #1b3340, transparent 35rem), #081016; color: var(--ink); font-family: ui-rounded, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; line-height: 1.5; }}
    main {{ max-width: 1500px; margin: 0 auto; padding: 4rem 2.5rem 5rem; }}
    .eyebrow {{ margin: 0 0 .55rem; color: var(--blue); font-size: .78rem; letter-spacing: .15em; text-transform: uppercase; font-weight: 700; }}
    h1 {{ margin: 0; font-size: clamp(2.6rem, 6vw, 5rem); letter-spacing: -.055em; line-height: .98; }}
    .lede {{ max-width: 58rem; color: var(--soft); font-size: 1.16rem; margin: 1.5rem 0 2.4rem; }}
    .rail {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1px; background: var(--line); border: 1px solid var(--line); border-radius: 1.1rem; overflow: hidden; margin: 2rem 0 3.5rem; }}
    .rail div {{ padding: 1rem 1.1rem 1.15rem; background: #0d161c; }}
    .rail strong {{ display: block; color: var(--accent); font-size: .88rem; margin-bottom: .25rem; }}
    .rail span {{ color: var(--soft); font-size: .93rem; }}
    h2 {{ margin: .15rem 0 .55rem; font-size: 1.45rem; letter-spacing: -.028em; line-height: 1.05; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1.3rem; }}
    .card {{ min-width: 0; overflow: hidden; border: 1px solid var(--line); border-radius: 1.15rem; background: var(--panel); box-shadow: 0 1rem 3rem rgba(0,0,0,.15); }}
    .image-link {{ display: block; background: #fff; }}
    .image-link img {{ width: 100%; display: block; aspect-ratio: 16 / 10; object-fit: cover; object-position: top; }}
    .card-body {{ padding: 1.25rem 1.35rem 1.4rem; }}
    .card-body > p:not(.eyebrow) {{ color: var(--soft); min-height: 3.2rem; margin: 0 0 1.2rem; }}
    .button {{ color: var(--blue); font-weight: 700; text-decoration: none; border: 1px solid #567a91; border-radius: .55rem; padding: .43rem .68rem; }}
    .foot {{ color: var(--soft); margin: 3rem 0 0; max-width: 68rem; font-size: .95rem; }}
    .foot a {{ color: var(--accent); }}
    @media (max-width: 780px) {{ main {{ padding: 2.4rem 1.15rem 3rem; }} .rail, .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
<main>
  <p class="eyebrow">Kikuchi Atlas · Ice Ih · detector-to-dictionary evidence</p>
  <h1>One pattern, named all the way down.</h1>
  <p class="lede">A browsable local index of the current Ice Ih engine slices: image-space bands, explicit detector geometry, fixed spherical features, coarse candidates, local orientation refinement, and the limits we can already see. These are source-bound synthetic proofs—not acquired-pattern performance claims.</p>
  <section class="rail" aria-label="evidence ladder">
    <div><strong>01 · Observe</strong><span>Raw detector values plus explicit geometry and identity preprocessing.</span></div>
    <div><strong>02 · Transform</strong><span>Detector pixels become a coverage-masked sample-frame S² signal.</span></div>
    <div><strong>03 · Solve carefully</strong><span>Cache ranking, local refinement, and sensitivity diagnostics retain their nonclaims.</span></div>
  </section>
  <section class="grid">
    {card_html}
  </section>
  <p class="foot">Machine-readable starting point: <a href="{html.escape(observation_manifest)}">Ice Ih detector observation manifest</a>. The manifest is intentionally identity-preprocessing only; no background correction, denoising, blur, or calibration is implied. Each card opens its source-bound JSON evidence or checksum-bearing package.</p>
</main>
</body>
</html>"""


def build(output_root: Path) -> Path:
    root = output_root.resolve()
    if root.exists():
        raise FileExistsError(f"dashboard output already exists: {root}")
    dictionaries = ROOT / "local/dictionaries"
    observation_manifest = ROOT / "local/observations/ice-ih-source-detector-identity-v0.1.0/observation.manifest.json"
    cards = [
        _card(
            title="Native detector Hough space",
            eyebrow="Image-space evidence",
            summary="Finite-difference edges and a raw line accumulator make the detector pattern legible without pretending to solve bands.",
            image=dictionaries / "ice-ih-detector-hough-diagnostic-v0.1.0/detector-hough-diagnostic.png",
            evidence=dictionaries / "ice-ih-detector-hough-diagnostic-v0.1.0/hough-diagnostic.json",
            dashboard_root=root,
        ),
        _card(
            title="Detector to partial S²",
            eyebrow="Explicit geometry bridge",
            summary="The declared camera sees 308 of 1,946 fixed sample-frame directions; the mask remains part of the signal.",
            image=dictionaries / "ice-ih-detector-to-s2-proof-v0.1.0/detector-to-s2-adapter-overview.png",
            evidence=dictionaries / "ice-ih-detector-to-s2-proof-v0.1.0/adapter-proof.json",
            dashboard_root=root,
        ),
        _card(
            title="Held-out orientation refinement",
            eyebrow="Coarse-to-local search",
            summary="Three truths absent from the frozen cache seed a coarse match, then improve under the same masked detector metric.",
            image=dictionaries / "ice-ih-offgrid-detector-refinement-v0.1.0/offgrid-detector-refinement.png",
            evidence=dictionaries / "ice-ih-offgrid-detector-refinement-v0.1.0/offgrid-detector-refinement.json",
            dashboard_root=root,
        ),
        _card(
            title="Projection-center sensitivity",
            eyebrow="Geometry calibration gate",
            summary="A named PCx/PCy perturbation grid shows why detector geometry must travel with the pixels.",
            image=dictionaries / "ice-ih-projection-center-sensitivity-v0.1.0/projection-center-sensitivity.png",
            evidence=dictionaries / "ice-ih-projection-center-sensitivity-v0.1.0/projection-center-sensitivity.json",
            dashboard_root=root,
        ),
        _card(
            title="Photometric stress sheet",
            eyebrow="Explicit synthetic inputs",
            summary="Affine contrast, ramps, clipping, and seeded noise are transparent stress probes—not hidden preprocessing choices.",
            image=dictionaries / "ice-ih-photometric-stress-v0.1.0/photometric-stress.png",
            evidence=dictionaries / "ice-ih-photometric-stress-v0.1.0/photometric-stress.json",
            dashboard_root=root,
        ),
        _card(
            title="Orientation-varied detector recovery",
            eyebrow="Cache convention proof",
            summary="Separated cache orientations look materially different in detector space and recover their known candidates first.",
            image=dictionaries / "ice-ih-synthetic-detector-orientation-recovery-v0.1.0/synthetic-detector-orientation-recovery.png",
            evidence=dictionaries / "ice-ih-synthetic-detector-orientation-recovery-v0.1.0/synthetic-detector-recovery.json",
            dashboard_root=root,
        ),
    ]
    _required_file(observation_manifest)
    staging = root.parent / f".{root.name}.{uuid4().hex}.partial"
    staging.mkdir(parents=True)
    try:
        _write_bytes(
            staging / "index.html",
            _html(cards, _relative_from_dashboard(root, observation_manifest)).encode("utf-8"),
        )
        _write_bytes(
            staging / "README.txt",
            (
                "Open index.html in a local browser. It links to sibling local evidence bundles "
                "and requires the checked Ice Ih products listed in the page.\n"
            ).encode("utf-8"),
        )
        os.replace(staging, root)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return root / "index.html"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        print(f"Ice Ih engine dashboard: {build(args.output)}")
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
