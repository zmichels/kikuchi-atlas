from __future__ import annotations

import hashlib
import math
import re
from io import BytesIO
from xml.etree import ElementTree

import matplotlib
import numpy as np
import pytest
from PIL import Image

from kikuchi_lab.art_products.contracts import (
    TattooBoundary,
    TattooGeometry,
    TattooPath,
)
from kikuchi_lab.art_products.tattoo_vector import (
    primary_svg_bytes,
    render_primary_tattoo,
)


WIDTHS = (4.8, 4.2, 3.6, 3.1, 2.5, 2.2, 1.9, 1.6, 1.2, 1.0, 0.8)
TIERS = ("dominant",) * 4 + ("secondary",) * 4 + ("fine",) * 3
EXPECTED = {"primary.svg", "primary.pdf", "mockup.png", "stencil.png"}


def _geometry() -> TattooGeometry:
    center = np.array([72.5, 72.5], dtype="<f8")
    paths = []
    for index, (tier, width) in enumerate(zip(TIERS, WIDTHS, strict=True)):
        angle = index * math.pi / 11.0
        direction = 63.8 * np.array([math.cos(angle), math.sin(angle)], dtype="<f8")
        paths.append(
            TattooPath(
                member_id=f"member-{index:02d}",
                tier=tier,
                width_mm=width,
                points_mm=np.vstack((center - direction, center + direction)),
                score_components={"strength": 1.0 - index / 20.0},
                selection_reason="render fixture with true transverse crossings",
            )
        )
    return TattooGeometry(
        schema_version=1,
        catalog_id="catalog-render-test",
        orientation_id="orientation-render-test",
        artboard_size_mm=145.0,
        boundary=TattooBoundary(
            schema_version=1,
            role="stereographic_hemisphere_boundary",
            scientific_claim="noncrystallographic_projection_primitive",
            center_mm=(72.5, 72.5),
            outer_diameter_mm=132.0,
            width_mm=2.2,
            ink="#000000",
        ),
        paths=tuple(paths),
        projection="upper_specimen_stereographic_center_trace",
    )


def _media_box_points(payload: bytes) -> tuple[float, float]:
    match = re.search(
        rb"/MediaBox\s*\[\s*0(?:\.0+)?\s+0(?:\.0+)?\s+"
        rb"([0-9.]+)\s+([0-9.]+)\s*\]",
        payload,
    )
    assert match is not None
    return float(match.group(1)), float(match.group(2))


def _px(mm: float) -> int:
    return round(mm * 1713 / 145.0)


def test_primary_svg_has_11_paths_then_one_complete_projection_boundary() -> None:
    geometry = _geometry()
    root = ElementTree.fromstring(primary_svg_bytes(geometry))
    children = list(root)
    assert [child.tag.rsplit("}", 1)[-1] for child in children] == [
        *("path" for _ in range(11)),
        "circle",
    ]
    circle = children[-1]
    assert circle.attrib == {
        "cx": "72.500000",
        "cy": "72.500000",
        "fill": "none",
        "id": geometry.boundary.boundary_id,
        "r": "64.900000",
        "stroke": "#000000",
        "stroke-width": "2.200000",
    }


def test_primary_render_is_byte_repeatable_and_preserves_geometry_and_globals() -> None:
    geometry = _geometry()
    geometry_id = geometry.geometry_id
    points_before = tuple(path.points_mm.copy() for path in geometry.paths)
    point_hashes = tuple(path.points_sha256 for path in geometry.paths)
    backend_before = matplotlib.get_backend()
    rc_before = {
        key: matplotlib.rcParams[key]
        for key in (
            "pdf.compression",
            "savefig.bbox",
            "savefig.pad_inches",
            "figure.figsize",
            "figure.dpi",
        )
    }

    first = render_primary_tattoo(geometry)
    repeated = render_primary_tattoo(geometry)

    assert set(first) == EXPECTED
    assert set(repeated) == EXPECTED
    assert {name: hashlib.sha256(payload).hexdigest() for name, payload in first.items()} == {
        name: hashlib.sha256(payload).hexdigest() for name, payload in repeated.items()
    }
    assert dict(first) == dict(repeated)
    assert first["primary.svg"] == primary_svg_bytes(geometry)
    assert first["primary.svg"].startswith(b"<svg ")
    assert first["primary.pdf"].startswith(b"%PDF-")
    assert first["mockup.png"].startswith(b"\x89PNG\r\n\x1a\n")
    assert first["stencil.png"].startswith(b"\x89PNG\r\n\x1a\n")
    assert geometry.geometry_id == geometry_id
    assert tuple(path.points_sha256 for path in geometry.paths) == point_hashes
    for path, before in zip(geometry.paths, points_before, strict=True):
        assert np.array_equal(path.points_mm, before)
        assert not path.points_mm.flags.writeable
    assert matplotlib.get_backend() == backend_before
    assert {key: matplotlib.rcParams[key] for key in rc_before} == rc_before


def test_primary_pdf_has_exact_physical_page_and_stable_metadata() -> None:
    payload = render_primary_tattoo(_geometry())["primary.pdf"]

    width_points, height_points = _media_box_points(payload)
    width_mm = width_points * 25.4 / 72.0
    height_mm = height_points * 25.4 / 72.0
    assert width_mm == pytest.approx(145.0, abs=0.02)
    assert height_mm == pytest.approx(145.0, abs=0.02)
    assert b"/Creator (kikuchi-lab)" in payload
    assert b"/CreationDate" not in payload
    assert b"/ModDate" not in payload
    assert b"/FlateDecode" not in payload


def test_primary_pdf_boundary_effective_zorder_is_above_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from matplotlib.axes import Axes
    from matplotlib.lines import Line2D
    from matplotlib.patches import Circle, Patch

    path_zorders: list[float] = []
    boundary_zorders: list[float] = []
    real_add_line = Axes.add_line
    real_add_patch = Axes.add_patch

    def capture_line(axis: Axes, line: Line2D) -> Line2D:
        path_zorders.append(line.get_zorder())
        return real_add_line(axis, line)

    def capture_patch(axis: Axes, patch: Patch) -> Patch:
        if isinstance(patch, Circle):
            boundary_zorders.append(patch.get_zorder())
        return real_add_patch(axis, patch)

    monkeypatch.setattr(Axes, "add_line", capture_line)
    monkeypatch.setattr(Axes, "add_patch", capture_patch)

    payload = render_primary_tattoo(_geometry())["primary.pdf"]

    assert payload.startswith(b"%PDF-")
    assert len(path_zorders) == 11
    assert len(boundary_zorders) == 1
    assert boundary_zorders[0] > max(path_zorders)


@pytest.mark.parametrize(
    ("name", "background"),
    (("mockup.png", (216, 181, 154)), ("stencil.png", (255, 255, 255))),
)
def test_primary_pngs_are_exact_300_dpi_palettes_without_timestamps(
    name: str,
    background: tuple[int, int, int],
) -> None:
    payload = render_primary_tattoo(_geometry())[name]

    with Image.open(BytesIO(payload)) as source:
        image = source.convert("RGB")
        assert source.size == (1713, 1713)
        assert source.info["dpi"] == pytest.approx((300.0, 300.0), abs=0.01)
        assert set(source.info) == {"dpi"}
        assert image.getpixel((0, 0)) == background
        assert image.getpixel((856, 856)) == (0, 0, 0)
        colors = image.getcolors(maxcolors=3)
        assert colors is not None
        assert {color for _, color in colors} == {background, (0, 0, 0)}
    assert b"tIME" not in payload
    assert b"tEXt" not in payload
    assert b"iTXt" not in payload


@pytest.mark.parametrize(
    ("name", "background"),
    (("mockup.png", (216, 181, 154)), ("stencil.png", (255, 255, 255))),
)
def test_primary_png_shows_complete_132_mm_boundary_with_clear_margin(
    name: str,
    background: tuple[int, int, int],
) -> None:
    payload = render_primary_tattoo(_geometry())[name]
    with Image.open(BytesIO(payload)) as source:
        image = source.convert("RGB")
        center = _px(72.5)
        assert image.getpixel((center, _px(6.5))) == (0, 0, 0)
        assert image.getpixel((center, _px(5.0))) == background
        assert image.getpixel((center, _px(138.5))) == (0, 0, 0)
        assert image.getpixel((_px(5.0), center)) == background
        assert image.getpixel((_px(140.0), center)) == background
